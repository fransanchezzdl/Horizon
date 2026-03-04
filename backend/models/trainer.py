"""
Módulo de entrenamiento para el modelo Horizon Predictor.

Implementa el bucle de entrenamiento con validación, early stopping,
scheduler de learning rate y guardado del mejor modelo.
"""

import os
import copy
import math
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from typing import Dict

from .model import HorizonBiGRU
from .config import FEATURE_COLS, SAVED_MODELS_DIR


def train_single_model(
    ticker: str,
    model_idx: int,
    config: dict,
    data: dict,
    device: torch.device,
) -> dict:
    """
    Entrena un único modelo HorizonBiGRU y lo guarda en disco.

    Utiliza HuberLoss como función de pérdida (robusta a outliers),
    optimizador Adam y scheduler ReduceLROnPlateau. Implementa early
    stopping para detener el entrenamiento si la pérdida de validación
    no mejora durante 'patience' epochs, restaurando los mejores pesos.

    Args:
        ticker: Símbolo del activo (ej: 'KO').
        model_idx: Índice del modelo dentro del ensemble (0-based).
        config: Diccionario de configuración del activo.
        data: Diccionario con tensores (salida de prepare_data()).
        device: Dispositivo de cómputo (CPU o CUDA).

    Returns:
        Diccionario con:
            - train_losses: lista de pérdidas por epoch (train)
            - val_losses: lista de pérdidas por epoch (validación)
            - best_val_loss: mejor pérdida de validación alcanzada
            - epochs_trained: número de epochs ejecutadas
            - model_path: ruta donde se guardó el modelo
    """
    # Semilla diferente para cada modelo del ensemble
    seed = 42 + model_idx
    torch.manual_seed(seed)
    np.random.seed(seed)

    hidden_dim = config["hidden_dim"]
    num_layers = config["num_layers"]
    dropout = config["dropout"]
    lr = config["learning_rate"]
    epochs = config["epochs"]
    batch_size = config["batch_size"]
    patience = config["early_stopping_patience"]

    # Instanciar modelo
    model = HorizonBiGRU(
        input_dim=len(FEATURE_COLS),
        hidden_dim=hidden_dim,
        num_layers=num_layers,
        dropout=dropout,
    ).to(device)

    # Loss, optimizador y scheduler
    criterion = nn.HuberLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=5
    )

    # DataLoaders
    train_dataset = TensorDataset(data["X_train"], data["y_train"])
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

    val_X = data["X_val"].to(device)
    val_y = data["y_val"].to(device)

    # Early stopping
    best_val_loss = float("inf")
    best_weights = None
    epochs_no_improve = 0

    train_losses = []
    val_losses = []

    print(
        f"\n🚀 Entrenando modelo {model_idx + 1} para {ticker} "
        f"(seed={seed}, device={device})..."
    )

    for epoch in range(1, epochs + 1):
        # ── Fase de entrenamiento ──────────────────────────────────────
        model.train()
        epoch_train_loss = 0.0
        for X_batch, y_batch in train_loader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)

            optimizer.zero_grad()
            predictions = model(X_batch)
            loss = criterion(predictions, y_batch)
            loss.backward()
            optimizer.step()
            epoch_train_loss += loss.item()

        avg_train_loss = epoch_train_loss / len(train_loader)

        # ── Fase de validación ────────────────────────────────────────
        model.eval()
        with torch.no_grad():
            val_preds = model(val_X)
            val_loss = criterion(val_preds, val_y).item()

        scheduler.step(val_loss)
        train_losses.append(avg_train_loss)
        val_losses.append(val_loss)

        # Imprimir progreso cada 10 epochs
        if epoch % 10 == 0 or epoch == 1:
            print(
                f"  Epoch {epoch:4d}/{epochs} | "
                f"Train Loss: {avg_train_loss:.6f} | "
                f"Val Loss: {val_loss:.6f}"
            )

        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_weights = copy.deepcopy(model.state_dict())
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                print(
                    f"  ⏹️  Early stopping en epoch {epoch} "
                    f"(sin mejora en {patience} epochs)."
                )
                break

    # Restaurar mejores pesos
    if best_weights is not None:
        model.load_state_dict(best_weights)

    # Guardar modelo
    os.makedirs(SAVED_MODELS_DIR, exist_ok=True)
    model_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_model_{model_idx}.pth")
    torch.save(model.state_dict(), model_path)
    print(f"  💾 Modelo guardado en {model_path} (val_loss={best_val_loss:.6f})")

    return {
        "train_losses": train_losses,
        "val_losses": val_losses,
        "best_val_loss": best_val_loss,
        "epochs_trained": len(train_losses),
        "model_path": model_path,
    }


def evaluate_model(
    model: HorizonBiGRU,
    X_test: torch.Tensor,
    y_test: torch.Tensor,
    device: torch.device,
) -> dict:
    """
    Evalúa un modelo entrenado en el conjunto de test.

    Calcula MAE, RMSE y accuracy direccional (porcentaje de veces que
    el modelo predice correctamente si el retorno será positivo o negativo).

    Args:
        model: Modelo HorizonBiGRU entrenado.
        X_test: Tensor de features del test [n, window_size, n_features].
        y_test: Tensor de targets reales del test [n, 1].
        device: Dispositivo de cómputo.

    Returns:
        Diccionario con métricas: mae, rmse, directional_accuracy.
    """
    model.eval()
    model.to(device)
    X_test = X_test.to(device)
    y_test = y_test.to(device)

    with torch.no_grad():
        preds = model(X_test).cpu().numpy()

    y_true = y_test.cpu().numpy()

    mae = float(np.mean(np.abs(preds - y_true)))
    rmse = float(math.sqrt(np.mean((preds - y_true) ** 2)))

    # Accuracy direccional: ¿el signo del retorno predicho coincide con el real?
    directional_accuracy = float(
        np.mean(np.sign(preds.flatten()) == np.sign(y_true.flatten()))
    )

    return {
        "mae": mae,
        "rmse": rmse,
        "directional_accuracy": directional_accuracy,
    }
