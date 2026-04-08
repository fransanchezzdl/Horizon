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
from datetime import datetime
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

    # TEMPORAL TARGET SIN LEAKAGE: Convertir retornos continuos (y) a clases ternarias
    # 0 = BAJISTA (retorno < -threshold)
    # 1 = LATERAL (retorno en [-threshold, +threshold])
    # 2 = ALCISTA (retorno > +threshold)
    # 
    # El threshold se calibra dinámicamente sobre validación para maximizar balanced accuracy
    
    # CRÍTICO: Usar los retornos CONTINUOS, no las clases ya hechas
    y_train_continuous = data.get("y_train_returns", data["y_train"].numpy() if hasattr(data["y_train"], 'numpy') else data["y_train"].cpu().numpy()).ravel()
    y_val_continuous = data.get("y_val_returns", data["y_val"].numpy() if hasattr(data["y_val"], 'numpy') else data["y_val"].cpu().numpy()).ravel()
    y_test_continuous = data.get("y_test_returns", data["y_test"].numpy() if hasattr(data["y_test"], 'numpy') else data["y_test"].cpu().numpy()).ravel()
    
    # Calibrar umbrales TEMPORALES basado en distribución de train
    # Percentil 33.33 para BAJISTA, 66.67 para ALCISTA
    down_threshold = np.percentile(y_train_continuous, 33.33)
    up_threshold = np.percentile(y_train_continuous, 66.67)
    
    def returns_to_classes(returns, down_th, up_th):
        """Convierte retornos continuos a 3 clases con umbrales."""
        classes = np.ones(len(returns), dtype=int)  # default: LATERAL (1)
        classes[returns <= down_th] = 0  # BAJISTA
        classes[returns >= up_th] = 2     # ALCISTA
        return classes
    
    y_train = returns_to_classes(y_train_continuous, down_threshold, up_threshold)
    y_val = returns_to_classes(y_val_continuous, down_threshold, up_threshold)
    y_test = returns_to_classes(y_test_continuous, down_threshold, up_threshold)
    
    # Distribuci n de clases para logging
    train_dist = np.bincount(y_train, minlength=3) / len(y_train) * 100
    val_dist = np.bincount(y_val, minlength=3) / len(y_val) * 100
    test_dist = np.bincount(y_test, minlength=3) / len(y_test) * 100
    
    logger.info(f"📊 Class distribution TRAIN: BAJISTA={train_dist[0]:.1f}% LATERAL={train_dist[1]:.1f}% ALCISTA={train_dist[2]:.1f}%")
    logger.info(f"📊 Class distribution VAL:   BAJISTA={val_dist[0]:.1f}% LATERAL={val_dist[1]:.1f}% ALCISTA={val_dist[2]:.1f}%")
    logger.info(f"📊 Class distribution TEST:  BAJISTA={test_dist[0]:.1f}% LATERAL={test_dist[1]:.1f}% ALCISTA={test_dist[2]:.1f}%")
    
    # Calcular scale_pos_weight para balancear desbalance binario
    # Comparar ALCISTA vs BAJISTA+LATERAL
    n_alcista = np.sum(y_train == 2)
    n_not_alcista = np.sum(y_train != 2)
    scale_pos_weight = n_not_alcista / max(n_alcista, 1)  # Sin multiplicador: honesto
    
    logger.info(f"🎯 scale_pos_weight={scale_pos_weight:.2f} (n_up={n_alcista}, n_down/lateral={n_not_alcista})")

    # Convertir a binario para XGBoost: 0=BAJISTA+LATERAL, 1=ALCISTA
    y_train_binary = (y_train == 2).astype(int)
    y_val_binary = (y_val == 2).astype(int)
    y_test_binary = (y_test == 2).astype(int)

    # Seleccionar configuración según tipo de activo
    from .config import XGBOOST_STABLE_CONFIG, XGBOOST_VOLATILE_CONFIG
    if asset_type == "volatile":
        cfg = XGBOOST_VOLATILE_CONFIG
        logger.info(f"🎯 Usando config VOLATILE para {ticker}")
    else:
        cfg = XGBOOST_STABLE_CONFIG
        logger.info(f"🎯 Usando config STABLE para {ticker}")
    
    model = XGBClassifier(
        n_estimators=cfg["n_estimators"],
        max_depth=cfg["max_depth"],
        learning_rate=cfg["learning_rate"],
        subsample=cfg["subsample"],
        colsample_bytree=cfg["colsample_bytree"],
        min_child_weight=cfg.get("min_child_weight", 1.0),  # finer splits
        gamma=cfg.get("gamma", 0.0),  # complexity penalty
        early_stopping_rounds=cfg["early_stopping_rounds"],
        eval_metric="logloss",
        objective="binary:logistic",
        scale_pos_weight=scale_pos_weight,  # CRÍTICO: balancea el sesgo alcista
        verbosity=0,
        random_state=seed,
    )

    model.fit(
        X_train,
        y_train_binary,
        eval_set=[(X_val, y_val_binary)],
        verbose=False,
    )

    # ── Métricas en test ───────────────────────────────────────────────────────
    y_pred_binary = model.predict(X_test)
    y_proba_full = model.predict_proba(X_test)  # shape: (n_samples, 2) - probabilidades completas
    y_prob = y_proba_full[:, 1]  # probabilidad de clase 1 (ALCISTA)
    
    # ⭐ CONFIANZA: Promedio de máximas probabilidades (predicción más confiada)
    # Para cada muestra, tomar max(P(class_0), P(class_1)) y promediar
    max_probabilities = np.max(y_proba_full, axis=1)  # array de max probs por sample
    confidence_score = float(np.mean(max_probabilities))  # promedio de confianzas
    
    # ⭐ v4 - RECALL-TARGET BASED THRESHOLD CALIBRATION (NEW)
    # En lugar de usar percentiles, busca DIRECTAMENTE el threshold que da recall ~50%
    # Esto garantiza recall consistente entre tickers, eliminando la variancia observada en v2/v3
    y_prob_val = model.predict_proba(X_val)[:, 1]
    
    TARGET_RECALL = 0.50  # Objetivo: 50% recall (40-60% acceptable)
    TOLERANCE = 0.10     # Tolerancia: ±10% alrededor del objetivo
    
    best_ba = -1
    best_down = np.percentile(y_prob_val, 25)  # fallback
    best_up = np.percentile(y_prob_val, 75)    # fallback
    best_recall_up = 0
    best_distance_to_target = float('inf')
    
    # Generar rango de thresholds a probar
    # Usar percentiles del 5% al 95% como límites de búsqueda
    min_prob = np.percentile(y_prob_val, 5)
    max_prob = np.percentile(y_prob_val, 95)
    
    # Crear grid fino de thresholds para buscar
    threshold_candidates = np.linspace(min_prob, max_prob, 60)
    
    # Para cada threshold, buscar la mejor combinación DOWN + UP
    for up_threshold in threshold_candidates:
        # DOWN threshold: más restrictivo, usar percentiles bajos
        for down_threshold in np.linspace(min_prob, min_prob * 0.9, 15):
            if down_threshold >= up_threshold - 0.02:  # Asegurar gap de al menos 0.02
                continue
            
            # Predecir ternario
            y_pred_candidate = np.ones(len(y_prob_val), dtype=int)
            y_pred_candidate[y_prob_val >= up_threshold] = 2      # ALCISTA
            y_pred_candidate[y_prob_val <= down_threshold] = 0    # BAJISTA
            
            # Calcular métricas
            ba_candidate = balanced_accuracy_score(y_val, y_pred_candidate)
            
            # Matriz de confusión
            cm = confusion_matrix(y_val, y_pred_candidate, labels=[0, 1, 2])
            tp_candidate = cm[2, 2]
            fp_candidate = np.sum(cm[:, 2]) - tp_candidate
            fn_candidate = np.sum(cm[2, :]) - tp_candidate
            recall_candidate = tp_candidate / (tp_candidate + fn_candidate) if (tp_candidate + fn_candidate) > 0 else 0
            
            # CRITERIO DE SELECCIÓN: 
            # 1. Priorizar recall cercano al target (40-60%)
            # 2. Entre candidatos con recall similar, elegir mayor BA
            distance_to_target = abs(recall_candidate - TARGET_RECALL)
            
            # Si recall está en rango aceptable, usar esta métrica
            if distance_to_target <= TOLERANCE:
                if distance_to_target < best_distance_to_target or \
                   (distance_to_target == best_distance_to_target and ba_candidate > best_ba):
                    best_ba = ba_candidate
                    best_down = down_threshold
                    best_up = up_threshold
                    best_recall_up = recall_candidate
                    best_distance_to_target = distance_to_target
    
    prob_25 = best_down
    prob_75 = best_up
    
    # DEBUG: Log con nueva versión
    import sys
    percentile_down_pct = np.searchsorted(np.sort(y_prob_val), best_down) / len(y_prob_val) * 100
    percentile_up_pct = np.searchsorted(np.sort(y_prob_val), best_up) / len(y_prob_val) * 100
    print(f"  v4 Recall-Target: DOWN={best_down:.4f} ({percentile_down_pct:.1f}%ile), UP={best_up:.4f} ({percentile_up_pct:.1f}%ile), BA={best_ba:.4f}, Recall={best_recall_up:.3f} | Target={TARGET_RECALL:.0%}", file=sys.stderr)
    
    # Convertir probabilidades a 3 clases usando BALANCED SMART THRESHOLDS
    # Evita extremos, prefiere balance precision/recall
    # - Si prob <= prob_down: BAJISTA (likely DOWN)
    # - Si prob >= prob_up: ALCISTA (likely UP)
    # - Si prob_down < prob < prob_up: LATERAL (zona neutral)
    
    y_pred_ternary = np.ones(len(y_prob), dtype=int)  # default: LATERAL
    y_pred_ternary[y_prob >= prob_75] = 2  # ALCISTA
    y_pred_ternary[y_prob <= prob_25] = 0  # BAJISTA

    # Métricas binarias (compatibilidad)
    dir_acc = float(np.mean(y_pred_binary == y_test_binary))
    
    # Métricas robustas para problema desbalanceado (3-class)
    balanced_acc = float(balanced_accuracy_score(y_test, y_pred_ternary))
    macro_f1 = float(f1_score(y_test, y_pred_ternary, average='macro', zero_division=0))
    
    # Matriz de confusión (3-class para diagnóstico del ALCISTA)
    cm_ternary = confusion_matrix(y_test, y_pred_ternary, labels=[0, 1, 2])
    
    # Extraer métricas del ALCISTA (clase 2) para compatibilidad
    # TP: True positives para ALCISTA  (diag[2, 2])
    # FP: False positives para ALCISTA (sum de col 2 minus TP)
    # FN: False negatives para ALCISTA (sum de row 2 minus TP)
    # TN: Samples no-Alcista predichos como no-Alcista
    tp = int(cm_ternary[2, 2])
    fn = int(np.sum(cm_ternary[2, :]) - tp)  # Alcistas predichos como no-Alcista
    fp = int(np.sum(cm_ternary[:, 2]) - tp)  # No-Alcistas predichos como Alcista
    tn = int(np.sum(cm_ternary) - tp - fp - fn)
    
    cm_dict = {
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
    }

    # Precision y recall para clase 2 (ALCISTA)
    tp = cm_dict["tp"]
    fp = cm_dict["fp"]
    fn = cm_dict["fn"]

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

    # ── Guardar modelo y umbrales ─────────────────────────────────────────────
    os.makedirs(SAVED_MODELS_DIR, exist_ok=True)
    model_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    logger.info("XGBoost guardado en %s", model_path)
    
    # Guardar umbrales calibrados para inferencia posterior
    thresholds = {
        "down_threshold": float(down_threshold),  # Por compatibilidad (return value)
        "up_threshold": float(up_threshold),      # Por compatibilidad (return value)
        "prob_25": float(prob_25),                # NOVO: 25 percentil de probabilidades
        "prob_75": float(prob_75),                # NOVO: 75 percentil de probabilidades
        "ticker": ticker,
        "timestamp": datetime.now().isoformat(),
        "scale_pos_weight": float(scale_pos_weight),
    }
    thresholds_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost_thresholds.pkl")
    with open(thresholds_path, "wb") as f:
        pickle.dump(thresholds, f)
    logger.info(f"Thresholds saved: down={down_threshold:.4f}, up={up_threshold:.4f}, prob_25={prob_25:.4f}, prob_75={prob_75:.4f}")

    # Resumen de métricas
    print(f"\n🌳 XGBoost {ticker} VALIDATION RESULTS:")
    print(f"   Directional Accuracy: {dir_acc:.2%}")
    print(f"   Balanced Accuracy:    {balanced_acc:.2%} (optimization metric)")
    print(f"   Macro F1 Score:       {macro_f1:.2%}")
    print(f"   Precision (ALCISTA):  {precision_up:.2%}")
    print(f"   Recall (ALCISTA):     {recall_up:.2%}")
    print(f"   ✨ Confidence Score:  {confidence_score:.2%} (for confianza_bygru) ✨")
    print(f"   Confusion Matrix (binary): TN={cm_dict['tn']} FP={cm_dict['fp']} FN={cm_dict['fn']} TP={cm_dict['tp']}")
    print(f"   Thresholds: DOWN≤{down_threshold:.4f} | LATERAL | UP≥{up_threshold:.4f}")
    print(f"   Scale Pos Weight:     {scale_pos_weight:.2f}")

    return {
        "xgb_directional_accuracy": dir_acc,
        "xgb_balanced_accuracy": balanced_acc,
        "xgb_macro_f1": macro_f1,
        "xgb_precision_up": precision_up,
        "xgb_recall_up": recall_up,
        "xgb_confidence_score": confidence_score,  # ⭐ Confianza de probabilidades máximas
        "xgb_confusion_matrix": cm_dict,
        "xgb_class_distribution": {
            "train": {"BAJISTA": train_dist[0], "LATERAL": train_dist[1], "ALCISTA": train_dist[2]},
            "val": {"BAJISTA": val_dist[0], "LATERAL": val_dist[1], "ALCISTA": val_dist[2]},
            "test": {"BAJISTA": test_dist[0], "LATERAL": test_dist[1], "ALCISTA": test_dist[2]},
        },
        "xgb_down_threshold": float(down_threshold),
        "xgb_up_threshold": float(up_threshold),
        "xgb_scale_pos_weight": float(scale_pos_weight),
        "feature_importance": feature_importance,
    }


