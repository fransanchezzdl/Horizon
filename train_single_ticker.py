python train_single_ticker.py KO 2>&1 | tail -100#!/usr/bin/env python3
"""
Script para entrenar un único ticker manualmente.

Uso:
    python train_single_ticker.py KO
    python train_single_ticker.py AAPL
"""

import sys
import time
from datetime import timedelta
from backend.models.ensemble import train_ensemble, predict_ensemble
from backend.models.config import USE_SENTIMENT
from backend.services import activo_update_service


def train_single(ticker: str) -> None:
    """Entrena un ticker individual y guarda en BD si es posible."""
    
    print("=" * 70)
    print(f"🚀 Entrenando {ticker} manualmente")
    print(f"   Sentimiento: {'✅ Activado' if USE_SENTIMENT else '❌ Desactivado'}")
    print("=" * 70)
    
    start_time = time.time()
    
    try:
        # Entrenar ensemble
        print(f"\n📚 Paso 1: Entrenando ensemble para {ticker}...\n")
        metrics = train_ensemble(ticker)
        elapsed_train = time.time() - start_time
        
        print(f"\n✅ Entrenamiento completado en {elapsed_train:.1f}s")
        print(f"   Val Loss: {metrics['avg_val_loss']:.6f}")
        print(f"   Dir. Accuracy: {metrics['avg_directional_accuracy']:.2%}")
        print(f"   Threshold dinámico: ±{metrics['dynamic_threshold']:.4f}")
        
        # Si no usamos sentimiento, también guardar en BD
        if not USE_SENTIMENT:
            try:
                print(f"\n📊 Paso 2: Realizando predicción para {ticker}...\n")
                ensemble_pred = predict_ensemble(ticker)
                
                print(f"   Trend: {ensemble_pred['trend']}")
                print(f"   Confidence: {ensemble_pred['confidence']:.4f}")
                print(f"   Current Price: ${ensemble_pred['current_price']:.2f}")
                print(f"   Predicted Price: ${ensemble_pred['predicted_price']:.2f}")
                
                # Guardar en BD
                print(f"\n💾 Paso 3: Guardando en BD...\n")
                training_metrics_to_save = {
                    "avg_val_loss": metrics.get("avg_val_loss"),
                    "avg_directional_accuracy": metrics.get("avg_directional_accuracy"),
                    "avg_mae": metrics.get("avg_mae"),
                    "avg_rmse": metrics.get("avg_rmse"),
                    "dynamic_threshold": metrics.get("dynamic_threshold"),
                    "xgb_directional_accuracy": metrics.get("xgb_directional_accuracy"),
                }
                
                success = activo_update_service.guardar_datos_post_entrenamiento(
                    ticker,
                    ensemble_pred,
                    training_metrics_to_save
                )
                
                if success:
                    print(f"\n✅ ¡Datos guardados exitosamente en BD para {ticker}!")
                    
                    # Verificación adicional: leer de la BD para confirmar
                    try:
                        print(f"\n📋 Paso 4: Verificando datos en BD...\n")
                        from backend.services.activo_service import activo_service
                        activo_guardado = activo_service.obtener_activo(ticker)
                        
                        if activo_guardado:
                            print(f"✅ Verificación exitosa - Datos confirmados en BD:")
                            print(f"   • Precio: ${activo_guardado.get('precio', 'N/A')}")
                            print(f"   • Señal: {activo_guardado.get('senal_ia', 'N/A')}")
                            print(f"   • Confianza: {activo_guardado.get('confianza_bygru', 'N/A')}")
                            
                            grafico = activo_guardado.get('grafico_prediccion')
                            if grafico:
                                print(f"   • Gráfico/Métricas: guardado ({len(grafico)} campos)")
                        else:
                            print(f"⚠️ No se pudo leer {ticker} de BD después de guardar")
                    except Exception as e:
                        print(f"⚠️ Error verificando datos: {e}")
                else:
                    print(f"\n❌ Error al guardar en BD para {ticker}")
            
            except Exception as e:
                print(f"\n❌ Error en predicción/guardado: {e}")
                print("   El modelo se entrenó OK, pero no se guardó en BD")
                import traceback
                traceback.print_exc()
        
        total_elapsed = time.time() - start_time
        print("\n" + "=" * 70)
        print(f"✅ COMPLETADO en {str(timedelta(seconds=int(total_elapsed)))}")
        print("=" * 70)
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python train_single_ticker.py TICKER")
        print("Ejemplo: python train_single_ticker.py KO")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    train_single(ticker)
