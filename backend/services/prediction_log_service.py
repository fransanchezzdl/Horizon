"""
Servicio de registro y resolución de predicciones.

Dos responsabilidades:
  1. Logger  — llama al modelo por cada ticker y guarda la predicción del día.
  2. Resolver — busca predicciones cuyo horizonte ya pasó, descarga el precio
                real y marca si la predicción fue correcta.

Uso manual (mientras no hay servidor 24/7):
    python -m backend.scripts.daily_log log
    python -m backend.scripts.daily_log resolve
"""

import logging
from datetime import date, timedelta
from typing import Dict, List, Tuple

import numpy as np
import yfinance as yf

from ..daos.prediction_log_dao import PredictionLogDAO
from ..models.config import TICKERS
from ..models.xgboost_model import _load_frozen_thresholds

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _classify_return(ret: float, dn: float, up: float) -> str:
    """Convierte un retorno en clase usando los mismos umbrales frozen del modelo."""
    if ret <= dn:
        return "BAJISTA"
    if ret >= up:
        return "ALCISTA"
    return "LATERAL"


def _get_actual_price(ticker: str, target_date: date) -> Tuple[float, bool]:
    """
    Descarga el precio de cierre más cercano a target_date.

    Busca en una ventana de ±3 días hábiles para cubrir fines de semana
    y festivos. Devuelve (precio, encontrado).
    """
    start = (target_date - timedelta(days=4)).isoformat()
    end   = (target_date + timedelta(days=4)).isoformat()
    try:
        df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
        if df.empty:
            return 0.0, False
        # Día más cercano a target_date
        df.index = df.index.normalize()
        target_ts = date.fromisoformat(target_date.isoformat() if isinstance(target_date, date) else target_date)
        closest = min(df.index, key=lambda d: abs((d.date() - target_ts).days))
        price = float(df.loc[closest, "Close"].iloc[0] if hasattr(df.loc[closest, "Close"], "iloc") else df.loc[closest, "Close"])
        return price, True
    except Exception as e:
        logger.warning(f"[{ticker}] No se pudo obtener precio para {target_date}: {e}")
        return 0.0, False


# ── Logger ─────────────────────────────────────────────────────────────────────

