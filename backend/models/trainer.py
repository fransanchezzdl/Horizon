"""
Módulo de entrenamiento para el modelo Horizon Predictor.

Implementa el bucle de entrenamiento para CLASIFICACIÓN de 3 clases con:
- CrossEntropyLoss + class_weights para manejar desbalanceo
- Validación sobre el conjunto de validación
- Early stopping basado en validación
- Scheduler de learning rate adaptativo
- Guardado del mejor modelo

Los targets son ahora clases (0=BAJISTA, 1=LATERAL, 2=ALCISTA) no retornos continuos.
"""

import os
import copy
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset
from typing import Dict

from .model import (
    StableHorizonModel,
    VolatileHorizonModel,
    HorizonBiGRU,
    HorizonBiGRUAttention,
    FocalLoss,
)
from .config import SAVED_MODELS_DIR
from .rebalancer import AdaptiveClassRebalancer


def _get_model_class(model_type: str = None):
    """Devuelve la clase de modelo según configuración o tipo especificado."""
    if model_type == "stable":
        return StableHorizonModel
    elif model_type == "volatile":
        return VolatileHorizonModel
    elif model_type == "attention":
        return HorizonBiGRUAttention
    else:
        # Default: intentar de config
        try:
            from .config import USE_ATTENTION_MODEL
            return HorizonBiGRUAttention if USE_ATTENTION_MODEL else HorizonBiGRU
        except ImportError:
            return HorizonBiGRU


def calibrate_temperature(
    model: nn.Module,
    X_val: torch.Tensor,
    y_val: torch.Tensor,
    device: torch.device,
    max_iter: int = 100,
) -> float:
    """
    Calibra el parámetro de temperatura para mejorar confianza de predicciones.
    
    Temperature scaling ajusta las probabilidades softmax para que sean bien
    calibradas sin cambiar las predicciones (argmax sigue siendo el mismo).
    
    P_calibrated(i) = softmax(logits / T)
    
    Método: Optimiza T minimizando cross-entropy en validation set.
    
    Args:
        model: Modelo entrenado (asume .eval() + eval mode)
        X_val: Características de validación [batch, window, features]
        y_val: Labels de validación [batch] (clases 0/1/2)
        device: CPU o CUDA
        max_iter: Iteraciones de optimización LBFGS
    
    Returns:
        Valor óptimo de temperatura T (float, típicamente 0.8-1.5)
    """
    # Crear parámetro de temperatura
    temperature = nn.Parameter(torch.ones(1, device=device))
    
    # Optimizador LBFGS para calibración
    optimizer = torch.optim.LBFGS([temperature], lr=0.01, max_iter=max_iter)
    criterion = nn.CrossEntropyLoss(reduction="mean")
    
    model.eval()
    X_val = X_val.to(device)
    y_val = y_val.to(device)
    
    def closure():
        optimizer.zero_grad()
        with torch.no_grad():
            logits = model(X_val)  # [batch, 3]
        
        # Aplicar temperature scaling
        scaled_logits = logits / temperature
        loss = criterion(scaled_logits, y_val)
        loss.backward()
        return loss
    
    # Optimizar
    optimizer.step(closure)
    
    temp_value = float(temperature.item())
    print(f"[*] Temperature calibrada: T={temp_value:.4f}")
    
    return temp_value


