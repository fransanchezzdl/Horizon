#!/usr/bin/env python
"""Script de prueba para Walk-Forward Validation + Temperature Scaling."""

import sys
import time
import numpy as np
import torch
from backend.models.data_pipeline import prepare_data_walk_forward
from backend.models.trainer import train_single_model, evaluate_model, calibrate_temperature
from backend.models.config import get_asset_type
from backend.models.model import HorizonBiGRUAttention

print("[*] Probando Walk-Forward Validation + Temperature Scaling...")
print()

# Parámetros
ticker = "KO"
asset_type = get_asset_type(ticker)
device = torch.device("cpu")

# Configuración básica
config = {
    "hidden_dim": 128 if asset_type == "stable" else 96,
    "num_layers": 2 if asset_type == "stable" else 3,
    "dropout": 0.1 if asset_type == "stable" else 0.3,
    "learning_rate": 0.001,
    "epochs": 50,  # Reducido para prueba rápida
    "batch_size": 32,
    "early_stopping_patience": 10,
    "model_class": "StableHorizonModel" if asset_type == "stable" else "VolatileHorizonModel",
}

# 1. Preparar datos walk-forward
start = time.time()
folds = prepare_data_walk_forward(
    ticker,
    config,
    window_size=30,
    n_folds=3,  # Solo 3 folds para prueba rápida
    gap_days=5,
)
prep_time = time.time() - start
print(f"✅ Preparación completada en {prep_time:.1f}s\n")

# 2. Entrenar en cada fold
fold_accuracies = []
fold_temperatures = []

for i, fold_data in enumerate(folds):
    print(f"\n{'='*60}")
    print(f"🔄 FOLD {i+1}/{len(folds)}")
    print(f"{'='*60}")
    
    # Preparar datos para este fold
    class_weights = fold_data.get("class_weights", torch.ones(3))
    
    train_data = {
        "X_train": fold_data["X_train"],
        "y_train": fold_data["y_train"],
        "X_val": fold_data["X_val"],
        "y_val": fold_data["y_val"],
        "X_test": fold_data["X_test"],
        "y_test": fold_data["y_test"],
        "class_weights": class_weights,
    }
    
    # Entrenar modelo
    start = time.time()
    metrics = train_single_model(
        ticker,
        i,
        config,
        train_data,
        device,
    )
    train_time = time.time() - start
    
    # Obtener temperatura calibrada
    temperature = metrics.get("temperature", 1.0)
    fold_temperatures.append(temperature)
    
    # Evaluar en test
    test_accuracy = metrics.get("best_val_accuracy", 0.0)
    fold_accuracies.append(test_accuracy)
    
    print(f"⏱️  Entrenamiento: {train_time:.1f}s")
    print(f"📊 Val Accuracy: {test_accuracy:.2%}")
    print(f"🌡️  Temperature: {temperature:.4f}")
    print(f"📉 Final Val Loss: {metrics['best_val_loss']:.6f}")

# 3. Resumen final
print(f"\n{'='*60}")
print("📈 RESUMEN WALK-FORWARD")
print(f"{'='*60}")
print(f"Folds completados: {len(folds)}")
print(f"Accuracy promedio: {np.mean(fold_accuracies):.2%}")
print(f"Accuracy std: {np.std(fold_accuracies):.2%}")
print(f"Temperature promedio: {np.mean(fold_temperatures):.4f}")
print(f"Temperature rango: [{np.min(fold_temperatures):.4f}, {np.max(fold_temperatures):.4f}]")
print()
print("✅ Walk-Forward Validation + Temperature Scaling: OPERATIVO")
print()
