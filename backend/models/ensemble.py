"""
Gestión del ensemble de modelos BiGRU para el predictor Horizon.

Entrena N modelos con diferentes semillas de inicialización y
combina sus predicciones mediante voto mayoritario para la tendencia
y estadísticas sobre los retornos predichos para el precio orientativo.
"""

import os
import torch
import numpy as np
from typing import List

from .config import (
    ENSEMBLE_SIZE,
    FEATURE_COLS,
    SAVED_MODELS_DIR,
    get_config,
)
from .data_pipeline import prepare_data, load_scaler, download_data, compute_features
from .model import HorizonBiGRU
from .trainer import train_single_model, evaluate_model


def train_ensemble(ticker: str) -> dict:
    """
    Entrena el ensemble completo de N modelos para un ticker dado.

    Cada modelo se entrena con una semilla diferente para introducir
    diversidad. El scaler y los modelos se guardan en saved_models/.

    Args:
        ticker: Símbolo del activo (ej: 'KO', 'TSLA').

    Returns:
        Diccionario con métricas agregadas del ensemble:
            - ticker: símbolo del activo
            - n_models: número de modelos entrenados
            - individual_metrics: lista de métricas por modelo
            - avg_val_loss: pérdida de validación media
            - avg_directional_accuracy: accuracy direccional media en test
    """
    config = get_config(ticker)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print(f"\n{'='*60}")
    print(f"🎯 Entrenando ensemble para {ticker} ({ENSEMBLE_SIZE} modelos)")
    print(f"   Dispositivo: {device}")
    print(f"{'='*60}")

    # Preparar datos una sola vez (compartido por todos los modelos)
    data = prepare_data(ticker, config)

    individual_metrics = []

    for model_idx in range(ENSEMBLE_SIZE):
        metrics = train_single_model(ticker, model_idx, config, data, device)
        # Evaluar en test
        model = _load_single_model(ticker, model_idx, config, device)
        test_metrics = evaluate_model(
            model, data["X_test"], data["y_test"], device
        )
        metrics.update(test_metrics)
        individual_metrics.append(metrics)

    avg_val_loss = float(
        np.mean([m["best_val_loss"] for m in individual_metrics])
    )
    avg_dir_acc = float(
        np.mean([m["directional_accuracy"] for m in individual_metrics])
    )

    print(f"\n✅ Ensemble {ticker} completado:")
    print(f"   Val Loss medio: {avg_val_loss:.6f}")
    print(f"   Accuracy direccional media (test): {avg_dir_acc:.2%}")

    return {
        "ticker": ticker,
        "n_models": ENSEMBLE_SIZE,
        "individual_metrics": individual_metrics,
        "avg_val_loss": avg_val_loss,
        "avg_directional_accuracy": avg_dir_acc,
    }


def _load_single_model(
    ticker: str, model_idx: int, config: dict, device: torch.device
) -> HorizonBiGRU:
    """
    Carga un único modelo guardado desde disco.

    Args:
        ticker: Símbolo del activo.
        model_idx: Índice del modelo dentro del ensemble.
        config: Diccionario de configuración.
        device: Dispositivo de cómputo.

    Returns:
        HorizonBiGRU cargado y en modo evaluación.

    Raises:
        FileNotFoundError: Si el archivo .pth no existe.
    """
    model_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_model_{model_idx}.pth")
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Modelo no encontrado: {model_path}. "
            f"Ejecuta train_ensemble('{ticker}') primero."
        )

    model = HorizonBiGRU(
        input_dim=len(FEATURE_COLS),
        hidden_dim=config["hidden_dim"],
        num_layers=config["num_layers"],
        dropout=config["dropout"],
    )
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.to(device)
    model.eval()
    return model


