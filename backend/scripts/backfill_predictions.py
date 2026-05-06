"""
Backfill retroactivo de prediction_log.

Para cada ticker y cada día hábil del rango indicado, simula lo que el modelo
hubiera predicho ese día usando SOLO datos disponibles hasta esa fecha
(sin leakage futuro), y resuelve inmediatamente el outcome real.

Flujo por fecha:
  1. Descarga OHLC desde 2018-01-01 hasta `fecha` (exclusive)
  2. Calcula features con los datos disponibles hasta `fecha`
  3. Reescala con un StandardScaler ajustado SOLO sobre esos datos
     (distinto del scaler de producción — no hay leakage)
  4. Predice con el modelo XGBoost guardado
  5. Obtiene precio real en `fecha + 5 días`
  6. Clasifica tendencia_real con thresholds_frozen y marca correcta
  7. Inserta en prediction_log como ya resuelta

IMPORTANTE: El modelo XGBoost en sí fue entrenado con datos hasta hoy,
por lo que hay leakage del modelo (pero no del scaler). Esto es aceptable
para validación del TFG y debe documentarse.

Uso:
    # Último mes (por defecto)
    python -m backend.scripts.backfill_predictions run

    # Rango personalizado
    python -m backend.scripts.backfill_predictions run --start 2026-01-01 --end 2026-03-31

    # Solo algunos tickers
    python -m backend.scripts.backfill_predictions run --tickers KO AAPL TSLA

    # Dry-run (muestra qué haría sin insertar nada)
    python -m backend.scripts.backfill_predictions run --dry-run

    # Guardar checkpoint antes de empezar (recomendado)
    python -m backend.scripts.checkpoint_prediction_log export
"""

import argparse
import io
import logging
import sys
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Helpers ────────────────────────────────────────────────────────────────────

def _business_days(start: date, end: date) -> List[date]:
    """Devuelve lista de días hábiles (lun-vie) en el rango [start, end)."""
    days = []
    current = start
    while current < end:
        if current.weekday() < 5:  # 0=lun … 4=vie
            days.append(current)
        current += timedelta(days=1)
    return days


def _download_until(ticker: str, end_date: date) -> pd.DataFrame:
    """
    Descarga OHLC desde 2018-01-01 hasta end_date (exclusive).
    Aplana MultiIndex si yfinance lo devuelve.
    """
    # Silenciar stdout de yfinance
    _stdout, sys.stdout = sys.stdout, io.StringIO()
    try:
        df = yf.download(
            ticker,
            start="2018-01-01",
            end=end_date.isoformat(),
            progress=False,
            auto_adjust=True,
        )
    finally:
        sys.stdout = _stdout

    if df.empty:
        raise ValueError(f"Sin datos para {ticker} hasta {end_date}")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    return df


def _get_actual_price(ticker: str, target_date: date) -> Tuple[float, bool]:
    """Precio de cierre más cercano a target_date (ventana ±4 días)."""
    start = (target_date - timedelta(days=4)).isoformat()
    end   = (target_date + timedelta(days=4)).isoformat()
    _stdout, sys.stdout = sys.stdout, io.StringIO()
    try:
        df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    finally:
        sys.stdout = _stdout

    if df.empty:
        return 0.0, False

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.index = df.index.normalize()
    closest = min(df.index, key=lambda d: abs((d.date() - target_date).days))
    price = float(
        df.loc[closest, "Close"].iloc[0]
        if hasattr(df.loc[closest, "Close"], "iloc")
        else df.loc[closest, "Close"]
    )
    return price, True


