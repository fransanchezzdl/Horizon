"""
Script para verificar el progreso del entrenamiento y comparar resultados.
"""

import os
import json
from pathlib import Path

SAVED_MODELS_DIR = "backend/models/saved_models"

def check_training_results():
    """Verifica los resultados de entrenamiento disponibles."""
    
    print("=" * 60)
    print("VERIFICACIÓN DE RESULTADOS DE ENTRENAMIENTO")
    print("=" * 60)
    
    # Buscar archivos de reporte
    reports = list(Path(SAVED_MODELS_DIR).glob("*_report.json"))
    
    if not reports:
        print("❌ No se encontraron reportes de entrenamiento")
        return
    
    print(f"\n📊 Encontrados {len(reports)} reportes:\n")
    
    for report_path in sorted(reports):
        ticker = report_path.stem.replace("_report", "")
        
        try:
            with open(report_path, "r") as f:
                report = json.load(f)
            
            print(f"{'=' * 60}")
            print(f"Ticker: {ticker}")
            print(f"{'=' * 60}")
            print(f"Fecha: {report.get('timestamp', 'N/A')}")
            print(f"Features: {report.get('num_features', 'N/A')}")
            print(f"Window size: {report.get('window_size', 'N/A')}")
            print(f"\nAccuracy BiGRU: {report.get('bigru_accuracy', 0) * 100:.2f}%")
            print(f"Accuracy XGBoost: {report.get('xgboost_accuracy', 0) * 100:.2f}%")
            print(f"Accuracy Meta-Ensemble: {report.get('meta_ensemble_accuracy', 0) * 100:.2f}%")
            
            # Mostrar métricas por clase
            if 'bigru_metrics' in report:
                metrics = report['bigru_metrics']
                print(f"\nMétricas BiGRU por clase:")
                print(f"  ALCISTA  - Precision: {metrics.get('precision_up', 0):.3f}, Recall: {metrics.get('recall_up', 0):.3f}")
                print(f"  LATERAL  - Precision: {metrics.get('precision_neutral', 0):.3f}, Recall: {metrics.get('recall_neutral', 0):.3f}")
                print(f"  BAJISTA  - Precision: {metrics.get('precision_down', 0):.3f}, Recall: {metrics.get('recall_down', 0):.3f}")
            
            print()
            
        except Exception as e:
            print(f"❌ Error leyendo {report_path}: {e}\n")

if __name__ == "__main__":
    check_training_results()
