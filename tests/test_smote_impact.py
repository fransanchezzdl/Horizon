"""
Test de impacto de SMOTE en GC=F (oro - commodity que más sufre desbalanceo)
"""

import sys
sys.path.insert(0, '/d/Uni/TFG/Horizon')

from backend.models.ensemble import train_ensemble
import torch

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("="*80)
print("TEST: Entrenamiento GC=F CON SMOTE")
print("="*80)
print(f"\nPrevio: GC=F tenía 33.47% test accuracy")
print(f"Objetivo: Subir a >40% con SMOTE rebalanceado\n")

try:
    results = train_ensemble(ticker="GC=F")
    
    print("\n" + "="*80)
    print("RESULTADOS CON SMOTE:")
    print("="*80)
    print(f"Test Accuracy: {results.get('avg_test_accuracy', 0):.2%}")
    print(f"F1 Weighted:   {results.get('avg_f1_weighted', 0):.4f}")
    print(f"Val Loss:      {results.get('avg_val_loss', 0):.4f}")
    print(f"XGB Directional: {results.get('xgboost_metrics', {}).get('xgb_directional_accuracy', 0):.2%}")
    
    # Comparación
    prev_acc = 0.3347
    new_acc = results.get('avg_test_accuracy', 0)
    improvement = new_acc - prev_acc
    improvement_pct = (improvement / prev_acc) * 100 if prev_acc > 0 else 0
    
    print(f"\n{'COMPARACIÓN':-^80}")
    print(f"Anterior: {prev_acc:.2%}")
    print(f"Nuevo:    {new_acc:.2%}")
    print(f"Mejora:   +{improvement:.4f} ({improvement_pct:+.1f}%)")
    
    if new_acc > prev_acc:
        print(f"\n✅ SMOTE MEJORÓ GC=F en {improvement_pct:.1f}%")
    else:
        print(f"\n⚠️ SMOTE no mejoró (o empeoró) GC=F")
        
except Exception as e:
    print(f"❌ Error durante entrenamiento: {e}")
    import traceback
    traceback.print_exc()