def load_ensemble(ticker: str) -> List[HorizonBiGRU]:
    """
    Carga los N modelos entrenados del ensemble para un ticker.

    Args:
        ticker: Símbolo del activo.

    Returns:
        Lista de modelos HorizonBiGRU cargados y listos para inferencia.

    Raises:
        FileNotFoundError: Si alguno de los modelos no existe en disco.
    """
    config = get_config(ticker)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    models = []
    for model_idx in range(ENSEMBLE_SIZE):
        model = _load_single_model(ticker, model_idx, config, device)
        models.append(model)

    print(f"📦 Ensemble de {ticker} cargado ({len(models)} modelos).")
    return models


def predict_ensemble(ticker: str) -> dict:
    """
    Ejecuta la predicción del ensemble para un ticker dado.

    Carga los N modelos y el scaler entrenados, descarga los últimos
    datos del ticker, calcula features y realiza la predicción. Combina
    los retornos predichos para obtener tendencia consenso, confianza,
    precio predicho y bandas de incertidumbre.

    Lógica de tendencia por modelo:
        - retorno > threshold  → ALCISTA
        - retorno < -threshold → BAJISTA
        - en otro caso         → LATERAL

    Tendencia final = voto mayoritario de los N modelos.
    Confianza = proporción de modelos que votan por la tendencia ganadora.

    Args:
        ticker: Símbolo del activo.

    Returns:
        Diccionario con:
            - trend: 'ALCISTA', 'BAJISTA' o 'LATERAL'
            - confidence: proporción 0.0–1.0
            - predicted_price: precio_actual * exp(media retornos)
            - price_upper: banda superior (media + std)
            - price_lower: banda inferior (media - std)
            - predicted_return: retorno logarítmico medio predicho
            - individual_predictions: lista con retorno de cada modelo

    Raises:
        FileNotFoundError: Si los modelos o el scaler no están entrenados.
        ValueError: Si no hay datos disponibles para el ticker.
    """
    config = get_config(ticker)
    threshold = config["trend_threshold"]
    window_size = config["window_size"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Cargar ensemble y scaler
    models = load_ensemble(ticker)
    scaler = load_scaler(ticker)

    # Descargar datos recientes y calcular features
    raw_df = download_data(ticker)
    feat_df = compute_features(raw_df)

    if len(feat_df) < window_size:
        raise ValueError(
            f"Datos insuficientes para {ticker}: "
            f"se necesitan al menos {window_size} filas, "
            f"disponibles {len(feat_df)}."
        )

    # Precio actual (último cierre disponible)
    current_price = float(feat_df["Close"].iloc[-1])

    # Escalar features con el scaler guardado
    last_window_raw = feat_df[FEATURE_COLS].values[-window_size:]
    last_window_scaled = scaler.transform(last_window_raw)

    # Tensor de entrada: [1, window_size, n_features]
    input_tensor = (
        torch.from_numpy(last_window_scaled).float().unsqueeze(0).to(device)
    )

    # Predicción de cada modelo
    individual_returns = []
    for model in models:
        model.eval()
        with torch.no_grad():
            pred_return = model(input_tensor).item()
        individual_returns.append(pred_return)

    # Tendencia por voto mayoritario
    votes = []
    for ret in individual_returns:
        if ret > threshold:
            votes.append("ALCISTA")
        elif ret < -threshold:
            votes.append("BAJISTA")
        else:
            votes.append("LATERAL")

    # Tendencia ganadora y confianza
    from collections import Counter
    vote_counts = Counter(votes)
    winning_trend, winning_count = vote_counts.most_common(1)[0]
    confidence = winning_count / ENSEMBLE_SIZE

    # Estadísticas de retornos
    mean_return = float(np.mean(individual_returns))
    std_return = float(np.std(individual_returns))

    predicted_price = current_price * np.exp(mean_return)
    price_upper = current_price * np.exp(mean_return + std_return)
    price_lower = current_price * np.exp(mean_return - std_return)

    return {
        "trend": winning_trend,
        "confidence": confidence,
        "current_price": current_price,
        "predicted_price": float(predicted_price),
        "price_upper": float(price_upper),
        "price_lower": float(price_lower),
        "predicted_return": mean_return,
        "individual_predictions": [
            {"model_id": i + 1, "predicted_return": r}
            for i, r in enumerate(individual_returns)
        ],
    }
