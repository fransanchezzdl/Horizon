"""
Backfill retroactivo de xai_explicaciones.

Para cada ticker y cada semana del rango indicado, genera la explicación SHAP
que el modelo hubiera producido ese día usando SOLO datos disponibles hasta
esa fecha (sin leakage futuro de datos, aunque el modelo sí fue entrenado con
datos posteriores — misma limitación documentada que backfill_predictions.py).

Uso:
    # Últimos 90 días (por defecto)
    python -m backend.scripts.backfill_xai run

    # Rango personalizado
    python -m backend.scripts.backfill_xai run --start 2026-01-01 --end 2026-04-19

    # Solo algunos tickers
    python -m backend.scripts.backfill_xai run --tickers AAPL MSFT

    # Dry-run (muestra qué haría sin insertar nada)
    python -m backend.scripts.backfill_xai run --dry-run
"""

import argparse
import io
import json
import logging
import os
import pickle
import sys
from datetime import date, timedelta
from typing import Dict, List, Optional

import numpy as np
import yfinance as yf

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _fridays(start: date, end: date) -> List[date]:
    """Devuelve los viernes (día 4) en el rango [start, end)."""
    days = []
    current = start
    while current < end:
        if current.weekday() == 4:
            days.append(current)
        current += timedelta(days=1)
    return days


