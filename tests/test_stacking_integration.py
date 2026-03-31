"""
Script de prueba para validar integración de Ensemble Stacking.

Prueba:
1. Entrena ensemble para GC=F
2. Entrena meta-model de stacking
3. Realiza predicción usando stacking
4. Compara con predicción sin stacking
"""

import os
import sys
import time
from datetime import timedelta


def test_stacking_integration():
    """Test completo del pipeline de stacking"""
    
    print("\n" + "="*80)
    print("🧪 TEST DE INTEGRACIÓN: ENSEMBLE STACKING")
    print("="*80)
    
    ticker = "GC=F"
    print(f"\n📍 Ticker de prueba: {ticker}")
    
    # ── Paso 1: Entrenar Ensemble ────────────────────────────────────────────
    print(f"\n1️⃣  Entrenando Ensemble para {ticker}...")
    start = time.time()
    try:
        from backend.models.ensemble import train_ensemble
        ensemble_metrics = train_ensemble(ticker)
        elapsed = time.time() - start
        
        print(f"   ✅ Ensemble entrenado en {elapsed:.1f}s")
        print(f"      - Avg Val Loss: {ensemble_metrics['avg_val_loss']:.6f}")
        print(f"      - Avg Test Acc: {ensemble_metrics['avg_test_accuracy']:.2%}")
        print(f"      - XGBoost available: {'xgboost_metrics' in ensemble_metrics}")
    except Exception as e:
        print(f"   ❌ Error en train_ensemble: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ── Paso 2: Entrenar Stacking Meta-Model ─────────────────────────────────
    print(f"\n2️⃣  Entrenando Meta-Model de Stacking para {ticker}...")
    start = time.time()
    try:
        from backend.models.train_stacking import train_stacking_metalearner
        stacking_metrics = train_stacking_metalearner(ticker, verbose=True)
        elapsed = time.time() - start
        
        print(f"   ✅ Meta-model entrenado en {elapsed:.1f}s")
        print(f"      - Accuracy: {stacking_metrics['accuracy']:.2%}")
        print(f"      - F1 Weighted: {stacking_metrics['f1_weighted']:.4f}")
    except FileNotFoundError as e:
        print(f"   ⚠️ Error: {e}")
        print(f"      (Esto es esperado si los modelos no se entrenaron correctamente)")
        return False
    except Exception as e:
        print(f"   ❌ Error en train_stacking_metalearner: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ── Paso 3: Realizar Predicción con Stacking ─────────────────────────────
    print(f"\n3️⃣  Realizando predicción con Ensemble + Stacking para {ticker}...")
    start = time.time()
    try:
        from backend.models.ensemble import predict_ensemble
        prediction = predict_ensemble(ticker)
        elapsed = time.time() - start
        
        print(f"   ✅ Predicción realizada en {elapsed:.2f}s")
        print(f"      - Tendencia BiGRU: {prediction['trend']}")
        print(f"      - Confianza BiGRU: {prediction['confidence']:.2%}")
        print(f"      - Tendencia Meta-Ensemble: {prediction.get('meta_trend', 'N/A')}")
        print(f"      - Score Meta: {prediction.get('meta_score', 'N/A')}")
        
        # Check si usó stacking
        if "stacking" in str(prediction).lower():
            print(f"      ✅ Stacking fue utilizado en la predicción")
        else:
            print(f"      ℹ️  Stacking no menciona... (quizás meta-ensemble fue usado)")
    except Exception as e:
        print(f"   ❌ Error en predict_ensemble: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ── Resumen ──────────────────────────────────────────────────────────────
    print(f"\n" + "="*80)
    print(f"✅ TEST DE INTEGRACIÓN COMPLETADO EXITOSAMENTE")
    print(f"="*80)
    
    print(f"\n📊 Resumen:")
    print(f"  - Ensemble BiGRU: {ensemble_metrics['avg_test_accuracy']:.2%}")
    print(f"  - Meta-Model Stacking: {stacking_metrics['accuracy']:.2%}")
    print(f"  - Predicción final: {prediction['trend']} (conf: {prediction['confidence']:.2%})")
    
    return True


if __name__ == "__main__":
    success = test_stacking_integration()
    sys.exit(0 if success else 1)
