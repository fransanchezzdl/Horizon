"""
Gestión del ensemble de modelos BiGRU para el predictor Horizon.

Entrena N modelos con diferentes hiperparámetros y semillas de inicialización,
y combina sus predicciones mediante voto mayoritario para la tendencia
y estadísticas sobre los retornos predichos para el precio orientativo.
"""

import json
import os
import pickle
import torch
import numpy as np
from datetime import datetime, timezone
from typing import List

from .config import (
    ENSEMBLE_SIZE,
    ENSEMBLE_VARIATIONS,
    FEATURE_COLS,
    SAVED_MODELS_DIR,
    TICKERS,
    get_config,
    get_asset_type,
    get_feature_cols,
)
from .data_pipeline import (
    prepare_data,
    prepare_data_multi_window,
    load_scaler,
    download_data,
    compute_features,
)
from .model import HorizonBiGRU
from .trainer import train_single_model, evaluate_model


def train_ensemble(ticker: str) -> dict:
    """
    Entrena el ensemble completo de N modelos para un ticker dado.

    Cada modelo usa hiperparámetros diferentes (ENSEMBLE_VARIATIONS) para
    introducir diversidad real en el ensemble. Los datos se preparan una vez
    por cada window_size único para evitar descargas redundantes.

    Args:
        ticker: Símbolo del activo (ej: 'KO', 'TSLA').

    Returns:
        Diccionario con métricas agregadas del ensemble.
    """
    config = get_config(ticker)
    asset_type = get_asset_type(ticker)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    variations = ENSEMBLE_VARIATIONS[asset_type]

    print(f"\n{'='*60}")
    print(f"🎯 Entrenando ensemble para {ticker} ({ENSEMBLE_SIZE} modelos)")
    print(f"   Dispositivo: {device}")
    print(f"{'='*60}")

    # Preparar todos los datos UNA SOLA VEZ para todos los window_sizes
    unique_window_sizes = list(set(v["window_size"] for v in variations))
    all_data = prepare_data_multi_window(ticker, config, unique_window_sizes)
    dynamic_threshold = all_data["dynamic_threshold"]

    # Guardar threshold dinámico para inferencia
    os.makedirs(SAVED_MODELS_DIR, exist_ok=True)
    threshold_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_threshold.pkl")
    with open(threshold_path, "wb") as f:
        pickle.dump(dynamic_threshold, f)

    individual_metrics = []

    for model_idx, variation in enumerate(variations):
        model_config = config.copy()
        model_config.update(variation)

        ws = variation["window_size"]
        data = all_data[ws]  # Datos para este window_size específico

        metrics = train_single_model(ticker, model_idx, model_config, data, device)
        # Evaluar en test
        model = _load_single_model(ticker, model_idx, model_config, device)
        test_metrics = evaluate_model(
            model, data["X_test"], data["y_test"], device
        )
        metrics.update(test_metrics)
        individual_metrics.append(metrics)

    # Guardar pesos del ensemble (val_loss por modelo)
    model_weights = {i: m["best_val_loss"] for i, m in enumerate(individual_metrics)}
    weights_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_weights.pkl")
    with open(weights_path, "wb") as f:
        pickle.dump(model_weights, f)
    print(f"⚖️ Pesos del ensemble guardados en {weights_path}")

    avg_val_loss = float(
        np.mean([m["best_val_loss"] for m in individual_metrics])
    )
    avg_dir_acc = float(
        np.mean([m["directional_accuracy"] for m in individual_metrics])
    )
    avg_mae = float(np.mean([m["mae"] for m in individual_metrics]))
    avg_rmse = float(np.mean([m["rmse"] for m in individual_metrics]))
    avg_precision_up = float(np.mean([m["precision_up"] for m in individual_metrics]))
    avg_recall_up = float(np.mean([m["recall_up"] for m in individual_metrics]))

    print(f"\n✅ Ensemble {ticker} completado:")
    print(f"   Val Loss medio: {avg_val_loss:.6f}")
    print(f"   Accuracy direccional media (test): {avg_dir_acc:.2%}")
    print(f"   Threshold dinámico: ±{dynamic_threshold:.4f} ({dynamic_threshold * 100:.2f}%)")

    # Guardar informe JSON
    report = {
        "ticker": ticker,
        "asset_type": asset_type,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_models": ENSEMBLE_SIZE,
        "config_used": config,
        "feature_cols": get_feature_cols(ticker),
        "dynamic_threshold": dynamic_threshold,
        "metrics": {
            "avg_val_loss": avg_val_loss,
            "avg_directional_accuracy": avg_dir_acc,
            "avg_mae": avg_mae,
            "avg_rmse": avg_rmse,
            "avg_precision_up": avg_precision_up,
            "avg_recall_up": avg_recall_up,
            "naive_baseline_accuracy": individual_metrics[0].get(
                "naive_baseline_accuracy", None
            ),
        },
        "individual_models": [
            {
                "model_idx": i,
                "seed": 42 + i,
                "variation": variations[i],
                "val_loss": m["best_val_loss"],
                "epochs_trained": m["epochs_trained"],
                "directional_accuracy": m["directional_accuracy"],
                "mae": m["mae"],
                "rmse": m["rmse"],
                "precision_up": m["precision_up"],
                "recall_up": m["recall_up"],
            }
            for i, m in enumerate(individual_metrics)
        ],
    }

    os.makedirs(SAVED_MODELS_DIR, exist_ok=True)
    report_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print(f"📄 Informe guardado en {report_path}")

    return {
        "ticker": ticker,
        "n_models": ENSEMBLE_SIZE,
        "individual_metrics": individual_metrics,
        "avg_val_loss": avg_val_loss,
        "avg_directional_accuracy": avg_dir_acc,
        "avg_mae": avg_mae,
        "avg_rmse": avg_rmse,
        "avg_precision_up": avg_precision_up,
        "avg_recall_up": avg_recall_up,
        "dynamic_threshold": dynamic_threshold,
    }