def _build_xgb_features(window: np.ndarray) -> np.ndarray:
    """
    Transforma ventana [window_size, n_features] en vector tabular [12*n_features].

    Agrega [last, mean, std, trend] sobre 3 sub-ventanas temporales:
      - corta  : últimos W//6 pasos  (ej. 5d  para stable, 10d para volatile)
      - media  : últimos W//2 pasos  (ej. 15d para stable, 30d para volatile)
      - completa: ventana entera W   (ej. 30d para stable, 60d para volatile)

    Debe ser idéntico a build_xgb_features en xgboost_model.py
    y a _build_xgb_features en walk_forward_xgb.py.
    """
    W = window.shape[0]
    sub_windows = [max(2, W // 6), W // 2, W]
    parts = []
    for sw in sub_windows:
        sl = window[-sw:, :]
        parts.extend([sl[-1, :], sl.mean(axis=0), sl.std(axis=0), sl[-1, :] - sl[0, :]])
    return np.concatenate(parts)


def _get_xgboost_prediction(ticker: str) -> Dict:
    """
    Obtiene la predicción XGBoost para un ticker descargando datos frescos.

    Replica el flujo de entrenamiento:
      1. Descargar datos y calcular features
      2. Escalar con el scaler guardado
      3. Tomar ventana de window_size filas
      4. Aplicar _build_xgb_features → vector de 4*n_features
      5. predict_xgboost con el vector correcto

    Returns: {trend, confidence, current_price}
    """
    from ..models.data_pipeline import download_data, compute_features, load_scaler
    from ..models.config import TICKERS, get_feature_cols, get_asset_type, ENSEMBLE_VARIATIONS
    from ..models.xgboost_model import predict_xgboost

    asset_type = get_asset_type(ticker)
    window_size = max(v["window_size"] for v in ENSEMBLE_VARIATIONS[asset_type])

    include_market_context = ticker in TICKERS["volatile"]
    raw_df  = download_data(ticker)
    feat_df = compute_features(raw_df, include_market_context=include_market_context, ticker=ticker)

    feature_cols  = get_feature_cols(ticker)
    current_price = float(feat_df["Close"].iloc[-1])

    if len(feat_df) < window_size:
        raise ValueError(f"Datos insuficientes para {ticker}: {len(feat_df)} < {window_size}")

    # Escalar igual que durante el entrenamiento
    scaler     = load_scaler(ticker)
    raw_window = feat_df[feature_cols].values[-window_size:]       # [window_size, n_feat]
    scaled     = scaler.transform(raw_window)                      # [window_size, n_feat]

    # Agregar ventana → vector tabular que el modelo XGBoost espera
    xgb_features = _build_xgb_features(scaled).reshape(1, -1)     # [1, 4*n_feat]

    # confidence_tau=0.36: si ninguna clase supera el 36% de confianza,
    # el modelo se abstiene en lugar de forzar una predicción sin convicción.
    # (Para 3 clases calibradas con Platt, el rango efectivo es ~0.33-0.49,
    #  por lo que 0.36 filtra predicciones casi aleatorias sin ser demasiado estricto)
    xgb = predict_xgboost(ticker, xgb_features, confidence_tau=0.36)

    direction_map = {0: "BAJISTA", 1: "LATERAL", 2: "ALCISTA"}
    trend = direction_map.get(xgb["direction"], "LATERAL")
    abstained = xgb.get("abstained", False)

    all_proba = xgb.get("all_proba", [0.33, 0.34, 0.33])

    # Volatilidad histórica 30d calculada de los datos ya descargados
    volatilidad_30d = None
    try:
        import math as _math
        import numpy as _np
        closes = feat_df["Close"].dropna().values.tolist()
        if len(closes) >= 10:
            log_ret = [_math.log(closes[i] / closes[i + 1]) for i in range(min(30, len(closes) - 1))]
            volatilidad_30d = round(float(_np.std(log_ret, ddof=1) * 100), 4)
    except Exception:
        pass

    return {
        "trend":          trend,
        "confidence":     xgb["confidence"],
        "current_price":  current_price,
        "abstained":      abstained,
        "volatilidad_30d": volatilidad_30d,
        "probabilidades_xgb": {
            "bajista":   round(float(xgb.get("probability_bajista", all_proba[0])), 4),
            "lateral":   round(float(xgb.get("probability_lateral", all_proba[1])), 4),
            "alcista":   round(float(xgb.get("probability_alcista", all_proba[2])), 4),
            "abstained": abstained,  # true = señal forzada a LATERAL por baja confianza
        },
    }


def log_daily_predictions(tickers: List[str] = None) -> Dict:
    """
    Genera y guarda la predicción de hoy para cada ticker usando XGBoost.

    Returns:
        {"logged": [...], "skipped": [...], "errors": [...]}
    """
    if tickers is None:
        tickers = TICKERS["stable"] + TICKERS["volatile"]

    today    = date.today()
    forecast = today + timedelta(days=3)

    logged, skipped, errors = [], [], []

    for ticker in tickers:
        try:
            import io, sys
            _stdout, sys.stdout = sys.stdout, io.StringIO()
            try:
                result = _get_xgboost_prediction(ticker)
            finally:
                sys.stdout = _stdout

            # Si el modelo se abstuvo (baja confianza), no loguear la predicción
            if result.get("abstained"):
                skipped.append(ticker)
                logger.info(f"[{ticker}] Abstención por baja confianza ({result['confidence']:.0%}), omitido.")
                continue

            record = {
                "ticker":             ticker,
                "fecha_prediccion":   today.isoformat(),
                "fecha_objetivo":     forecast.isoformat(),
                "tendencia_predicha": result["trend"],
                "confianza_ensemble": round(float(result["confidence"]), 4),
                "precio_entrada":     round(float(result["current_price"]), 4),
                "dias_horizonte":     3,
            }

            inserted = PredictionLogDAO.crear(record)
            if inserted:
                logged.append(ticker)
                logger.info(f"[{ticker}] Prediccion registrada: {result['trend']} ({result['confidence']:.0%})")
                # Mantener activos sincronizado con la señal fresca del día
                try:
                    from ..daos.activo_dao import ActivoDAO
                    ActivoDAO.actualizar(ticker, {
                        "senal_ia":        result["trend"],
                        "confianza_bygru":  round(float(result["confidence"]), 4),
                        "precio":           round(float(result["current_price"]), 4),
                    })
                except Exception as _upd_err:
                    logger.warning(f"[{ticker}] No se pudo actualizar activos: {_upd_err}")
            else:
                skipped.append(ticker)
                logger.info(f"[{ticker}] Ya registrado hoy, omitido.")

        except Exception as e:
            errors.append({"ticker": ticker, "error": str(e)})
            logger.error(f"[{ticker}] Error al loggear prediccion: {e}")

    summary = {"logged": logged, "skipped": skipped, "errors": errors}
    logger.info(
        f"Log diario completado: "
        f"nuevas={len(logged)} omitidas={len(skipped)} errores={len(errors)}"
    )
    return summary


# ── Resolver ───────────────────────────────────────────────────────────────────

def resolve_pending_predictions() -> Dict:
    """
    Resuelve todas las predicciones cuyo forecast_for_date ya ha pasado.

    Para cada predicción pendiente:
      1. Descarga el precio real en forecast_for_date.
      2. Calcula la tendencia real usando los mismos umbrales frozen.
      3. Compara con predicted_trend y marca correct=True/False.

    Returns:
        {"resolved": [...], "failed": [...]}
    """
    pendientes = PredictionLogDAO.obtener_pendientes_de_resolver()

    if not pendientes:
        logger.info("No hay predicciones pendientes de resolver.")
        return {"resolved": [], "failed": []}

    resolved, failed = [], []

    for pred in pendientes:
        ticker          = pred["ticker"]
        record_id       = pred["id"]
        price_entry     = float(pred["precio_entrada"])
        forecast_date   = date.fromisoformat(pred["fecha_objetivo"])
        predicted_trend = pred["tendencia_predicha"]

        # Precio real en la fecha de resolución
        price_exit, found = _get_actual_price(ticker, forecast_date)
        if not found or price_entry == 0:
            logger.warning(f"[{ticker}] Sin precio para {forecast_date} — omitido.")
            failed.append({"ticker": ticker, "id": record_id, "reason": "precio_no_disponible"})
            continue

        # Retorno logarítmico real
        import math
        actual_return = math.log(price_exit / price_entry)

        # Clasificar con umbrales frozen del ticker
        dn, up = _load_frozen_thresholds(ticker)
        actual_trend = _classify_return(actual_return, dn, up)

        correct = (actual_trend == predicted_trend)

        ok = PredictionLogDAO.resolver(
            record_id      = record_id,
            tendencia_real = actual_trend,
            precio_salida  = round(price_exit, 4),
            correcta       = correct,
        )

        if ok:
            resolved.append({
                "ticker":        ticker,
                "predicha":      predicted_trend,
                "real":          actual_trend,
                "correcta":      correct,
                "precio_entrada": price_entry,
                "precio_salida":  round(price_exit, 4),
                "retorno_real":   round(actual_return * 100, 2),
            })
            status = "✓" if correct else "✗"
            logger.info(
                f"[{ticker}] {status} {predicted_trend} → real: {actual_trend} "
                f"(retorno: {actual_return*100:.2f}%)"
            )
        else:
            failed.append({"ticker": ticker, "id": record_id, "reason": "db_error"})

    logger.info(
        f"Resolucion completada: resueltas={len(resolved)} fallidas={len(failed)}"
    )
    return {"resolved": resolved, "failed": failed}


# ── Stats combinadas ────────────────────────────────────────────────────────────

def get_reliability_stats(ticker: str, walk_forward_path: str = "docs/walk_forward_results.json") -> Dict:
    """
    Combina métricas de walk-forward (offline) con las predicciones live.

    Returns:
        {
          "ticker": str,
          "walk_forward": {"ba_mean": float, "ba_std": float, "f1_mean": float} | None,
          "live": {"total": int, "resueltas": int, "correctas": int, "accuracy": float|None},
          "baseline": 33.33,
          "señal": "FUERTE"|"MODERADA"|"DÉBIL"|"SIN_DATOS"
        }
    """
    import json, os

    # Walk-forward offline
    wf_data = None
    if os.path.exists(walk_forward_path):
        try:
            with open(walk_forward_path, encoding="utf-8") as f:
                wf = json.load(f)
            ticker_wf = wf.get("tickers", {}).get(ticker)
            if ticker_wf and "error" not in ticker_wf:
                wf_data = {
                    "ba_mean": ticker_wf["ba_mean"],
                    "ba_std":  ticker_wf["ba_std"],
                    "f1_mean": ticker_wf["f1_mean"],
                    "n_folds": ticker_wf["n_splits_done"],
                }
        except Exception as e:
            logger.warning(f"No se pudo leer walk_forward_results.json: {e}")

    # Live predictions
    live = PredictionLogDAO.stats_ticker(ticker)

    # Señal cualitativa basada en walk-forward BA (fuente más fiable con pocos live datos)
    señal = "SIN_DATOS"
    if wf_data:
        ba = wf_data["ba_mean"]
        if ba >= 38:
            señal = "FUERTE"
        elif ba >= 35:
            señal = "MODERADA"
        elif ba >= 33.3:
            señal = "DÉBIL"
        else:
            señal = "SIN_SEÑAL"

    return {
        "ticker":        ticker,
        "walk_forward":  wf_data,
        "live": {
            "total":     live.get("total_predicciones", 0),
            "resueltas": live.get("resueltas", 0),
            "correctas": live.get("correctas", 0),
            "accuracy":  live.get("live_accuracy"),
            "por_clase": live.get("por_clase", {}),
        },
        "baseline": 33.33,
        "señal":     señal,
    }
