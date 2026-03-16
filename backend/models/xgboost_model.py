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

    # ── Construir features temporales agregadas ────────────────────────────────
    # Usamos estadísticas de toda la ventana: last, mean, std, trend por feature.
    # Esto da al XGBoost información temporal sin necesitar secuencias.
    def build_xgb_features(X_tensor):
        X = X_tensor.numpy()  # [n, window, features]
        last  = X[:, -1, :]
        mean  = X.mean(axis=1)
        std   = X.std(axis=1)
        trend = X[:, -1, :] - X[:, 0, :]  # cambio total en la ventana
        return np.concatenate([last, mean, std, trend], axis=1)

    X_train = build_xgb_features(data["X_train"])
    X_val   = build_xgb_features(data["X_val"])
    X_test  = build_xgb_features(data["X_test"])

    # y son clases enteras (0=BAJISTA, 1=LATERAL, 2=ALCISTA)
    y_train = data["y_train"].numpy().ravel()
    y_val   = data["y_val"].numpy().ravel()
    y_test  = data["y_test"].numpy().ravel()

    cfg = XGBOOST_CONFIG
    model = XGBClassifier(
        n_estimators=cfg["n_estimators"],
        max_depth=cfg["max_depth"],
        learning_rate=cfg["learning_rate"],
        subsample=cfg["subsample"],
        colsample_bytree=cfg["colsample_bytree"],
        early_stopping_rounds=cfg["early_stopping_rounds"],
        eval_metric="mlogloss",
        objective="multi:softprob",
        num_class=3,
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
    y_prob = model.predict_proba(X_test)[:, 2]  # probabilidad clase ALCISTA (2)

    dir_acc = float(np.mean(y_pred == y_test))

    # Precision y recall para clase 2 (ALCISTA)
    tp = int(np.sum((y_pred == 2) & (y_test == 2)))
    fp = int(np.sum((y_pred == 2) & (y_test != 2)))
    fn = int(np.sum((y_pred != 2) & (y_test == 2)))

    precision_up = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall_up = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    # ── Importancia de features (top 10) ──────────────────────────────────────
    # Las features expandidas son 4x (last, mean, std, trend), pero solo
    # reportamos las del último timestep (primeras n_features columnas)
    importances = model.feature_importances_
    n_features = len(feature_cols)
    # Tomar solo las importancias del bloque "last" (primeras n_features)
    last_importances = importances[:n_features]
    top_n = min(10, n_features)
    top_indices = np.argsort(last_importances)[::-1][:top_n]
    feature_importance = {
        feature_cols[i]: round(float(last_importances[i]), 6)
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
        # En clasificación 3 clases: 0=BAJISTA, 1=LATERAL, 2=ALCISTA
        probs = model.predict_proba(arr)[0]
        probability = float(probs[2]) if len(probs) == 3 else float(probs[-1])

        return {"direction": direction, "probability": probability}

    except Exception as exc:
        logger.warning("Error en predict_xgboost para %s: %s", ticker, exc)
        return {"direction": 0, "probability": 0.5}