def _download_until(ticker: str, end_date: date) -> "pd.DataFrame":
    import pandas as pd
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
    if isinstance(df.columns, __import__("pandas").MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def _build_xgb_features(window: np.ndarray) -> np.ndarray:
    """
    Replica build_xgb_features de xgboost_model.py:
    3 sub-ventanas × 4 agregaciones = 12 * n_features.
    """
    W = window.shape[0]
    sub_windows = [max(2, W // 6), W // 2, W]
    parts = []
    for sw in sub_windows:
        sl = window[-sw:, :]
        parts.extend([
            sl[-1, :],
            sl.mean(axis=0),
            sl.std(axis=0),
            sl[-1, :] - sl[0, :],
        ])
    return np.concatenate(parts)


# ── Generación de explicación XAI para una fecha ──────────────────────────────

def _generar_xai_para_fecha(ticker: str, pred_date: date) -> Optional[Dict]:
    """
    Genera la explicación SHAP que el modelo hubiera dado en pred_date,
    usando solo datos disponibles hasta ese día.

    Returns: dict con shap_valores, features_top20, contribucion_features,
             senal_prediccion, confianza_prediccion — o None si hay error.
    """
    from ..models.config import (
        get_asset_type, get_feature_cols, get_config, SAVED_MODELS_DIR,
    )
    from ..models.data_pipeline import compute_features
    from ..models.xai_explanation_engine import XAIEngine
    from ..models.platt_scaling_calibration_v2 import load_calibrator

    try:
        config     = get_config(ticker)
        asset_type = get_asset_type(ticker)
        feature_cols = get_feature_cols(ticker)
        window_size  = config.get("window_size", 30)

        # 1. Datos hasta pred_date
        raw_df = _download_until(ticker, pred_date)
        include_ctx = (asset_type == "volatile")
        feat_df = compute_features(raw_df, include_market_context=include_ctx, ticker=ticker)

        feature_cols = [c for c in feature_cols if c in feat_df.columns]

        if len(feat_df) < window_size:
            logger.warning(f"[{ticker}] {pred_date}: datos insuficientes")
            return None

        # 2. Scaler de producción
        scaler_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_scaler.pkl")
        if not os.path.exists(scaler_path):
            logger.warning(f"[{ticker}] scaler no encontrado")
            return None
        with open(scaler_path, "rb") as f:
            scaler = pickle.load(f)

        # Si el scaler espera más features que las disponibles, recomputar con contexto de mercado
        if hasattr(scaler, "n_features_in_") and scaler.n_features_in_ != len(feature_cols):
            feat_df = compute_features(raw_df, include_market_context=True, ticker=ticker)
            feature_cols = [c for c in get_feature_cols(ticker) if c in feat_df.columns]

        last_window_raw    = feat_df[feature_cols].values[-window_size:]
        last_window_scaled = scaler.transform(last_window_raw)

        # 3. Construir vector tabular (3 sub-ventanas × 4 agregaciones)
        X_test = _build_xgb_features(last_window_scaled).reshape(1, -1).astype(np.float32)

        # 4. Modelo XGBoost
        xgb_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost.pkl")
        if not os.path.exists(xgb_path):
            logger.warning(f"[{ticker}] modelo xgboost no encontrado")
            return None
        with open(xgb_path, "rb") as f:
            xgb_model = pickle.load(f)

        y_pred  = xgb_model.predict(X_test)[0]
        y_proba = xgb_model.predict_proba(X_test)[0]

        senal = {0: "BAJISTA", 1: "LATERAL", 2: "ALCISTA"}.get(int(y_pred), "LATERAL")

        calibrator = load_calibrator(ticker)
        if calibrator is not None:
            raw_conf   = np.max(y_proba).reshape(1, 1)
            confianza  = float(calibrator.predict_proba(raw_conf)[0, 1])
        else:
            confianza = float(np.max(y_proba))

        # 5. Feature names (fallback si no existe el pkl)
        feat_names_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_feature_names.pkl")
        if os.path.exists(feat_names_path):
            with open(feat_names_path, "rb") as f:
                feature_names = pickle.load(f)
        else:
            W = window_size
            sub_windows = [max(2, W // 6), W // 2, W]
            feature_names = []
            for sw in sub_windows:
                feature_names += (
                    [f"{c}_sw{sw}_last"  for c in feature_cols] +
                    [f"{c}_sw{sw}_mean"  for c in feature_cols] +
                    [f"{c}_sw{sw}_std"   for c in feature_cols] +
                    [f"{c}_sw{sw}_trend" for c in feature_cols]
                )

        # 6. XAI Engine — genera SHAP values
        xai_engine = XAIEngine(xgb_model=xgb_model, feature_names=feature_names)
        explicacion = xai_engine.explain_prediction(
            X_instance=X_test[0],
            ticker=ticker,
            senal_prediccion=senal,
            confianza=confianza,
            feature_names=feature_names,
        )

        return {
            "shap_valores":        explicacion.get("shap_valores", []),
            "shap_grafico":        explicacion.get("shap_grafico_base64", ""),
            "features_top20":      explicacion.get("features_top20", []),
            "contribucion_features": explicacion.get("contribucion_features", {}),
            "senal_prediccion":    senal,
            "confianza_prediccion": confianza,
        }

    except Exception as e:
        logger.error(f"[{ticker}] {pred_date}: error — {e}")
        return None


# ── Backfill principal ─────────────────────────────────────────────────────────

def run_backfill(
    tickers: List[str],
    start_date: date,
    end_date: date,
    dry_run: bool = False,
) -> Dict:
    from ..daos.explicacion_xai_dao import ExplicacionXAIDAO

    weeks = _fridays(start_date, end_date)
    logger.info(
        f"Backfill XAI: {len(tickers)} tickers × {len(weeks)} semanas "
        f"({start_date} → {end_date})"
    )
    if dry_run:
        logger.info("[DRY-RUN] No se insertará nada en la base de datos.")

    total_inserted = 0
    total_skipped  = 0
    total_errors   = 0

    for ticker in tickers:
        logger.info(f"── {ticker} ──────────────────────────────")
        ticker_inserted = ticker_skipped = ticker_errors = 0

        for pred_date in weeks:
            if pred_date >= date.today():
                ticker_skipped += 1
                total_skipped  += 1
                continue

            result = _generar_xai_para_fecha(ticker, pred_date)
            if result is None:
                ticker_errors += 1
                total_errors  += 1
                continue

            if dry_run:
                logger.info(
                    f"  [DRY] {pred_date} → {result['senal_prediccion']} "
                    f"conf={result['confianza_prediccion']:.0%} "
                    f"shap_features={len(result['shap_valores'])}"
                )
                ticker_inserted += 1
                total_inserted  += 1
                continue

            success = ExplicacionXAIDAO.crear(
                ticker=ticker,
                shap_valores=result["shap_valores"],
                shap_grafico=result["shap_grafico"],
                features_top20=result["features_top20"],
                contribucion_features=result["contribucion_features"],
                senal_prediccion=result["senal_prediccion"],
                confianza_prediccion=result["confianza_prediccion"],
                version_modelo="backfill",
                seed_modelo=42,
                fecha_prediccion=pred_date.isoformat(),
            )

            if success:
                logger.info(
                    f"  {pred_date} → {result['senal_prediccion']} "
                    f"conf={result['confianza_prediccion']:.0%}"
                )
                ticker_inserted += 1
                total_inserted  += 1
            else:
                logger.debug(f"  {pred_date}: ya existe o error al insertar, omitido.")
                ticker_skipped += 1
                total_skipped  += 1

        logger.info(
            f"[{ticker}] insertadas={ticker_inserted} omitidas={ticker_skipped} errores={ticker_errors}"
        )

    summary = {"inserted": total_inserted, "skipped": total_skipped, "errors": total_errors}
    logger.info(
        f"\nBackfill XAI completado → insertadas={total_inserted} "
        f"omitidas={total_skipped} errores={total_errors}"
    )
    return summary


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    from ..models.config import TICKERS, get_tickers_from_database  # noqa: F401 (TICKERS solo como fallback)

    parser = argparse.ArgumentParser(
        description="Backfill retroactivo de xai_explicaciones",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="cmd")

    run_p = subparsers.add_parser("run", help="Ejecutar backfill")
    run_p.add_argument(
        "--start",
        type=date.fromisoformat,
        default=date.today() - timedelta(days=90),
        help="Fecha inicio (YYYY-MM-DD). Por defecto: hace 90 días.",
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
        help="Tickers a procesar. Por defecto: todos.",
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

    from ..models.config import get_tickers_from_database
    if args.tickers:
        tickers = args.tickers
    else:
        tickers_config = get_tickers_from_database()
        tickers = tickers_config["stable"] + tickers_config["volatile"]
        if not tickers:
            tickers = TICKERS["stable"] + TICKERS["volatile"]
            logger.warning("BD sin tickers — usando config hardcoded")
    run_backfill(
        tickers=tickers,
        start_date=args.start,
        end_date=args.end,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
