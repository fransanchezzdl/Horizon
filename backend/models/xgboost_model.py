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

import json
import os
import pickle
import logging
from datetime import datetime
from typing import Dict, Tuple

import numpy as np

from .config import SAVED_MODELS_DIR, XGBOOST_CONFIG, LABELING_FIXED_THRESHOLDS
from .platt_scaling_calibration_v2 import load_calibrator

logger = logging.getLogger(__name__)

THRESHOLDS_FROZEN_FILE = os.path.join(os.path.dirname(__file__), "thresholds_frozen.json")


def _load_frozen_thresholds(ticker: str) -> Tuple[float, float]:
    """
    Carga los umbrales de etiquetado FROZEN para un ticker desde JSON versionado.

    Si el archivo no existe o el ticker no está calibrado, hace fallback al
    universal LABELING_FIXED_THRESHOLDS y emite warning. En producción debe
    haberse ejecutado `calibrate_thresholds.py` previamente.

    Returns: (down_threshold, up_threshold)
    """
    if os.path.exists(THRESHOLDS_FROZEN_FILE):
        try:
            with open(THRESHOLDS_FROZEN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if ticker in data:
                return data[ticker]["bajista"], data[ticker]["alcista"]
            logger.warning(
                f"[{ticker}] no calibrado en {THRESHOLDS_FROZEN_FILE}. "
                f"Ejecutar: python -m backend.models.calibrate_thresholds"
            )
        except Exception as e:
            logger.warning(f"No se pudo cargar {THRESHOLDS_FROZEN_FILE}: {e}")
    else:
        logger.warning(
            f"{THRESHOLDS_FROZEN_FILE} no existe. "
            f"Usando LABELING_FIXED_THRESHOLDS universal como fallback."
        )
    return LABELING_FIXED_THRESHOLDS["bajista"], LABELING_FIXED_THRESHOLDS["alcista"]


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


def train_xgboost(ticker: str, data: dict, feature_cols: list, asset_type: str = "stable", seed: int = 42) -> dict:
    """
    Entrena el clasificador XGBoost con los datos del pipeline.

    CAMBIOS PARA CORREGIR SESGO ALCISTA:
    1. Target temporal estricto: y_t = (close[t+1] > close[t]) sin leakage
    2. Dual threshold con zona LATERAL
    3. Scale pos weight para balancear clases
    4. Métricas robustas: balanced accuracy + confusion matrix
    5. Persistencia de umbrales y probabilidades
    6. Configuración segregada por tipo de activo (NUEVO)

    Extrae el último timestep de cada secuencia BiGRU para construir
    el dataset tabular de XGBoost. Las etiquetas son 0=BAJISTA, 1=LATERAL, 2=ALCISTA.

    Args:
        ticker:       Símbolo del activo (ej: 'KO', 'TSLA').
        data:         Diccionario devuelto por prepare_data() con:
                          X_train, y_train, X_val, y_val, X_test, y_test
                          (todos son tensores PyTorch).
        feature_cols: Lista de nombres de features (solo para logs).
        asset_type:   Tipo de activo ('stable' o 'volatile') para seleccionar config.
        seed:         Random seed para reproducibilidad (default=42 para Phase 3, 123/456 para Phase 4 ensemble).

    Returns:
        Diccionario con métricas de test:
            - xgb_directional_accuracy
            - xgb_balanced_accuracy (métrica principal para desbalance)
            - xgb_macro_f1
            - xgb_confusion_matrix (dict)
            - xgb_class_distribution (train/val/test)
            - xgb_precision_up, xgb_recall_up (para compatibilidad)
            - xgb_down_threshold, xgb_up_threshold (umbrales calibrados)
            - feature_importance (top 10 features)
    """
    XGBClassifier = _get_xgb_classifier()
    from sklearn.metrics import balanced_accuracy_score, f1_score, confusion_matrix

    # ── Construir features temporales agregadas ────────────────────────────────
    # Estadísticas de la ventana completa: last, mean, std, trend por feature.
    # Esto da al XGBoost señal temporal sin necesitar secuencias recurrentes.
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

    # ── Obtener retornos continuos ─────────────────────────────────────────────
    # Preferir y_*_returns (retornos continuos) si existen; si no, usar y_* directamente
    def _get_returns(split_key: str) -> np.ndarray:
        val = data.get(f"y_{split_key}_returns", None)
        if val is None:
            val = data[f"y_{split_key}"]
        arr = val.numpy() if hasattr(val, "numpy") else np.array(val)
        return arr.ravel()

    y_train_continuous = _get_returns("train")
    y_val_continuous   = _get_returns("val")
    y_test_continuous  = _get_returns("test")

    # ── Etiquetas FROZEN per-ticker (reproducibles + adaptadas a volatilidad) ──
    # Calibradas UNA VEZ con calibrate_thresholds.py y versionadas en JSON.
    # Mismo retorno → mismo label siempre, independientemente de cuándo se reentrene.
    down_threshold, up_threshold = _load_frozen_thresholds(ticker)
    logger.info(
        f"[{ticker}] frozen thresholds: BAJISTA<={down_threshold:+.4f} | ALCISTA>={up_threshold:+.4f}"
    )

    def returns_to_classes(returns: np.ndarray, down_th: float, up_th: float) -> np.ndarray:
        classes = np.ones(len(returns), dtype=int)  # LATERAL por defecto
        classes[returns <= down_th] = 0  # BAJISTA
        classes[returns >= up_th]   = 2  # ALCISTA
        return classes

    y_train = returns_to_classes(y_train_continuous, down_threshold, up_threshold)
    y_val   = returns_to_classes(y_val_continuous,   down_threshold, up_threshold)
    y_test  = returns_to_classes(y_test_continuous,  down_threshold, up_threshold)

    # Distribución de clases para logging
    train_dist = np.bincount(y_train, minlength=3) / len(y_train) * 100
    val_dist   = np.bincount(y_val,   minlength=3) / len(y_val)   * 100
    test_dist  = np.bincount(y_test,  minlength=3) / len(y_test)  * 100

    logger.info(f"📊 Class distribution TRAIN: BAJISTA={train_dist[0]:.1f}% LATERAL={train_dist[1]:.1f}% ALCISTA={train_dist[2]:.1f}%")
    logger.info(f"📊 Class distribution VAL:   BAJISTA={val_dist[0]:.1f}% LATERAL={val_dist[1]:.1f}% ALCISTA={val_dist[2]:.1f}%")
    logger.info(f"📊 Class distribution TEST:  BAJISTA={test_dist[0]:.1f}% LATERAL={test_dist[1]:.1f}% ALCISTA={test_dist[2]:.1f}%")

    # ── Pesos de muestra para balanceo multi-clase ─────────────────────────────
    # Cada clase pesa inversamente proporcional a su frecuencia en train.
    # Equivalente a sample_weight para multi:softprob.
    class_counts = np.bincount(y_train, minlength=3)
    sample_weights = np.ones(len(y_train), dtype=float)
    for cls in range(3):
        if class_counts[cls] > 0:
            sample_weights[y_train == cls] = len(y_train) / (3.0 * class_counts[cls])
    logger.info(f"🎯 Class counts: BAJISTA={class_counts[0]}, LATERAL={class_counts[1]}, ALCISTA={class_counts[2]}")

    # ── Seleccionar configuración por tipo de activo ───────────────────────────
    from .config import XGBOOST_STABLE_CONFIG, XGBOOST_VOLATILE_CONFIG
    cfg = XGBOOST_VOLATILE_CONFIG if asset_type == "volatile" else XGBOOST_STABLE_CONFIG
    logger.info(f"🎯 Usando config {asset_type.upper()} para {ticker}")

    # ── Modelo multi-clase nativo ──────────────────────────────────────────────
    # multi:softprob predice directamente P(BAJISTA), P(LATERAL), P(ALCISTA).
    # Sin post-procesado de umbrales: el argmax ya da la clase final.
    model = XGBClassifier(
        n_estimators=cfg["n_estimators"],
        max_depth=cfg["max_depth"],
        learning_rate=cfg["learning_rate"],
        subsample=cfg["subsample"],
        colsample_bytree=cfg["colsample_bytree"],
        min_child_weight=cfg.get("min_child_weight", 1.0),
        gamma=cfg.get("gamma", 0.0),
        early_stopping_rounds=cfg["early_stopping_rounds"],
        objective="multi:softprob",
        num_class=3,
        eval_metric="mlogloss",
        verbosity=0,
        random_state=seed,
    )

    model.fit(
        X_train,
        y_train,
        sample_weight=sample_weights,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    # ── Predicciones multi-clase ───────────────────────────────────────────────
    y_pred  = model.predict(X_test)        # shape [n], valores 0/1/2
    y_proba = model.predict_proba(X_test)  # shape [n, 3]: P(BAJ), P(LAT), P(ALC)

    # ── Calibración Platt Scaling (opcional) ──────────────────────────────────
    # Ajusta la magnitud de la confianza máxima, sin alterar el argmax.
    calibrator = load_calibrator(ticker)
    if calibrator is not None:
        logger.info(f"📊 Applying Platt Scaling calibration for {ticker}")
        max_conf = np.max(y_proba, axis=1).reshape(-1, 1)
        cal_conf = calibrator.predict_proba(max_conf)[:, 1]
        cal_conf = np.clip(cal_conf, 0.0, 1.0)
        scale_factor = cal_conf / (max_conf.flatten() + 1e-10)
        scale_factor = np.clip(scale_factor, 0.5, 2.0)
        y_proba = y_proba * scale_factor.reshape(-1, 1)
        y_proba = y_proba / (y_proba.sum(axis=1, keepdims=True) + 1e-10)
        logger.info(f"✅ Calibration applied. Confidence range: {cal_conf.min():.2%} - {cal_conf.max():.2%}")

    # Confianza = promedio de la probabilidad máxima por muestra
    confidence_score = float(np.mean(np.max(y_proba, axis=1)))

    # ── Métricas (multi-clase) ────────────────────────────────────────────────
    dir_acc      = float(np.mean(y_pred == y_test))
    balanced_acc = float(balanced_accuracy_score(y_test, y_pred))
    macro_f1     = float(f1_score(y_test, y_pred, average="macro", zero_division=0))

    cm_ternary = confusion_matrix(y_test, y_pred, labels=[0, 1, 2])

    # Métricas del ALCISTA (clase 2) para compatibilidad
    tp = int(cm_ternary[2, 2])
    fn = int(np.sum(cm_ternary[2, :]) - tp)
    fp = int(np.sum(cm_ternary[:, 2]) - tp)
    tn = int(np.sum(cm_ternary) - tp - fp - fn)

    cm_dict = {"tn": tn, "fp": fp, "fn": fn, "tp": tp}
    precision_up = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall_up    = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    # ── Importancia de features (top 10) ──────────────────────────────────────
    importances = model.feature_importances_
    n_features  = len(feature_cols)
    last_importances = importances[:n_features]  # bloque "last" del build_xgb_features
    top_n    = min(10, n_features)
    top_indices = np.argsort(last_importances)[::-1][:top_n]
    feature_importance = {
        feature_cols[i]: round(float(last_importances[i]), 6)
        for i in top_indices
    }

    # ── Guardar modelo y umbrales ─────────────────────────────────────────────
    os.makedirs(SAVED_MODELS_DIR, exist_ok=True)
    model_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    logger.info("XGBoost guardado en %s", model_path)

    thresholds = {
        "down_threshold": down_threshold,
        "up_threshold":   up_threshold,
        "ticker":         ticker,
        "timestamp":      datetime.now().isoformat(),
        "version":        "v5_multiclass_frozen_perticker",
        "source":         "thresholds_frozen.json",
    }
    thresholds_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost_thresholds.pkl")
    with open(thresholds_path, "wb") as f:
        pickle.dump(thresholds, f)
    logger.info(f"Thresholds saved: BAJISTA<={down_threshold:.3f}, ALCISTA>={up_threshold:.3f}")

    # Resumen
    print(f"\n🌳 XGBoost {ticker} TEST RESULTS (v5 multi-clase, etiquetas fijas):")
    print(f"   Balanced Accuracy:    {balanced_acc:.2%}")
    print(f"   Macro F1 Score:       {macro_f1:.2%}")
    print(f"   Directional Accuracy: {dir_acc:.2%}")
    print(f"   Precision (ALCISTA):  {precision_up:.2%}")
    print(f"   Recall (ALCISTA):     {recall_up:.2%}")
    print(f"   Confidence Score:     {confidence_score:.2%}")
    print(f"   Class dist [TRAIN]:   B={train_dist[0]:.1f}% L={train_dist[1]:.1f}% A={train_dist[2]:.1f}%")
    print(f"   Class dist [TEST]:    B={test_dist[0]:.1f}% L={test_dist[1]:.1f}% A={test_dist[2]:.1f}%")
    print(f"   Fixed thresholds:     BAJISTA<={down_threshold:.3f} | LATERAL | ALCISTA>={up_threshold:.3f}")

    return {
        "xgb_directional_accuracy": dir_acc,
        "xgb_balanced_accuracy":    balanced_acc,
        "xgb_macro_f1":             macro_f1,
        "xgb_precision_up":         precision_up,
        "xgb_recall_up":            recall_up,
        "xgb_confidence_score":     confidence_score,
        "xgb_confusion_matrix":     cm_dict,
        "xgb_class_distribution": {
            "train": {"BAJISTA": train_dist[0], "LATERAL": train_dist[1], "ALCISTA": train_dist[2]},
            "val":   {"BAJISTA": val_dist[0],   "LATERAL": val_dist[1],   "ALCISTA": val_dist[2]},
            "test":  {"BAJISTA": test_dist[0],  "LATERAL": test_dist[1],  "ALCISTA": test_dist[2]},
        },
        "xgb_down_threshold":    down_threshold,
        "xgb_up_threshold":      up_threshold,
        "xgb_scale_pos_weight":  1.0,  # Mantenido por compatibilidad (ahora se usa sample_weight)
        "feature_importance":    feature_importance,
    }


def predict_xgboost(ticker: str, features: np.ndarray, confidence_tau: float = 0.0) -> Dict:
    """
    Predicción multi-clase con XGBoost (v5).

    El modelo predice directamente P(BAJISTA), P(LATERAL), P(ALCISTA).
    La clase final es argmax de las probabilidades — sin post-procesado de umbrales.

    Args:
        ticker:          Símbolo del activo.
        features:        Array 1D o 2D con las features del ÚLTIMO timestep.
                         Forma esperada: [n_features] o [1, n_features].
        confidence_tau:  Umbral mínimo de confianza para emitir una predicción
                         direccional. Si max(proba) < tau → devuelve LATERAL
                         con abstained=True. Default 0.0 (sin abstención,
                         comportamiento original).
                         Valores recomendados: 0.40 (moderado), 0.45 (estricto).

    Returns:
        Diccionario con:
            - direction:       0=BAJISTA, 1=LATERAL, 2=ALCISTA
            - probability:     P(ALCISTA) — para compatibilidad con meta_ensemble
            - confidence:      max(probabilidades) — confianza real de la predicción
            - all_proba:       [P(BAJ), P(LAT), P(ALC)] — para stacking
            - abstained:       True si se abstuvo por baja confianza
            - model_id:        identificador del modelo
            - timestamp:       cuándo se hizo la predicción

    En caso de error devuelve direction=1 (LATERAL), probability=0.5.
    """
    model_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost.pkl")

    if not os.path.exists(model_path):
        logger.warning("Modelo XGBoost no encontrado para %s: %s", ticker, model_path)
        return {
            "direction": 1,
            "probability": 0.5,
            "confidence": 0.5,
            "all_proba": [0.33, 0.34, 0.33],
            "abstained": False,
            "error": "Model not found",
        }

    try:
        with open(model_path, "rb") as f:
            model = pickle.load(f)

        arr = np.array(features)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)

        # Probabilidades multi-clase: [P(BAJISTA), P(LATERAL), P(ALCISTA)]
        probs = model.predict_proba(arr)[0]  # shape [3]
        confidence = float(np.max(probs))

        # Abstención por baja confianza: si el modelo no está seguro de ninguna
        # clase, devolver LATERAL sin forzar una predicción errónea.
        # Esto mejora la precision de las predicciones direccionales emitidas.
        abstained = False
        if confidence_tau > 0.0 and confidence < confidence_tau:
            direction = 1  # LATERAL por defecto
            abstained = True
            logger.debug(
                f"[{ticker}] Abstención: conf={confidence:.3f} < tau={confidence_tau:.3f}"
            )
        else:
            direction = int(np.argmax(probs))  # 0, 1 o 2

        prob_bajista = float(probs[0])
        prob_lateral = float(probs[1])
        prob_alcista = float(probs[2])

        return {
            "direction":               direction,
            "direction_binary":        1 if direction == 2 else 0,  # Compatibilidad legacy
            "probability":             prob_alcista,    # Compatibilidad meta_ensemble
            "confidence":              confidence,      # Confianza real (max prob)
            "probability_alcista":     prob_alcista,
            "probability_lateral":     prob_lateral,
            "probability_bajista":     prob_bajista,
            "probability_not_alcista": prob_bajista + prob_lateral,
            "all_proba":               [prob_bajista, prob_lateral, prob_alcista],
            "abstained":               abstained,
            "confidence_tau":          confidence_tau,
            "model_id":                f"{ticker}_xgboost_v5",
            "timestamp":               datetime.now().isoformat(),
        }

    except Exception as exc:
        logger.warning("Error en predict_xgboost para %s: %s", ticker, exc)
        return {
            "direction": 1,
            "probability": 0.5,
            "confidence": 0.5,
            "all_proba": [0.33, 0.34, 0.33],
            "abstained": False,
            "error": str(exc),
        }
