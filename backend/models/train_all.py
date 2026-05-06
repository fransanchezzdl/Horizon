"""
Script de entrenamiento masivo del ensemble Horizon Predictor.

Entrena los 5 modelos BiGRU para cada ticker definido en config.py
y muestra un resumen final con métricas y tiempo total.

Uso:
    python -m backend.models.train_all
"""

import time
import sys
from datetime import timedelta, date
from typing import Dict

from .config import TICKERS, USE_SENTIMENT, get_tickers_from_database
from .ensemble import train_ensemble, predict_ensemble
from .train_stacking import train_stacking_metalearner


def main() -> None:
    """
    Punto de entrada del entrenamiento masivo.

    Itera sobre todos los tickers del catálogo (stable + volatile),
    entrena el ensemble para cada uno y muestra un resumen al final.
    
    Si sentiment_flag=false, también guarda los datos en la BD de Supabase
    usando las predicciones del ensemble.
    """
    # Cargar tickers desde BD si es posible, sino usar hardcoded
    print("📡 Intentando cargar tickers desde BD...")
    tickers_config = get_tickers_from_database()
    all_tickers = tickers_config["stable"] + tickers_config["volatile"]
    
    if not all_tickers:
        print("⚠️  No se cargaron tickers, usando configuración por defecto")
        all_tickers = TICKERS["stable"] + TICKERS["volatile"]
    total_start = time.time()
    results = []
    
    # Importar el servicio de actualización solo si NO estamos usando sentimiento
    if not USE_SENTIMENT:
        try:
            from ..services import ActivoUpdateService
            from ..daos import ActivoDAO
            from ..daos.prediction_log_dao import PredictionLogDAO
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
            
            # Entrenar meta-model de ensemble stacking (opcional, resiliente a errores)
            try:
                print(f"\n🔗 Entrenando Ensemble Stacking Meta-Model para {ticker}...")
                stacking_metrics = train_stacking_metalearner(ticker, verbose=True)
                metrics["stacking_available"] = True
                metrics["stacking_accuracy"] = stacking_metrics.get("accuracy", 0)
                print(f"   ✅ Stacking meta-model entrenado: {stacking_metrics['accuracy']:.2%}")
            except Exception as stacking_error:
                print(f"   ⚠️ Stacking no disponible: {stacking_error}")
                metrics["stacking_available"] = False
            
            # Si no usamos sentimiento, hacer predicciones y guardar en BD
            if use_db:
                try:
                    print(f"\n📊 Realizando predicción para {ticker}...")
                    ensemble_pred = predict_ensemble(ticker)
                    
                    # Guardar en BD con métricas del entrenamiento (clasificación)
                    training_metrics_to_save = {
                        "avg_val_loss": metrics.get("avg_val_loss"),
                        "avg_test_accuracy": metrics.get("avg_test_accuracy"),
                        "avg_f1_weighted": metrics.get("avg_f1_weighted"),
                        "dynamic_threshold": metrics.get("dynamic_threshold"),
                        "xgb_directional_accuracy": metrics.get("xgboost_metrics", {}).get("xgb_directional_accuracy"),
                        "xgb_precision_up": metrics.get("xgboost_metrics", {}).get("xgb_precision_up"),
                        "xgb_recall_up": metrics.get("xgboost_metrics", {}).get("xgb_recall_up"),
                    }
                    
                    # 🔧 IMPORTANTE: Reemplazar confianza por accuracy real
                    ensemble_pred_corrected = ensemble_pred.copy()
                    ensemble_pred_corrected["confidence"] = metrics.get("avg_test_accuracy", 0)
                    
                    success = ActivoUpdateService.guardar_datos_post_entrenamiento(
                        ticker,
                        ensemble_pred_corrected,
                        training_metrics_to_save
                    )

                    metrics["db_saved"] = success
                    if success:
                        print(f"💾 Datos guardados en BD para {ticker}")
                    else:
                        print(f"⚠️ Error al guardar en BD para {ticker}")

                    # Opción B: generar y guardar explicación XAI con el modelo recién entrenado
                    # Garantiza que xai_explicaciones siempre esté sincronizado con activos.senal_ia
                    try:
                        print(f"\n🔍 Generando explicación XAI para {ticker}...")
                        from ..scripts.backfill_xai import _generar_xai_para_fecha
                        from ..daos.explicacion_xai_dao import ExplicacionXAIDAO

                        xai_result = _generar_xai_para_fecha(ticker, date.today())
                        if xai_result is not None:
                            xai_ok = ExplicacionXAIDAO.crear(
                                ticker=ticker,
                                shap_valores=xai_result["shap_valores"],
                                shap_grafico=xai_result.get("shap_grafico", ""),
                                features_top20=xai_result["features_top20"],
                                contribucion_features=xai_result["contribucion_features"],
                                senal_prediccion=ensemble_pred_corrected.get("trend", "LATERAL"),
                                confianza_prediccion=float(ensemble_pred_corrected.get("confidence", 0)),
                                version_modelo="train_all",
                                seed_modelo=42,
                            )
                            if xai_ok:
                                print(f"   ✅ Explicación XAI guardada para {ticker}")
                            else:
                                print(f"   ⚠️ No se pudo guardar explicación XAI para {ticker}")
                        else:
                            print(f"   ⚠️ No se pudo generar explicación XAI para {ticker}")
                    except Exception as xai_err:
                        print(f"   ⚠️ Error en XAI post-entrenamiento para {ticker}: {xai_err}")

                    # Calcular y guardar live_accuracy_30d y volatilidad_30d
                    extra_update = {}

                    try:
                        stats = PredictionLogDAO.stats_ticker(ticker)
                        live_acc = stats.get("live_accuracy")
                        if live_acc is not None:
                            extra_update["live_accuracy_30d"] = float(live_acc)
                    except Exception as acc_err:
                        print(f"⚠️ No se pudo calcular live_accuracy_30d para {ticker}: {acc_err}")

                    if extra_update:
                        ActivoDAO.actualizar(ticker, extra_update)
                        print(f"   • Métricas extra guardadas: {list(extra_update.keys())}")
                
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
                xgb_acc = r.get("xgboost_metrics", {}).get("xgb_directional_accuracy")
                xgb_str = f"XGB Acc: {xgb_acc:.2%} | " if xgb_acc is not None else ""
                db_status = "💾" if r.get("db_saved") else "❌"
                print(
                    f"  ✅ {r['ticker']:10s} | "
                    f"Val Loss: {r['avg_val_loss']:.6f} | "
                    f"Test Acc: {r.get('avg_test_accuracy', 0):.2%} | "
                    f"F1: {r.get('avg_f1_weighted', 0):.4f} | "
                    f"{xgb_str}"
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