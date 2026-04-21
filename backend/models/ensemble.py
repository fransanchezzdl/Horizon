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
    META_ENSEMBLE_WEIGHTS,
    META_ENSEMBLE_SIGMOID_SCALE,
    META_ENSEMBLE_TREND_DELTA,
    USE_ATTENTION_MODEL,
    get_config,
    get_asset_type,
    get_feature_cols,
)
from .data_pipeline import (
    prepare_data,
    prepare_data_multi_window,
    load_scaler,
    load_feature_cols,
    download_data,
    compute_features,
)
from .model import HorizonBiGRU, HorizonBiGRUAttention
from .trainer import train_single_model, evaluate_model
from .xgboost_model import train_xgboost, predict_xgboost
from .meta_ensemble import get_meta_ensemble_prediction


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
    avg_test_accuracy = float(
        np.mean([m.get("accuracy", 0.0) for m in individual_metrics])
    )
    avg_f1_weighted = float(
        np.mean([m.get("f1_weighted", 0.0) for m in individual_metrics])
    )

    print(f"\n✅ Ensemble {ticker} completado:")
    print(f"   Val Loss medio: {avg_val_loss:.6f}")
    print(f"   Test Accuracy media: {avg_test_accuracy:.2%}")
    print(f"   Test F1 Weighted media: {avg_f1_weighted:.4f}")
    print(f"   Threshold dinámico: ±{dynamic_threshold:.4f} ({dynamic_threshold * 100:.2f}%)")

    # ── Entrenar XGBoost con los mismos datos ──────────────────────────────────
    xgb_metrics = {}
    feature_cols = get_feature_cols(ticker)
    # Usamos el dataset con el window_size mayor para tener más contexto
    max_ws = max(v["window_size"] for v in variations)
    xgb_data = all_data[max_ws]  # type: ignore
    try:
        xgb_metrics = train_xgboost(ticker, xgb_data, feature_cols)
    except Exception as exc:
        print(f"⚠️  XGBoost no entrenado para {ticker}: {exc}")

    # ── Guardar informe JSON ───────────────────────────────────────────────────
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
            "avg_test_accuracy": avg_test_accuracy,
            "avg_f1_weighted": avg_f1_weighted,
        },
        "xgboost_metrics": xgb_metrics,
        "individual_models": [
            {
                "model_idx": i,
                "seed": 42 + i,
                "variation": variations[i],
                "val_loss": m["best_val_loss"],
                "epochs_trained": m["epochs_trained"],
                "test_accuracy": m.get("accuracy", 0.0),
                "f1_weighted": m.get("f1_weighted", 0.0),
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
        "avg_test_accuracy": avg_test_accuracy,
        "avg_f1_weighted": avg_f1_weighted,
        "dynamic_threshold": dynamic_threshold,
        "xgboost_metrics": xgb_metrics,
    }


def _load_single_model(
    ticker: str, model_idx: int, config: dict, device: torch.device
) -> HorizonBiGRU:
    """
    Carga un único modelo guardado desde disco.
    Usa HorizonBiGRUAttention si USE_ATTENTION_MODEL=True.
    """
    model_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_model_{model_idx}.pth")
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Modelo no encontrado: {model_path}. "
            f"Ejecuta train_ensemble('{ticker}') primero."
        )

    feature_cols = load_feature_cols(ticker)
    ModelClass = HorizonBiGRUAttention if USE_ATTENTION_MODEL else HorizonBiGRU
    model = ModelClass(
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
    feat_df = compute_features(
        raw_df,
        include_market_context=include_market_context,
        ticker=ticker,
    )
    feature_cols = load_feature_cols(ticker)

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
    # El modelo devuelve un retorno continuo [1, 1]
    individual_returns = []

    for model, variation in zip(models, variations):
        ws = variation["window_size"]
        window_slice = last_window_scaled[-ws:]
        input_tensor = (
            torch.from_numpy(window_slice).float().unsqueeze(0).to(device)
        )

        model.eval()
        with torch.no_grad():
            logits = model(input_tensor)  # [1, 3] para 3 clases (BAJISTA, LATERAL, ALCISTA)
            probs = torch.softmax(logits, dim=1)[0]  # [3] probabilidades
            
            # Convertir probabilidades a "retorno equivalente"
            # ALCISTA (clase 2) - BAJISTA (clase 0)
            # Esto mapea [0, 1] a [-1, 1] aproximadamente
            pred_return = (probs[2] - probs[0]).item()

        individual_returns.append(pred_return)

    # Votación ponderada sobre retornos predichos
    mean_return = float(np.average(individual_returns, weights=model_weights))
    std_return  = float(np.std(individual_returns))

    # Tendencia por threshold
    if mean_return > threshold:
        winning_trend = "ALCISTA"
    elif mean_return < -threshold:
        winning_trend = "BAJISTA"
    else:
        winning_trend = "LATERAL"

    # Confianza: qué fracción de modelos coincide con la tendencia ganadora
    if winning_trend == "ALCISTA":
        confidence = float(np.mean([r > threshold for r in individual_returns]))
    elif winning_trend == "BAJISTA":
        confidence = float(np.mean([r < -threshold for r in individual_returns]))
    else:
        confidence = float(np.mean([abs(r) <= threshold for r in individual_returns]))

    predicted_price = current_price * np.exp(mean_return)
    price_upper = current_price * np.exp(mean_return + std_return)
    price_lower = current_price * np.exp(mean_return - std_return)

    # ── Meta-ensemble: combinar BiGRU + XGBoost ────────────────────────────────
    # Obtener predicción XGBoost con el último timestep (features raw)
    last_features_raw = feat_df[feature_cols].values[-1]
    xgb_result = predict_xgboost(ticker, last_features_raw, confidence_tau=0.40)
    xgb_prob = xgb_result["probability"]

    # Salvaguarda: si el BiGRU de este ticker tiene F1 < 0.20 (modelo roto,
    # p.ej. NVDA/TSLA donde early stopping capturó pesos inútiles), ignorar
    # su contribución y usar solo XGBoost para no contaminar la predicción.
    _bigru_weights = None  # None = usar META_ENSEMBLE_WEIGHTS por defecto
    try:
        import json as _json
        _report_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_report.json")
        with open(_report_path) as _f:
            _report = _json.load(_f)
        _bigru_f1 = _report.get("metrics", {}).get("avg_f1_weighted", 1.0)
        if _bigru_f1 < 0.20:
            _bigru_weights = {"bigru": 0.0, "xgboost": 1.0}
            print(f"   ⚠️  BiGRU {ticker} ignorado (F1={_bigru_f1:.3f} < 0.20) → usando solo XGBoost")
    except Exception:
        pass  # sin report → comportamiento normal

    # Intentar usar ensemble stacking si está disponible
    stacking_available = False
    try:
        from .ensemble_stacking import load_stacking_metalearner
        stacking_meta = load_stacking_metalearner(ticker, verbose=False)
        if stacking_meta is not None:
            # Generar predicciones de BiGRU para stacking
            bigru_proba_stacking = []
            for model in models:
                proba = torch.softmax(
                    model(torch.from_numpy(last_window_scaled).float().unsqueeze(0).to(device)),
                    dim=1
                ).detach().cpu().numpy()[0]  # [3] para ultima predicción
                bigru_proba_stacking.append(proba)
            bigru_proba_mean = np.mean(bigru_proba_stacking, axis=0)  # [3]
            
            # XGBoost predicción (v5: direction ya es ternario 0/1/2)
            xgb_pred = xgb_result.get("direction", 1)  # 0=BAJISTA, 1=LATERAL, 2=ALCISTA
            
            # Usar stacking para combinar
            X_stacking = stacking_meta.create_stacking_features(
                np.array([bigru_proba_mean]),  # (1, 3)
                np.array([xgb_pred]),  # (1,)
                np.array([xgb_result.get("all_proba", [0.33, 0.33, 0.33])])  # (1, 3)
            )
            y_stacking, proba_stacking = stacking_meta.predict_ensemble(
                np.array([bigru_proba_mean]),
                np.array([xgb_pred]),
                np.array([xgb_result.get("all_proba", [0.33, 0.33, 0.33])])
            )
            
            # Convertir predicción stacking a tendencia
            stacking_pred = y_stacking[0]  # 0, 1, 2
            stacking_proba = proba_stacking[0]  # [p0, p1, p2]
            
            if stacking_pred == 2:
                stacking_trend = "ALCISTA"
            elif stacking_pred == 0:
                stacking_trend = "BAJISTA"
            else:
                stacking_trend = "LATERAL"
            
            meta_result = {"meta_trend": stacking_trend, "meta_score": float(stacking_proba.max())}
            stacking_available = True
            print(f"   🔗 Usando Ensemble Stacking: {stacking_trend} (confidence: {stacking_proba.max():.2%})")
    except (ImportError, FileNotFoundError, Exception) as e:
        # Si stacking no disponible, usar meta-ensemble original
        meta_result = get_meta_ensemble_prediction(mean_return, xgb_prob, weights=_bigru_weights)

    # Si stacking no disponible, usar meta-ensemble
    if not stacking_available:
        meta_result = get_meta_ensemble_prediction(mean_return, xgb_prob, weights=_bigru_weights)

    return {
        "trend": winning_trend,
        "confidence": round(confidence, 4),
        "current_price": current_price,
        "predicted_price": float(predicted_price),
        "price_upper": float(price_upper),
        "price_lower": float(price_lower),
        "predicted_return": mean_return,
        "predicted_return_pct": round(mean_return * 100, 2),

        # Meta-ensemble results
        "meta_trend": meta_result["meta_trend"],
        "meta_score": round(meta_result["meta_score"], 6),

        # XGBoost results (v5: direction es ternario 0=BAJISTA, 1=LATERAL, 2=ALCISTA)
        "xgboost_direction": {0: "BAJISTA", 1: "LATERAL", 2: "ALCISTA"}.get(xgb_result["direction"], "LATERAL"),
        "xgboost_probability": round(xgb_prob, 6),
        "xgboost_all_proba": {
            "bajista": round(float(xgb_result.get("probability_bajista", xgb_result.get("all_proba", [0.33, 0.34, 0.33])[0])), 4),
            "lateral": round(float(xgb_result.get("probability_lateral", xgb_result.get("all_proba", [0.33, 0.34, 0.33])[1])), 4),
            "alcista": round(float(xgb_result.get("probability_alcista", xgb_result.get("all_proba", [0.33, 0.34, 0.33])[2])), 4),
        },

        # Individual predictions
        "individual_predictions": [
            {"model_id": i + 1, "predicted_return": r, "predicted_return_pct": round(r * 100, 2)}
            for i, r in enumerate(individual_returns)
        ],
    }