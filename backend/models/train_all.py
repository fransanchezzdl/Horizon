"""
Script de entrenamiento masivo del ensemble Horizon Predictor.

Entrena los 5 modelos BiGRU para cada ticker definido en config.py
y muestra un resumen final con métricas y tiempo total.

Uso:
    python -m backend.models.train_all
"""

import time
import sys
from datetime import timedelta
from typing import Dict

from .config import TICKERS, USE_SENTIMENT
from .ensemble import train_ensemble, predict_ensemble


def main() -> None:
    """
    Punto de entrada del entrenamiento masivo.

    Itera sobre todos los tickers del catálogo (stable + volatile),
    entrena el ensemble para cada uno y muestra un resumen al final.
    
    Si sentiment_flag=false, también guarda los datos en la BD de Supabase
    usando las predicciones del ensemble.
    """
    all_tickers = TICKERS["stable"] + TICKERS["volatile"]
    total_start = time.time()
    results = []
    
    # Importar el servicio de actualización solo si NO estamos usando sentimiento
    if not USE_SENTIMENT:
        try:
            from ..services import ActivoUpdateService
            use_db = True
            print("✅ Guardado en BD activado (sentiment=false)")
        except Exception as e:
            print(f"⚠️ No se puede usar BD: {e}")
            use_db = False
    else:
        use_db = False
        print("ℹ️  Guardado en BD desactivado (sentiment=true)")

    print("=" * 60)
    print("🌅 HORIZON — Entrenamiento masivo del ensemble BiGRU + XGBoost")
    print(f"   Tickers: {all_tickers}")
    print(f"   Sentimiento FinBERT: {'✅ Activado' if USE_SENTIMENT else '❌ Desactivado'}")
    print("=" * 60)

    for ticker in all_tickers:
        ticker_start = time.time()
        try:
            # Entrenar ensemble
            metrics = train_ensemble(ticker)
            elapsed = time.time() - ticker_start
            metrics["elapsed_seconds"] = elapsed
            metrics["status"] = "OK"
            
            # Si no usamos sentimiento, hacer predicciones y guardar en BD
            if use_db:
                try:
                    print(f"\n📊 Realizando predicción para {ticker}...")
                    ensemble_pred = predict_ensemble(ticker)
                    
                    # Guardar en BD con métricas del entrenamiento
                    training_metrics_to_save = {
                        "avg_val_loss": metrics.get("avg_val_loss"),
                        "avg_directional_accuracy": metrics.get("avg_directional_accuracy"),
                        "avg_mae": metrics.get("avg_mae"),
                        "avg_rmse": metrics.get("avg_rmse"),
                        "dynamic_threshold": metrics.get("dynamic_threshold"),
                        "xgb_directional_accuracy": metrics.get("xgb_directional_accuracy"),
                    }
                    
                    success = ActivoUpdateService.guardar_datos_post_entrenamiento(
                        ticker,
                        ensemble_pred,
                        training_metrics_to_save
                    )
                    
                    metrics["db_saved"] = success
                    if success:
                        print(f"💾 Datos guardados en BD para {ticker}")
                    else:
                        print(f"⚠️ Error al guardar en BD para {ticker}")
                
                except Exception as pred_error:
                    print(f"⚠️ Error en predicción/guardado para {ticker}: {pred_error}")
                    metrics["db_saved"] = False
        
        except Exception as exc:
            elapsed = time.time() - ticker_start
            print(f"❌ Error entrenando {ticker}: {exc}")
            metrics = {
                "ticker": ticker,
                "status": "ERROR",
                "error": str(exc),
                "elapsed_seconds": elapsed,
                "db_saved": False,
            }
        results.append(metrics)

    total_elapsed = time.time() - total_start

    # ── Resumen final ──────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("📋 RESUMEN FINAL")
    print("=" * 60)
    for r in results:
            if r["status"] == "OK":
                threshold_str = (
                    f"Threshold: ±{r['dynamic_threshold']:.4f} | "
                    if r.get("dynamic_threshold") is not None
                    else ""
                )
                xgb_acc = r.get("xgb_directional_accuracy")
                xgb_str = f"XGB Acc: {xgb_acc:.2%} | " if xgb_acc is not None else ""
                db_status = "💾" if r.get("db_saved") else "❌"
                print(
                    f"  ✅ {r['ticker']:10s} | "
                    f"Val Loss: {r['avg_val_loss']:.6f} | "
                    f"Dir. Acc: {r['avg_directional_accuracy']:.2%} | "
                    f"{xgb_str}"
                    f"Prec↑: {r.get('avg_precision_up', 0):.2%} | "
                    f"Rec↑: {r.get('avg_recall_up', 0):.2%} | "
                    f"{threshold_str}"
                    f"Tiempo: {r['elapsed_seconds']:.1f}s {db_status}"
                )
            else:
                print(f"  ❌ {r['ticker']:10s} | ERROR: {r.get('error', 'desconocido')}")

    print("-" * 60)
    print(f"⏱️  Tiempo total: {str(timedelta(seconds=int(total_elapsed)))}")
    print("=" * 60)


if __name__ == "__main__":
    main()