"""
Modelo XGBoost complementario para el predictor Horizon.

Entrena un clasificador binario que predice la dirección del precio:
    1 → precio sube (retorno > 0)
    0 → precio baja o se mantiene (retorno ≤ 0)

Usa las mismas features técnicas (+ sentimiento si está activo) que el BiGRU,
pero solo emplea el ÚLTIMO timestep de cada ventana (XGBoost no usa secuencias).

Funciones:
    - train_xgboost(ticker, data, feature_cols) → dict de métricas
    - predict_xgboost(ticker, features)         → {"direction": 0/1, "probability": float}
"""

import os
import pickle
import logging
from typing import Dict

import numpy as np

from .config import SAVED_MODELS_DIR, XGBOOST_CONFIG

logger = logging.getLogger(__name__)


def _get_xgb_classifier():
    """
    Importa XGBClassifier dinámicamente para evitar errores en caso de que
    xgboost no esté instalado.
    """
    try:
        from xgboost import XGBClassifier
        return XGBClassifier
    except ImportError:
        raise ImportError(
            "El paquete 'xgboost' no está instalado. "
            "Instálalo con: pip install xgboost>=2.0.0"
        )


def train_xgboost(ticker: str, data: dict, feature_cols: list) -> dict:
    """
    Entrena el clasificador XGBoost con los datos del pipeline.

    Extrae el último timestep de cada secuencia BiGRU para construir
    el dataset tabular de XGBoost. Las etiquetas son 1 si el retorno
    es positivo, 0 en caso contrario.

    Args:
        ticker:       Símbolo del activo (ej: 'KO', 'TSLA').
        data:         Diccionario devuelto por prepare_data() con:
                          X_train, y_train, X_val, y_val, X_test, y_test
                          (todos son tensores PyTorch).
        feature_cols: Lista de nombres de features (solo para logs).

    Returns:
        Diccionario con métricas de test:
            - xgb_directional_accuracy
            - xgb_precision_up
            - xgb_recall_up
            - feature_importance (top 10 features)
    """
    XGBClassifier = _get_xgb_classifier()

    # ── Extraer último timestep de cada secuencia ──────────────────────────────
    # X tiene forma [n_sequences, window_size, n_features]; tomamos [:, -1, :]
    X_train = data["X_train"].numpy()[:, -1, :]
    y_train_raw = data["y_train"].numpy().ravel()

    X_val = data["X_val"].numpy()[:, -1, :]
    y_val_raw = data["y_val"].numpy().ravel()

    X_test = data["X_test"].numpy()[:, -1, :]
    y_test_raw = data["y_test"].numpy().ravel()

    # Etiquetas binarias: 1 si retorno > 0
    y_train = (y_train_raw > 0).astype(int)
    y_val = (y_val_raw > 0).astype(int)
    y_test = (y_test_raw > 0).astype(int)

    cfg = XGBOOST_CONFIG
    model = XGBClassifier(
        n_estimators=cfg["n_estimators"],
        max_depth=cfg["max_depth"],
        learning_rate=cfg["learning_rate"],
        subsample=cfg["subsample"],
        colsample_bytree=cfg["colsample_bytree"],
        early_stopping_rounds=cfg["early_stopping_rounds"],
        eval_metric="logloss",
        use_label_encoder=False,
        verbosity=0,
        random_state=42,
    )

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    # ── Métricas en test ───────────────────────────────────────────────────────
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    dir_acc = float(np.mean(y_pred == y_test))

    # Precision y recall para clase 1 (alcista)
    tp = int(np.sum((y_pred == 1) & (y_test == 1)))
    fp = int(np.sum((y_pred == 1) & (y_test == 0)))
    fn = int(np.sum((y_pred == 0) & (y_test == 1)))

    precision_up = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall_up = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    # ── Importancia de features (top 10) ──────────────────────────────────────
    importances = model.feature_importances_
    top_n = min(10, len(feature_cols))
    top_indices = np.argsort(importances)[::-1][:top_n]
    feature_importance = {
        feature_cols[i]: round(float(importances[i]), 6)
        for i in top_indices
    }

    # ── Guardar modelo ─────────────────────────────────────────────────────────
    os.makedirs(SAVED_MODELS_DIR, exist_ok=True)
    model_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    logger.info("XGBoost guardado en %s", model_path)

    print(f"🌳 XGBoost {ticker} — Dir. Acc: {dir_acc:.2%} | "
          f"Prec↑: {precision_up:.2%} | Rec↑: {recall_up:.2%}")

    return {
        "xgb_directional_accuracy": dir_acc,
        "xgb_precision_up": precision_up,
        "xgb_recall_up": recall_up,
        "feature_importance": feature_importance,
    }


def predict_xgboost(ticker: str, features: np.ndarray) -> Dict:
    """
    Realiza una predicción de dirección con el modelo XGBoost guardado.

    Args:
        ticker:   Símbolo del activo.
        features: Array 1D o 2D con las features del ÚLTIMO timestep.
                  Forma esperada: [n_features] o [1, n_features].

    Returns:
        Diccionario con:
            - direction:   0 (bajista) o 1 (alcista)
            - probability: probabilidad de subida [0.0, 1.0]

    En caso de error devuelve direction=0, probability=0.5 (neutral).
    """
    model_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost.pkl")
    if not os.path.exists(model_path):
        logger.warning("Modelo XGBoost no encontrado para %s: %s", ticker, model_path)
        return {"direction": 0, "probability": 0.5}

    try:
        with open(model_path, "rb") as f:
            model = pickle.load(f)

        arr = np.array(features)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)

        direction = int(model.predict(arr)[0])
        probability = float(model.predict_proba(arr)[0, 1])

        return {"direction": direction, "probability": probability}

    except Exception as exc:
        logger.warning("Error en predict_xgboost para %s: %s", ticker, exc)
        return {"direction": 0, "probability": 0.5}