def _load_single_model(
    ticker: str, model_idx: int, config: dict, device: torch.device
) -> HorizonBiGRU:
    """
    Carga un único modelo guardado desde disco.

    Args:
        ticker: Símbolo del activo.
        model_idx: Índice del modelo dentro del ensemble.
        config: Diccionario de configuración (puede incluir variación específica).
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

    feature_cols = get_feature_cols(ticker)
    model = HorizonBiGRU(
        input_dim=len(feature_cols),
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
    asset_type = get_asset_type(ticker)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    variations = ENSEMBLE_VARIATIONS[asset_type]

    models = []
    for model_idx, variation in enumerate(variations):
        model_config = config.copy()
        model_config.update(variation)
        model = _load_single_model(ticker, model_idx, model_config, device)
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
    asset_type = get_asset_type(ticker)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    variations = ENSEMBLE_VARIATIONS[asset_type]

    # Cargar threshold dinámico si está disponible, si no usar el fijo de config
    threshold_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_threshold.pkl")
    if os.path.exists(threshold_path):
        with open(threshold_path, "rb") as f:
            threshold = pickle.load(f)
        print(f"📏 Usando threshold dinámico: ±{threshold:.4f}")
    else:
        threshold = config["trend_threshold"]
        print(f"⚠️ Threshold dinámico no encontrado, usando fijo: ±{threshold}")

    # Cargar pesos del ensemble basados en val_loss
    weights_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_weights.pkl")
    if os.path.exists(weights_path):
        with open(weights_path, "rb") as f:
            val_losses = pickle.load(f)
        # Pesos inversamente proporcionales al val_loss: menor pérdida = mayor peso
        # Se añade epsilon para evitar división por cero si val_loss == 0.0
        inv_losses = {k: 1.0 / (v + 1e-8) for k, v in val_losses.items()}
        total_inv = sum(inv_losses.values())
        # Si faltan índices (modelos no entrenados), usar peso uniforme como fallback
        if all(i in inv_losses for i in range(ENSEMBLE_SIZE)):
            model_weights = [inv_losses[i] / total_inv for i in range(ENSEMBLE_SIZE)]
        else:
            model_weights = [1.0 / ENSEMBLE_SIZE] * ENSEMBLE_SIZE
        print(f"⚖️ Pesos ponderados: {[f'{w:.3f}' for w in model_weights]}")
    else:
        model_weights = [1.0 / ENSEMBLE_SIZE] * ENSEMBLE_SIZE

    # Tamaño máximo de ventana para descargar datos suficientes
    max_window_size = max(v["window_size"] for v in variations)

    scaler = load_scaler(ticker)

    # Descargar datos recientes y calcular features
    include_market_context = ticker in TICKERS["volatile"]
    raw_df = download_data(ticker)
    feat_df = compute_features(raw_df, include_market_context=include_market_context)
    feature_cols = get_feature_cols(ticker)

    if len(feat_df) < max_window_size:
        raise ValueError(
            f"Datos insuficientes para {ticker}: "
            f"se necesitan al menos {max_window_size} filas, "
            f"disponibles {len(feat_df)}."
        )

    # Precio actual (último cierre disponible)
    current_price = float(feat_df["Close"].iloc[-1])

    # Escalar la ventana máxima de features con el scaler guardado
    last_window_raw = feat_df[feature_cols].values[-max_window_size:]
    last_window_scaled = scaler.transform(last_window_raw)

    # Cargar ensemble de modelos (evita I/O redundante por modelo)
    models = load_ensemble(ticker)

    # Predicción de cada modelo con su window_size específico
    individual_returns = []
    for model, variation in zip(models, variations):
        ws = variation["window_size"]
        window_slice = last_window_scaled[-ws:]
        input_tensor = (
            torch.from_numpy(window_slice).float().unsqueeze(0).to(device)
        )

        model.eval()
        with torch.no_grad():
            pred_return = model(input_tensor).item()
        individual_returns.append(pred_return)

    # Votación ponderada para tendencia
    trend_weights = {"ALCISTA": 0.0, "BAJISTA": 0.0, "LATERAL": 0.0}
    for ret, weight in zip(individual_returns, model_weights):
        if ret > threshold:
            trend_weights["ALCISTA"] += weight
        elif ret < -threshold:
            trend_weights["BAJISTA"] += weight
        else:
            trend_weights["LATERAL"] += weight

    winning_trend = max(trend_weights, key=trend_weights.get)
    confidence = trend_weights[winning_trend]  # Ya en rango 0-1 (pesos suman 1)

    # Retorno ponderado por rendimiento de los modelos
    weighted_return = sum(w * r for w, r in zip(model_weights, individual_returns))
    mean_return = float(weighted_return)
    std_return = float(np.std(individual_returns))

    predicted_price = current_price * np.exp(mean_return)
    price_upper = current_price * np.exp(mean_return + std_return)
    price_lower = current_price * np.exp(mean_return - std_return)

    return {
        "trend": winning_trend,
        "confidence": round(confidence, 4),
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