"""
Script para comparar resultados de diferentes configuraciones de features.
"""

import json
import os
from datetime import datetime

SAVED_MODELS_DIR = "backend/models/saved_models"

def load_report(ticker: str):
    """Carga el reporte de un ticker."""
    report_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_report.json")
    if not os.path.exists(report_path):
        return None
    
    with open(report_path, "r") as f:
        return json.load(f)

def compare_models(ticker: str):
    """Compara el modelo actual con versiones anteriores."""
    
    report = load_report(ticker)
    if not report:
        print(f"❌ No se encontró reporte para {ticker}")
        return
    
    print("=" * 70)
    print(f"COMPARACIÓN DE MODELOS PARA {ticker}")
    print("=" * 70)
    
    # Información general
    num_features = len(report.get("feature_cols", []))
    trained_at = report.get("trained_at", "N/A")
    
    print(f"\n📅 Entrenado: {trained_at}")
    print(f"📊 Features: {num_features}")
    print(f"🎯 Tipo: {report.get('asset_type', 'N/A')}")
    
    # Métricas BiGRU
    metrics = report.get("metrics", {})
    bigru_acc = metrics.get("avg_directional_accuracy", 0) * 100
    
    print(f"\n{'=' * 70}")
    print("MÉTRICAS BIGRU ENSEMBLE")
    print(f"{'=' * 70}")
    print(f"Accuracy:           {bigru_acc:.2f}%")
    print(f"Precision (Alcista): {metrics.get('avg_precision_up', 0) * 100:.2f}%")
    print(f"Recall (Alcista):    {metrics.get('avg_recall_up', 0) * 100:.2f}%")
    print(f"MAE:                {metrics.get('avg_mae', 0):.6f}")
    print(f"RMSE:               {metrics.get('avg_rmse', 0):.6f}")
    
    # Métricas XGBoost
    xgb_metrics = report.get("xgboost_metrics", {})
    xgb_acc = xgb_metrics.get("xgb_directional_accuracy", 0) * 100
    
    print(f"\n{'=' * 70}")
    print("MÉTRICAS XGBOOST")
    print(f"{'=' * 70}")
    print(f"Accuracy:           {xgb_acc:.2f}%")
    print(f"Precision (Alcista): {xgb_metrics.get('xgb_precision_up', 0) * 100:.2f}%")
    print(f"Recall (Alcista):    {xgb_metrics.get('xgb_recall_up', 0) * 100:.2f}%")
    
    # Feature importance
    feature_importance = xgb_metrics.get("feature_importance", {})
    if feature_importance:
        print(f"\n{'=' * 70}")
        print("TOP 10 FEATURES MÁS IMPORTANTES (XGBoost)")
        print(f"{'=' * 70}")
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
        for i, (feat, importance) in enumerate(sorted_features[:10], 1):
            print(f"{i:2d}. {feat:<20} {importance:.4f}")
    
    # Análisis de early stopping
    individual_models = report.get("individual_models", [])
    if individual_models:
        epochs = [m.get("epochs_trained", 0) for m in individual_models]
        avg_epochs = sum(epochs) / len(epochs)
        
        print(f"\n{'=' * 70}")
        print("ANÁLISIS DE EARLY STOPPING")
        print(f"{'=' * 70}")
        print(f"Epochs promedio: {avg_epochs:.1f}")
        print(f"Epochs por modelo: {epochs}")
        
        if avg_epochs < 35:
            print(f"\n⚠️  El modelo converge rápido (promedio {avg_epochs:.1f} epochs)")
            print("   Esto puede indicar:")
            print("   • El modelo alcanzó su capacidad máxima (OK si accuracy > 55%)")
            print("   • Learning rate muy alto (el modelo oscila)")
            print("   • Necesita más datos o features diferentes")
        else:
            print(f"\n✅ El modelo entrena normalmente ({avg_epochs:.1f} epochs)")
    
    # Comparación con baseline
    baseline = metrics.get("naive_baseline_accuracy", 0) * 100
    improvement = bigru_acc - baseline
    
    print(f"\n{'=' * 70}")
    print("COMPARACIÓN CON BASELINE")
    print(f"{'=' * 70}")
    print(f"Baseline (naive):   {baseline:.2f}%")
    print(f"BiGRU Ensemble:     {bigru_acc:.2f}%")
    print(f"Mejora:             +{improvement:.2f}%")
    
    # Evaluación final
    print(f"\n{'=' * 70}")
    print("EVALUACIÓN FINAL")
    print(f"{'=' * 70}")
    
    if bigru_acc >= 58:
        print(f"🎉 EXCELENTE: Accuracy {bigru_acc:.2f}% supera el objetivo (58%)")
    elif bigru_acc >= 55:
        print(f"✅ BUENO: Accuracy {bigru_acc:.2f}% está cerca del objetivo")
    elif bigru_acc >= 50:
        print(f"⚠️  REGULAR: Accuracy {bigru_acc:.2f}% necesita mejoras")
    else:
        print(f"❌ BAJO: Accuracy {bigru_acc:.2f}% requiere revisión")
        print("\nSugerencias:")
        print("• Revisar normalización de features")
        print("• Eliminar features con baja correlación")
        print("• Ajustar hiperparámetros (learning rate, dropout)")
        print("• Aumentar early_stopping_patience")

if __name__ == "__main__":
    compare_models("KO")