def train_single_model(
    ticker: str,
    model_idx: int,
    config: dict,
    data: dict,
    device: torch.device,
) -> dict:
    """
    Entrena un único modelo para CLASIFICACIÓN de 3 clases.

    Utiliza CrossEntropyLoss con class_weights para manejar desbalanceo de clases.
    Optimizador Adam con scheduler ReduceLROnPlateau para ajustar learning rate.
    Implementa early stopping.

    Args:
        ticker: Símbolo del activo (ej: 'KO').
        model_idx: Índice del modelo dentro del ensemble (0-based).
        config: Diccionario de configuración del activo con:
            - model_class: "StableHorizonModel" o "VolatileHorizonModel"
            - hidden_dim, num_layers, dropout, etc.
        data: Diccionario con tensores:
            - X_train, y_train, X_val, y_val, X_test, y_test (aquí y son clases long)
            - class_weights: torch.Tensor [3] para balanceo
        device: Dispositivo de cómputo (CPU o CUDA).

    Returns:
        Diccionario con:
            - train_losses: lista de pérdidas por epoch (train)
            - val_losses: lista de pérdidas por epoch (validación)
            - best_val_loss: mejor pérdida de validación alcanzada
            - epochs_trained: número de epochs ejecutadas
            - model_path: ruta donde se guardó el modelo
            - train_accuracies: accuracies por epoch (train)
            - val_accuracies: accuracies por epoch (validación)
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
    input_dim = data["X_train"].shape[2]

    # Instanciar modelo correcto
    model_name = config.get("model_class", "HorizonBiGRUAttention")
    if model_name == "StableHorizonModel":
        model = StableHorizonModel(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            num_layers=num_layers,
            dropout=dropout,
            num_classes=3,
        )
    elif model_name == "VolatileHorizonModel":
        model = VolatileHorizonModel(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            num_layers=num_layers,
            dropout=dropout,
            num_classes=3,
        )
    else:
        model = HorizonBiGRUAttention(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            num_layers=num_layers,
            dropout=dropout,
            num_classes=3,
        )

    model = model.to(device)

    # Loss function: CrossEntropyLoss con class_weights (BUG FIX #1)
    class_weights = data.get("class_weights", torch.ones(3, device=device))
    if not isinstance(class_weights, torch.Tensor):
        class_weights = torch.tensor(class_weights, dtype=torch.float32, device=device)
    else:
        class_weights = class_weights.to(device)

    use_focal_loss = config.get("loss_function") == "FocalLoss"
    if use_focal_loss:
        criterion = FocalLoss(
            alpha=class_weights,
            gamma=config.get("focal_loss_gamma", 2.0),
            reduction="mean",
        )
    else:
        criterion = nn.CrossEntropyLoss(weight=class_weights, reduction="mean")

    # Optimizador y scheduler
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.7, patience=10
    )

    # ========== REBALANCEO DE CLASES CON SMOTE ==========
    # Detectar desbalanceo y aplicar estrategia adaptativa
    X_train_np = data["X_train"].cpu().numpy() if isinstance(data["X_train"], torch.Tensor) else data["X_train"]
    y_train_np = data["y_train"].cpu().numpy() if isinstance(data["y_train"], torch.Tensor) else data["y_train"]
    
    # Aplanar X para SMOTE (sequence, features) → (sequence*timesteps, features)
    n_samples, seq_len, n_features = X_train_np.shape
    X_train_flat = X_train_np.reshape(n_samples, -1)  # (n_samples, seq_len*n_features)
    
    imbalance_ratio, original_dist = AdaptiveClassRebalancer.calculate_imbalance_ratio(y_train_np)
    strategy = AdaptiveClassRebalancer.get_rebalance_strategy(imbalance_ratio, ticker)
    
    if strategy != "none":
        print(f"   📊 Desbalanceo detectado: {imbalance_ratio:.2f}x → Aplicando estrategia '{strategy}'")
        
        # Aplicar rebalanceo
        X_balanced_flat, y_balanced, class_weights_new = AdaptiveClassRebalancer.rebalance(
            X_train_flat, y_train_np, strategy=strategy, return_class_weights=True
        )
        
        # Reshape de vuelta a (n_samples, seq_len, n_features)
        X_balanced = X_balanced_flat.reshape(-1, seq_len, n_features)
        
        # Log de cambios
        _, new_dist = AdaptiveClassRebalancer.calculate_imbalance_ratio(y_balanced)
        class_names = {0: 'BAJISTA', 1: 'LATERAL', 2: 'ALCISTA'}
        for cls in range(3):
            orig = original_dist.get(cls, 0)
            new = new_dist.get(cls, 0)
            pct_orig = 100 * orig / sum(original_dist.values())
            pct_new = 100 * new / sum(new_dist.values())
            print(f"     {class_names[cls]:8s}: {orig:5d} ({pct_orig:5.1f}%) → {new:5d} ({pct_new:5.1f}%)")
        
        # Convertir a tensores
        data["X_train"] = torch.from_numpy(X_balanced).float().to(device)
        data["y_train"] = torch.from_numpy(y_balanced).long().to(device)
        data["class_weights"] = torch.tensor(
            [class_weights_new.get(i, 1.0) for i in range(3)],
            dtype=torch.float32,
            device=device
        )
    
    # DataLoaders — y_train son clases (long)
    train_dataset = TensorDataset(data["X_train"], data["y_train"])
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

    val_X = data["X_val"].to(device)
    val_y = data["y_val"].to(device)  # long tensor [batch]

    # Early stopping
    best_val_loss = float("inf")
    best_weights = None
    epochs_no_improve = 0

    train_losses = []
    val_losses = []
    train_accuracies = []
    val_accuracies = []

    print(
        f"\n🚀 Entrenando modelo {model_idx + 1} para {ticker} "
        f"({model_name}, seed={seed}, device={device})..."
    )

    for epoch in range(1, epochs + 1):
        # ── Fase de entrenamiento ──────────────────────────────────────
        model.train()
        epoch_train_loss = 0.0
        epoch_train_correct = 0
        epoch_train_total = 0

        for X_batch, y_batch in train_loader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)

            optimizer.zero_grad()
            logits = model(X_batch)  # [batch, 3]
            loss = criterion(logits, y_batch)
            loss.backward()
            optimizer.step()

            epoch_train_loss += loss.item()
            preds = torch.argmax(logits, dim=1)
            epoch_train_correct += (preds == y_batch).sum().item()
            epoch_train_total += y_batch.size(0)

        avg_train_loss = epoch_train_loss / len(train_loader)
        train_accuracy = epoch_train_correct / epoch_train_total if epoch_train_total > 0 else 0.0

        # ── Fase de validación ────────────────────────────────────────
        model.eval()
        with torch.no_grad():
            val_logits = model(val_X)  # [batch, 3]
            val_loss = criterion(val_logits, val_y).item()
            val_preds = torch.argmax(val_logits, dim=1)
            val_correct = (val_preds == val_y).sum().item()
            val_accuracy = val_correct / val_y.size(0) if val_y.size(0) > 0 else 0.0

        scheduler.step(val_loss)
        train_losses.append(avg_train_loss)
        val_losses.append(val_loss)
        train_accuracies.append(train_accuracy)
        val_accuracies.append(val_accuracy)

        # Imprimir progreso cada 10 epochs
        if epoch % 10 == 0 or epoch == 1:
            print(
                f"  Epoch {epoch:4d}/{epochs} | "
                f"Train Loss: {avg_train_loss:.6f} (Acc: {train_accuracy:.2%}) | "
                f"Val Loss: {val_loss:.6f} (Acc: {val_accuracy:.2%})"
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

    # Calibrar temperatura en validation set
    temperature = calibrate_temperature(model, val_X, val_y, device)

    # Guardar modelo
    os.makedirs(SAVED_MODELS_DIR, exist_ok=True)
    model_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_model_{model_idx}.pth")
    torch.save(model.state_dict(), model_path)
    
    # Guardar temperatura junto con el modelo
    temperature_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_temperature_{model_idx}.pt")
    torch.save(torch.tensor(temperature, dtype=torch.float32), temperature_path)
    
    best_epoch = np.argmin(val_losses)
    print(
        f"  💾 Modelo guardado en {model_path} "
        f"(best_epoch={best_epoch+1}, val_loss={best_val_loss:.6f}, "
        f"val_acc={val_accuracies[best_epoch]:.2%})"
    )

    return {
        "train_losses": train_losses,
        "val_losses": val_losses,
        "train_accuracies": train_accuracies,
        "val_accuracies": val_accuracies,
        "best_val_loss": best_val_loss,
        "best_val_accuracy": max(val_accuracies) if val_accuracies else 0.0,
        "epochs_trained": len(train_losses),
        "model_path": model_path,
        "temperature": temperature,
    }


def evaluate_model(
    model,
    X_test: torch.Tensor,
    y_test: torch.Tensor,
    device: torch.device,
) -> dict:
    """
    Evalúa el modelo en el conjunto de test usando métricas de clasificación.

    BUG FIX: Ya no usa threshold de regresión. Classifica directamente con argmax.

    Args:
        model: Modelo a evaluar
        X_test: [batch, window_size, features] características de test
        y_test: [batch] clases verdaderas (0, 1, 2)
        device: Dispositivo

    Returns:
        Diccionario con métricas:
        - accuracy: overall accuracy
        - precision_per_class: [3] precision por clase
        - recall_per_class: [3] recall por clase
        - f1_per_class: [3] F1 por clase
        - confusion_matrix: [3, 3]
        - per_class_metrics: dict más detallado de métricas
    """
    model.eval()
    model = model.to(device)
    X_test = X_test.to(device)
    y_test = y_test.to(device)

    with torch.no_grad():
        logits = model(X_test)  # [batch, 3]
        preds = torch.argmax(logits, dim=1)  # [batch]

    y_true = y_test.cpu().numpy()
    y_pred = preds.cpu().numpy()

    # Accuracy general
    accuracy = float(np.mean(y_pred == y_true))

    # Confusion matrix y métricas por clase
    confusion_matrix = np.zeros((3, 3), dtype=np.int32)
    precision_per_class = []
    recall_per_class = []
    f1_per_class = []

    class_names = ["BAJISTA", "LATERAL", "ALCISTA"]

    for class_idx in range(3):
        # TP, FP, FN, TN
        tp = np.sum((y_pred == class_idx) & (y_true == class_idx))
        fp = np.sum((y_pred == class_idx) & (y_true != class_idx))
        fn = np.sum((y_pred != class_idx) & (y_true == class_idx))

        precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        precision_per_class.append(precision)
        recall_per_class.append(recall)
        f1_per_class.append(f1)

        # Rellenar confusion matrix
        for c in range(3):
            confusion_matrix[class_idx, c] = np.sum((y_true == class_idx) & (y_pred == c))

    return {
        "accuracy": accuracy,
        "precision_per_class": precision_per_class,
        "recall_per_class": recall_per_class,
        "f1_per_class": f1_per_class,
        "f1_weighted": float(
            np.average(f1_per_class, weights=[(y_true == i).sum() for i in range(3)])
        ),
        "confusion_matrix": confusion_matrix,
        "per_class_metrics": {
            class_names[i]: {
                "precision": precision_per_class[i],
                "recall": recall_per_class[i],
                "f1": f1_per_class[i],
            }
            for i in range(3)
        },
        "n_samples_test": len(y_true),
    }
