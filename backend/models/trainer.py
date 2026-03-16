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

from .model import HorizonBiGRU, HorizonBiGRUAttention
from .config import SAVED_MODELS_DIR

def _get_model_class():
    """Devuelve la clase de modelo según configuración."""
    try:
        from .config import USE_ATTENTION_MODEL
        return HorizonBiGRUAttention if USE_ATTENTION_MODEL else HorizonBiGRU
    except ImportError:
        return HorizonBiGRU


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

    # Instanciar modelo (Attention o BiGRU según config)
    ModelClass = _get_model_class()
    model = ModelClass(
        input_dim=data["X_train"].shape[2],
        hidden_dim=hidden_dim,
        num_layers=num_layers,
        dropout=dropout,
    ).to(device)

    # Loss, optimizador y scheduler
    # HuberLoss para regresión (robusto a outliers)
    criterion = nn.HuberLoss(delta=0.01)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.7, patience=10
    )

    # DataLoaders — y_train son retornos continuos (float)
    train_dataset = TensorDataset(data["X_train"], data["y_train"])
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

    val_X = data["X_val"].to(device)
    val_y = data["y_val"].to(device)  # float tensor

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
    model,
    X_test: torch.Tensor,
    y_test: torch.Tensor,
    device: torch.device,
    threshold: float = 0.01,
) -> dict:
    """
    Evalúa el modelo de regresión en el conjunto de test.

    Convierte retornos predichos a dirección usando el threshold dinámico.
    y_test son retornos continuos (float).
    """
    model.eval()
    model.to(device)
    X_test = X_test.to(device)

    with torch.no_grad():
        preds = model(X_test).squeeze(1).cpu().numpy()  # [n]

    y_true = y_test.squeeze(1).cpu().numpy()  # [n]

    # Convertir retornos a dirección binaria con threshold
    pred_dir = (preds > threshold).astype(int)
    true_dir = (y_true > threshold).astype(int)

    accuracy = float(np.mean(pred_dir == true_dir))

    mae  = float(np.mean(np.abs(preds - y_true)))
    rmse = float(np.sqrt(np.mean((preds - y_true) ** 2)))

    tp = np.sum((pred_dir == 1) & (true_dir == 1))
    fp = np.sum((pred_dir == 1) & (true_dir == 0))
    fn = np.sum((pred_dir == 0) & (true_dir == 1))
    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall    = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0

    naive_accuracy = float(np.mean(true_dir == int(true_dir.mean() > 0.5)))

    return {
        "directional_accuracy": accuracy,
        "precision_up": precision,
        "recall_up": recall,
        "mae": mae,
        "rmse": rmse,
        "naive_baseline_accuracy": naive_accuracy,
        "n_samples_test": len(y_true),
    }
