#!/usr/bin/env python
"""Script rápido para probar entrenamiento con un ticker."""

import sys
import time
from backend.models.ensemble import train_ensemble

print("[*] Iniciando entrenamiento con KO...")
start = time.time()

try:
    metrics = train_ensemble("KO")
    elapsed = time.time() - start
    
    print("")
    print("[OK] ENTRENAMIENTO COMPLETADO")
    print(f"[*] Tiempo total: {elapsed:.1f}s ({elapsed/60:.1f}m)")
    print("[*] Metricas principales:")
    if "avg_val_loss" in metrics:
        print(f"    avg_val_loss: {metrics['avg_val_loss']:.4f}")
    if "avg_directional_accuracy" in metrics:
        print(f"    avg_directional_accuracy: {metrics['avg_directional_accuracy']:.4f}")
    if "xgb_directional_accuracy" in metrics:
        print(f"    xgb_directional_accuracy: {metrics['xgb_directional_accuracy']:.4f}")
        
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
