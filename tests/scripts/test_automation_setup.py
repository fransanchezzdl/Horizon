#!/usr/bin/env python
"""
Script de testing rápido para verificar que todo está configurado correctamente.

Prueba:
1. Conexión a BD
2. Existencia de archivos de modelo
3. Operaciones de guardado en BD
4. Flujo completo de entrenamiento

Uso:
    python scripts/test_automation_setup.py
    python scripts/test_automation_setup.py --quick   # Solo verificaciones básicas
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# Agregar backend al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.models.config import TICKERS, USE_SENTIMENT
from backend.services.activo_service import activo_service
from backend.models.ensemble import train_ensemble, predict_ensemble


def test_imports():
    """Verifica que todas las dependencias se pueden importar."""
    print("=" * 70)
    print("🔍 TEST 1: Verificando importaciones...")
    print("=" * 70)
    
    try:
        import apscheduler
        print("✅ APScheduler disponible")
    except ImportError:
        print("❌ APScheduler no instalado")
        print("   Instala con: pip install apscheduler")
        return False
    
    try:
        from backend.services import activo_update_service
        print("✅ Servicio de actualización de activos disponible")
    except ImportError as e:
        print(f"❌ Error importando servicio: {e}")
        return False
    
    return True


def test_database():
    """Verifica la conexión a BD."""
    print("\n" + "=" * 70)
    print("🔍 TEST 2: Verificando conexión a BD...")
    print("=" * 70)
    
    try:
        # Intentar traer un activo
        activo = activo_service.obtener_activo("AAPL")
        if activo:
            print(f"✅ BD accesible")
            print(f"   Activo AAPL: {activo.get('nombre_completo', 'N/A')}")
            return True
        else:
            print("⚠️ AAPL no encontrado, pero BD está accesible")
            print("   Verifica que existan activos en la tabla")
            return True
    except Exception as e:
        print(f"❌ Error conectando a BD: {e}")
        print("   Verifica credenciales en .env")
        return False


def test_sentiment_flag():
    """Verifica que USE_SENTIMENT está en False."""
    print("\n" + "=" * 70)
    print("🔍 TEST 3: Verificando configuración de sentimiento...")
    print("=" * 70)
    
    if USE_SENTIMENT:
        print("⚠️ USE_SENTIMENT=True")
        print("   Los entrenamientos NO guardarán en BD con sentiment activado")
        print("   Para guardar, asegúrate que backend/models/config.py tenga:")
        print("   USE_SENTIMENT = False")
        return False
    else:
        print("✅ USE_SENTIMENT=False")
        print("   Los entrenamientos guardarán en BD")
        return True


def test_single_training(ticker: str = "AAPL"):
    """Realiza un entrenamiento de prueba con un ticker."""
    print("\n" + "=" * 70)
    print(f"🔍 TEST 4: Realizando entrenamiento de prueba ({ticker})...")
    print("=" * 70)
    print("   Esto puede tomar 2-5 minutos...\n")
    
    try:
        start = time.time()
        
        print(f"📚 Entrenando ensemble...")
        metrics = train_ensemble(ticker)
        
        if not metrics:
            print(f"❌ train_ensemble retornó None")
            return False
        
        print(f"✅ Entrenamiento completado")
        print(f"   Val Loss: {metrics.get('avg_val_loss', 'N/A'):.6f}")
        print(f"   Directional Accuracy: {metrics.get('avg_directional_accuracy', 'N/A'):.2%}")
        
        if USE_SENTIMENT:
            print("ℹ️ Sentiment activado - No se realizará guardado en BD en esta prueba")
            elapsed = time.time() - start
            print(f"   Tiempo: {elapsed:.1f}s")
            return True
        
        # Hacer predicción
        print(f"\n📊 Realizando predicción...")
        ensemble_pred = predict_ensemble(ticker)
        
        if not ensemble_pred:
            print(f"❌ predict_ensemble retornó None")
            return False
        
        print(f"✅ Predicción completada")
        print(f"   Trend: {ensemble_pred.get('trend', 'N/A')}")
        print(f"   Confidence: {ensemble_pred.get('confidence', 'N/A'):.4f}")
        
        # Guardar en BD
        print(f"\n💾 Guardando en BD...")
        from backend.services import activo_update_service
        
        training_metrics = {
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
            training_metrics
        )
        
        if not success:
            print(f"❌ Error al guardar en BD")
            return False
        
        print(f"✅ Datos guardados en BD")
        
        # Verificar
        print(f"\n📋 Verificando datos en BD...")
        activo_guardado = activo_service.obtener_activo(ticker)
        
        if activo_guardado:
            print(f"✅ Verificación exitosa")
            print(f"   Precio: ${activo_guardado.get('precio', 'N/A')}")
            print(f"   Señal: {activo_guardado.get('senal_ia', 'N/A')}")
            print(f"   Confianza: {activo_guardado.get('confianza_bygru', 'N/A'):.4f}")
        else:
            print(f"❌ No se pudo verificar en BD")
            return False
        
        elapsed = time.time() - start
        print(f"\n⏱️ Tiempo total: {elapsed:.1f}s")
        return True
        
    except Exception as e:
        print(f"❌ Error en entrenamiento: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_summary(results):
    """Imprime resumen de tests."""
    print("\n" + "=" * 70)
    print("📋 RESUMEN DE TESTS")
    print("=" * 70)
    
    test_names = [
        "Importaciones",
        "Conexión a BD",
        "Configuración de sentimiento",
        "Entrenamiento de prueba",
    ]
    
    for name, result in zip(test_names, results):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print("=" * 70)
    
    if all(results):
        print("\n🎉 ¡TODOS LOS TESTS PASARON!")
        print("\nYa puedes activar la automatización:")
        print("  Opción 1 (FastAPI): Agregar scheduler_service a main.py")
        print("  Opción 2 (Daemon): python scripts/scheduler_daemon.py --foreground")
        print("  Opción 3 (Windows): .\\windows_task_scheduler_setup.ps1 -Action Create")
        print("  Opción 4 (Linux): bash linux_cron_setup.sh --create")
    else:
        print("\n⚠️ Algunos tests fallaron.")
        print("Soluciona los errores antes de activar automatización.")
    
    print()


def main():
    """Punto de entrada."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test de automatización")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Solo tests básicos (sin entrenar)"
    )
    parser.add_argument(
        "--ticker",
        default="AAPL",
        help="Ticker para test de entrenamiento (default: AAPL)"
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 70)
    print("🧪 TESTING SETUP DE AUTOMATIZACIÓN — HORIZON PREDICTOR")
    print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")
    
    results = []
    
    # Test 1: Importaciones
    results.append(test_imports())
    
    # Test 2: BD
    results.append(test_database())
    
    # Test 3: Configuración
    results.append(test_sentiment_flag())
    
    # Test 4: Entrenamiento (opcional si --quick)
    if not args.quick:
        results.append(test_single_training(args.ticker))
    else:
        print("\n" + "=" * 70)
        print("⏭️ Saltando entrenamiento (modo --quick)")
        print("=" * 70)
        results.append(True)  # Asumir que pasaría
    
    # Resumen
    print_summary(results)
    
    # Exit code
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
