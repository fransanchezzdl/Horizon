"""
Calibración ÚNICA de umbrales de etiquetado por ticker.

Concepto:
    En lugar de umbrales dinámicos (que cambian en cada reentrenamiento) o
    universales fijos (que ignoran la volatilidad propia de cada activo),
    calculamos UNA SOLA VEZ los percentiles 33 y 67 de los retornos log a 5
    días sobre la PORCIÓN train de los datos históricos. Esos umbrales se
    versionan en `thresholds_frozen.json` y NO se modifican en futuros
    reentrenamientos.

Ventajas para defensa de TFG:
    - Reproducibilidad 100%: el mismo retorno → siempre el mismo label.
    - Adaptado a la volatilidad real del activo (BTC tendrá umbrales ~6%,
      KO tendrá ~1%).
    - Sin overfitting: el umbral no se optimiza contra ninguna métrica.
    - Auditable: el archivo está en git, con timestamp de calibración.

Uso:
    python -m backend.models.calibrate_thresholds

    # Para forzar recalibración (NO hacer en producción salvo causa justificada):
    python -m backend.models.calibrate_thresholds --force
"""

import argparse
import json
import os
import sys
from datetime import datetime

import numpy as np

from .config import TICKERS, get_config
from .data_pipeline import prepare_data_multi_window

THRESHOLDS_FILE = os.path.join(os.path.dirname(__file__), "thresholds_frozen.json")
PERCENTILE_LOWER = 33.33
PERCENTILE_UPPER = 66.67


def calibrate_ticker(ticker: str) -> dict:
    """
    Compute frozen thresholds for one ticker using TRAIN portion of returns.

    Returns dict with bajista/alcista thresholds and metadata for that ticker.
    """
    config = get_config(ticker)
    window_size = config["window_size"]
    all_data = prepare_data_multi_window(ticker, config, [window_size])
    data = all_data[window_size]

    y_train_returns = np.asarray(data["y_train_returns"]).ravel()
    n_samples = len(y_train_returns)

    bajista = float(np.percentile(y_train_returns, PERCENTILE_LOWER))
    alcista = float(np.percentile(y_train_returns, PERCENTILE_UPPER))

    return {
        "bajista": round(bajista, 6),
        "alcista": round(alcista, 6),
        "n_train_samples": n_samples,
        "min_return": round(float(np.min(y_train_returns)), 6),
        "max_return": round(float(np.max(y_train_returns)), 6),
        "std_return": round(float(np.std(y_train_returns)), 6),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recalibrar incluso si el archivo ya existe",
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=None,
        help="Lista específica de tickers a calibrar (default: todos)",
    )
    args = parser.parse_args()

    if os.path.exists(THRESHOLDS_FILE) and not args.force:
        print(f"[SKIP] {THRESHOLDS_FILE} ya existe.")
        print("Usa --force para recalibrar (perderás reproducibilidad histórica).")
        sys.exit(0)

    all_tickers = args.tickers or (TICKERS["stable"] + TICKERS["volatile"])
    print(f"\n[CALIBRATE] Calibrando umbrales fijos para {len(all_tickers)} tickers")
    print(f"            Método: percentiles {PERCENTILE_LOWER}/{PERCENTILE_UPPER} sobre train")
    print(f"            Output: {THRESHOLDS_FILE}\n")

    results = {
        "_meta": {
            "version": "1.0",
            "calibrated_at": datetime.now().isoformat(),
            "method": f"percentile_{PERCENTILE_LOWER}_{PERCENTILE_UPPER}",
            "horizon_days": 3,
            "split": "train_only_70pct",
            "description": (
                "Umbrales fijos de etiquetado calibrados UNA SOLA VEZ sobre la "
                "portion train de retornos log a 3 días (cambiado de 5d tras "
                "comparativa empírica walk-forward 2026-04-13). NO MODIFICAR: la "
                "reproducibilidad del modelo depende de que estos valores sean "
                "inmutables. Si se necesita recalibrar, hacer en una nueva "
                "version del modelo."
            ),
        }
    }

    failed = []
    for ticker in all_tickers:
        try:
            print(f"[*] {ticker}...")
            cal = calibrate_ticker(ticker)
            results[ticker] = cal
            print(
                f"    BAJISTA={cal['bajista']:+.4f} ({cal['bajista']*100:+.2f}%) | "
                f"ALCISTA={cal['alcista']:+.4f} ({cal['alcista']*100:+.2f}%) | "
                f"std={cal['std_return']:.4f} | n={cal['n_train_samples']}"
            )
        except Exception as e:
            print(f"    [ERROR] {ticker}: {e}")
            failed.append(ticker)

    with open(THRESHOLDS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[OK] Guardado en {THRESHOLDS_FILE}")
    print(f"     Calibrados: {len(results) - 1}/{len(all_tickers)}")
    if failed:
        print(f"     Fallidos: {failed}")
        sys.exit(1)


if __name__ == "__main__":
    main()