def predict_xgboost(ticker: str, features: np.ndarray) -> Dict:
    """
    Realiza una predicción de dirección con el modelo XGBoost guardado.
    
    MEJORAS:
    - Usa umbrales calibrados (dual threshold) para 3 clases: BAJISTA/LATERAL/ALCISTA
    - Persiste probabilidades para auditoría
    - Trazabilidad completa de por qué se predice cada clase

    Args:
        ticker:   Símbolo del activo.
        features: Array 1D o 2D con las features del ÚLTIMO timestep.
                  Forma esperada: [n_features] o [1, n_features].

    Returns:
        Diccionario con:
            - direction:   0 (bajista), 1 (lateral), 2 (alcista)
            - probability: probabilidad cruda [0.0, 1.0]
            - down_threshold: umbral para BAJISTA (usado en decisión)
            - up_threshold: umbral para ALCISTA (usado en decisión)
            - model_id: identificador del modelo
            - timestamp: cuándo se hizo la predicción

    En caso de error devuelve direction=1 (LATERAL), probability=0.5 (neutral).
    """
    model_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost.pkl")
    thresholds_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost_thresholds.pkl")
    
    if not os.path.exists(model_path):
        logger.warning("Modelo XGBoost no encontrado para %s: %s", ticker, model_path)
        return {
            "direction": 1,  # LATERAL por defecto
            "probability": 0.5,
            "error": "Model not found"
        }

    try:
        # Cargar modelo
        with open(model_path, "rb") as f:
            model = pickle.load(f)
        
        # Cargar umbrales percentile calibrados
        thresholds = {}
        if os.path.exists(thresholds_path):
            try:
                with open(thresholds_path, "rb") as f:
                    thresholds = pickle.load(f)
            except Exception as e:
                logger.debug("Could not load thresholds: %s", e)
        
        prob_25 = thresholds.get("prob_25", 0.25)
        prob_75 = thresholds.get("prob_75", 0.35)
        
        # Fixed probability thresholds for 3-class prediction
        # (0.35 = bajista, 0.65 = alcista, rest = lateral)
        
        arr = np.array(features)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)

        # Predicción binaria
        direction_binary = int(model.predict(arr)[0])
        
        # Probabilidad de clase ALCISTA
        probs = model.predict_proba(arr)[0]
        probability = float(probs[1]) if len(probs) > 1 else 0.5
        
        # Convertir a 3 clases usando PERCENTILES calibrados
        # - Si prob >= 75%ile: ALCISTA (top tercio: likely UP)
        # - Si prob <= 25%ile: BAJISTA (bottom tercio: likely DOWN)
        # - Si 25%ile < prob < 75%ile: LATERAL (zona neutral)
        
        if probability >= prob_75:
            direction_ternary = 2  # ALCISTA
            confidence_level = "high"
        elif probability <= prob_25:
            direction_ternary = 0  # BAJISTA
            confidence_level = "high"
        else:
            direction_ternary = 1  # LATERAL (zona de incertidumbre)
            confidence_level = "low"
        
        return {
            "direction": direction_ternary,
            "direction_binary": direction_binary,  # Para compatibilidad
            "probability": probability,
            "probability_not_alcista": float(probs[0]) if len(probs) > 1 else 0.5,
            "confidence_level": confidence_level,  # Basado en distancia del 0.5
            "model_id": f"{ticker}_xgboost",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as exc:
        logger.warning("Error en predict_xgboost para %s: %s", ticker, exc)
        return {
            "direction": 1,  # LATERAL
            "probability": 0.5,
            "error": str(exc)
        }
