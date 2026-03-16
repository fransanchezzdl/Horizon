"""
Script para monitorear el progreso del entrenamiento en tiempo real.
Lee el archivo de log y muestra estadísticas.
"""

import os
import re
from pathlib import Path

LOG_FILE = "entrenamiento.log"

def parse_log():
    """Parse el archivo de log y extrae información relevante."""
    
    if not os.path.exists(LOG_FILE):
        print(f"❌ No se encontró {LOG_FILE}")
        return
    
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        # Intentar con latin-1 si utf-8 falla
        with open(LOG_FILE, "r", encoding="latin-1") as f:
            content = f.read()
    
    # Buscar información de early stopping
    early_stopping_pattern = r"Early stopping en epoch (\d+)"
    early_stops = re.findall(early_stopping_pattern, content)
    
    # Buscar validation losses guardados
    val_loss_pattern = r"val_loss=([\d.]+)"
    val_losses = re.findall(val_loss_pattern, content)
    
    # Buscar accuracy final
    accuracy_pattern = r"Accuracy.*?:\s*([\d.]+)%"
    accuracies = re.findall(accuracy_pattern, content)
    
    print("=" * 60)
    print("MONITOREO DE ENTRENAMIENTO")
    print("=" * 60)
    
    if early_stops:
        print(f"\n📊 Early stopping detectado en epochs:")
        for i, epoch in enumerate(early_stops, 1):
            loss = val_losses[i-1] if i <= len(val_losses) else "N/A"
            print(f"  Modelo {i}: epoch {epoch} (val_loss={loss})")
        
        avg_epoch = sum(int(e) for e in early_stops) / len(early_stops)
        print(f"\n📈 Promedio de epochs: {avg_epoch:.1f}")
        
        if avg_epoch < 30:
            print("\n⚠️  ANÁLISIS:")
            print("  El early stopping ocurre muy temprano (<30 epochs).")
            print("  Posibles causas:")
            print("  1. El modelo converge rápido (bueno si accuracy es alto)")
            print("  2. Learning rate muy alto (el modelo oscila)")
            print("  3. Features no aportan información útil")
            print("\n  Solución: Espera a ver el accuracy final.")
            print("  Si accuracy < 55%, considera ajustar hiperparámetros.")
        else:
            print("\n✅ El modelo está entrenando normalmente.")
    
    if accuracies:
        print(f"\n🎯 Accuracies encontrados:")
        for i, acc in enumerate(accuracies, 1):
            print(f"  {i}. {acc}%")
    
    # Contar modelos completados
    models_completed = content.count("Modelo guardado")
    print(f"\n✅ Modelos completados: {models_completed}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    parse_log()