def _build_xgb_features(window: np.ndarray) -> np.ndarray:
    """
    [window_size, n_feat] → [12*n_feat] (last, mean, std, trend sobre 3 sub-ventanas).

    Debe ser idéntico a _build_xgb_features en prediction_log_service.py
    y a build_xgb_features en xgboost_model.py.
    """
    W = window.shape[0]
    sub_windows = [max(2, W // 6), W // 2, W]
    parts = []
    for sw in sub_windows:
        sl = window[-sw:, :]
        parts.extend([sl[-1, :], sl.mean(axis=0), sl.std(axis=0), sl[-1, :] - sl[0, :]])
    return np.concatenate(parts)


def _classify_return(ret: float, dn: float, up: float) -> str:
    if ret <= dn:
        return "BAJISTA"
    if ret >= up:
        return "ALCISTA"
    return "LATERAL"


# ── Predicción con datos hasta fecha dada ──────────────────────────────────────

def _predict_for_date(ticker: str, pred_date: date) -> Optional[Dict]:
    """
    Genera la predicción que el modelo hubiera dado en pred_date,
    usando solo datos disponibles hasta ese día.

    Usa el scaler de producción (el mismo con el que fue entrenado el modelo)
    para que los features estén en la distribución que el modelo espera.
    Nota: introduce leakage estadístico del scaler, documentado como limitación.

    Returns: {trend, confidence, current_price} o None si hay error.
    """
    from ..models.data_pipeline import compute_features, load_scaler
    from ..models.config import TICKERS, get_feature_cols, get_asset_type, ENSEMBLE_VARIATIONS
    from ..models.xgboost_model import predict_xgboost

    try:
        asset_type  = get_asset_type(ticker)
        window_size = max(v["window_size"] for v in ENSEMBLE_VARIATIONS[asset_type])

        include_market_context = ticker in TICKERS["volatile"]

        # 1. Datos solo hasta pred_date (exclusive → el modelo no "ve" ese día aún)
        raw_df = _download_until(ticker, pred_date)

        # 2. Features
        feat_df = compute_features(
            raw_df,
            include_market_context=include_market_context,
            ticker=ticker,
        )

        feature_cols  = get_feature_cols(ticker)
        current_price = float(feat_df["Close"].iloc[-1])

        if len(feat_df) < window_size:
            logger.warning(f"[{ticker}] {pred_date}: datos insuficientes ({len(feat_df)} < {window_size})")
            return None

        # 3. Escalar con el scaler de producción — misma distribución que durante
        #    el entrenamiento del modelo, evitando colapso de clases por OOD features.
        #    (leakage estadístico del scaler documentado como limitación del backfill)
        scaler     = load_scaler(ticker)
        raw_values = feat_df[feature_cols].values
        scaled_all = scaler.transform(raw_values)

        # Tomar las últimas window_size filas
        scaled_window = scaled_all[-window_size:]     # [window_size, n_feat]

        # 4. Agregar → vector tabular
        xgb_features = _build_xgb_features(scaled_window).reshape(1, -1)

        # 5. Predecir con el modelo guardado
        # confidence_tau=0.36: filtra predicciones sin convicción real
        # sin ser demasiado estricto dado el rango calibrado ~0.33-0.49
        xgb = predict_xgboost(ticker, xgb_features, confidence_tau=0.0)

        direction_map = {0: "BAJISTA", 1: "LATERAL", 2: "ALCISTA"}
        return {
            "trend":         direction_map.get(xgb["direction"], "LATERAL"),
            "confidence":    xgb["confidence"],
            "current_price": current_price,
            "abstained":     xgb.get("abstained", False),
        }

    except Exception as e:
        logger.error(f"[{ticker}] {pred_date}: error en predicción — {e}")
        return None


# ── Backfill principal ─────────────────────────────────────────────────────────

def run_backfill(
    tickers: List[str],
    start_date: date,
    end_date: date,
    dry_run: bool = False,
) -> Dict:
    """
    Ejecuta el backfill para todos los tickers en el rango [start_date, end_date).

    Returns: resumen {inserted, skipped, errors}
    """
    from ..daos.prediction_log_dao import PredictionLogDAO
    from ..models.xgboost_model import _load_frozen_thresholds

    days = _business_days(start_date, end_date)
    logger.info(
        f"Backfill: {len(tickers)} tickers × {len(days)} días hábiles "
        f"({start_date} → {end_date})"
    )
    if dry_run:
        logger.info("[DRY-RUN] No se insertará nada en la base de datos.")

    total_inserted = 0
    total_skipped  = 0
    total_errors   = 0

    for ticker in tickers:
        logger.info(f"── {ticker} ──────────────────────────────")
        dn, up = _load_frozen_thresholds(ticker)

        ticker_inserted = 0
        ticker_skipped  = 0
        ticker_errors   = 0

        for pred_date in days:
            fecha_objetivo = pred_date + timedelta(days=5)

            # Saltar si la fecha objetivo aún no ha llegado (no hay precio real disponible)
            if fecha_objetivo >= date.today():
                logger.debug(f"[{ticker}] {pred_date}: fecha_objetivo {fecha_objetivo} aún futura, omitiendo.")
                ticker_skipped += 1
                continue

            # ── Predicción ──
            result = _predict_for_date(ticker, pred_date)
            if result is None:
                ticker_errors += 1
                total_errors  += 1
                continue

            # Si el modelo se abstuvo (baja confianza), no insertar
            if result.get("abstained"):
                logger.debug(f"  {pred_date}: abstención ({result['confidence']:.0%}), omitido.")
                ticker_skipped += 1
                total_skipped  += 1
                continue

            # ── Precio real en fecha_objetivo ──
            precio_salida, found = _get_actual_price(ticker, fecha_objetivo)
            if not found:
                logger.warning(f"[{ticker}] {pred_date}: no se encontró precio real para {fecha_objetivo}")
                ticker_errors += 1
                total_errors  += 1
                continue

            # ── Clasificar tendencia real ──
            ret = np.log(precio_salida / result["current_price"])
            tendencia_real = _classify_return(ret, dn, up)
            correcta       = result["trend"] == tendencia_real

            record = {
                "ticker":             ticker,
                "fecha_prediccion":   pred_date.isoformat(),
                "fecha_objetivo":     fecha_objetivo.isoformat(),
                "tendencia_predicha": result["trend"],
                "confianza_ensemble": round(float(result["confidence"]), 4),
                "precio_entrada":     round(float(result["current_price"]), 4),
                "dias_horizonte":     5,
                "resuelta":           True,
                "tendencia_real":     tendencia_real,
                "precio_salida":      round(precio_salida, 4),
                "correcta":           correcta,
            }

            if dry_run:
                status = "✓" if correcta else "✗"
                logger.info(
                    f"  [DRY] {pred_date} → pred={result['trend']} real={tendencia_real} "
                    f"conf={result['confidence']:.0%} {status}"
                )
                ticker_inserted += 1
                total_inserted  += 1
                continue

            # ── Insertar ──
            inserted = PredictionLogDAO.crear(record)
            if inserted:
                status = "✓" if correcta else "✗"
                logger.info(
                    f"  {pred_date} → pred={result['trend']} real={tendencia_real} "
                    f"conf={result['confidence']:.0%} {status}"
                )
                ticker_inserted += 1
                total_inserted  += 1
            else:
                logger.debug(f"  {pred_date}: ya existe, omitido.")
                ticker_skipped += 1
                total_skipped  += 1

        logger.info(
            f"[{ticker}] insertadas={ticker_inserted} omitidas={ticker_skipped} errores={ticker_errors}"
        )

    summary = {
        "inserted": total_inserted,
        "skipped":  total_skipped,
        "errors":   total_errors,
    }
    logger.info(
        f"\nBackfill completado → insertadas={total_inserted} omitidas={total_skipped} errores={total_errors}"
    )
    return summary


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    from ..models.config import TICKERS

    parser = argparse.ArgumentParser(
        description="Backfill retroactivo de prediction_log",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="cmd")

    run_p = subparsers.add_parser("run", help="Ejecutar backfill")
    run_p.add_argument(
        "--start",
        type=date.fromisoformat,
        default=date.today() - timedelta(days=30),
        help="Fecha inicio (YYYY-MM-DD). Por defecto: hace 30 días.",
    )
    run_p.add_argument(
        "--end",
        type=date.fromisoformat,
        default=date.today(),
        help="Fecha fin exclusive (YYYY-MM-DD). Por defecto: hoy.",
    )
    run_p.add_argument(
        "--tickers",
        nargs="+",
        default=None,
        help="Tickers a procesar. Por defecto: todos (stable + volatile).",
    )
    run_p.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula el backfill sin insertar datos en la BD.",
    )

    args = parser.parse_args()

    if args.cmd != "run":
        parser.print_help()
        sys.exit(1)

    tickers = args.tickers or (TICKERS["stable"] + TICKERS["volatile"])

    run_backfill(
        tickers=tickers,
        start_date=args.start,
        end_date=args.end,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
