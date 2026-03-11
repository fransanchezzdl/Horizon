"""
Script de entrenamiento masivo del ensemble Horizon Predictor.

Entrena los 5 modelos BiGRU para cada ticker definido en config.py
y muestra un resumen final con métricas y tiempo total.

Uso:
    python -m backend.models.train_all
"""

import time
from datetime import timedelta

from .config import TICKERS
from .ensemble import train_ensemble


def main() -> None:
    """
    Punto de entrada del entrenamiento masivo.

    Itera sobre todos los tickers del catálogo (stable + volatile),
    entrena el ensemble para cada uno y muestra un resumen al final.
    """
    all_tickers = TICKERS["stable"] + TICKERS["volatile"]
    total_start = time.time()
    results = []

    print("=" * 60)
    print("🌅 HORIZON — Entrenamiento masivo del ensemble BiGRU + XGBoost")
    print(f"   Tickers: {all_tickers}")
    from .config import USE_SENTIMENT
    print(f"   Sentimiento FinBERT: {'✅ Activado' if USE_SENTIMENT else '❌ Desactivado'}")
    print("=" * 60)

    for ticker in all_tickers:
        ticker_start = time.time()
        try:
            metrics = train_ensemble(ticker)
            elapsed = time.time() - ticker_start
            metrics["elapsed_seconds"] = elapsed
            metrics["status"] = "OK"
        except Exception as exc:
            elapsed = time.time() - ticker_start
            print(f"❌ Error entrenando {ticker}: {exc}")
            metrics = {
                "ticker": ticker,
                "status": "ERROR",
                "error": str(exc),
                "elapsed_seconds": elapsed,
            }
        results.append(metrics)

    total_elapsed = time.time() - total_start

    # ── Resumen final ──────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("📋 RESUMEN FINAL")
    print("=" * 60)
    for r in results:
        if r["status"] == "OK":
            xgb_acc = r.get("xgb_directional_accuracy")
            xgb_str = f"XGB Acc: {xgb_acc:.2%} | " if xgb_acc is not None else ""
            print(
                f"  ✅ {r['ticker']:10s} | "
                f"Val Loss: {r['avg_val_loss']:.6f} | "
                f"Dir. Acc: {r['avg_directional_accuracy']:.2%} | "
                f"{xgb_str}"
                f"Prec↑: {r.get('avg_precision_up', 0):.2%} | "
                f"Rec↑: {r.get('avg_recall_up', 0):.2%} | "
                f"Tiempo: {r['elapsed_seconds']:.1f}s"
            )
        else:
            print(f"  ❌ {r['ticker']:10s} | ERROR: {r.get('error', 'desconocido')}")

    print("-" * 60)
    print(f"⏱️  Tiempo total: {str(timedelta(seconds=int(total_elapsed)))}")
    print("=" * 60)


if __name__ == "__main__":
    main()
