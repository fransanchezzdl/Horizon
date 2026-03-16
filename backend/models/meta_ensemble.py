"""
Meta-ensemble para combinar predicciones de BiGRU y XGBoost.

El meta-ensemble combina las fortalezas de ambos modelos:
- BiGRU: Captura patrones temporales complejos en series de tiempo
- XGBoost: Robusto para clasificación tabular con feature importance

Funciones principales:
    - sigmoid_transform(return, scale) → probabilidad
    - combine_predictions(bigru_return, xgb_prob, weights) → score final
    - classify_trend(score, delta) → ALCISTA/BAJISTA/LATERAL
"""

import math
from typing import Dict, Tuple

from .config import (
    META_ENSEMBLE_WEIGHTS,
    META_ENSEMBLE_SIGMOID_SCALE,
    META_ENSEMBLE_TREND_DELTA,
)


def sigmoid_transform(log_return: float, scale: float = META_ENSEMBLE_SIGMOID_SCALE) -> float:
    """
    Convierte un retorno logarítmico en probabilidad usando sigmoid escalado.

    La función sigmoid mapea retornos a probabilidades en el rango [0, 1]:
        prob = 1 / (1 + exp(-return * scale))

    Args:
        log_return: Retorno logarítmico predicho por BiGRU.
        scale: Factor de escala para ajustar sensibilidad (default: 50.0).
               Un valor mayor hace que pequeños cambios en el retorno
               produzcan cambios más grandes en la probabilidad.

    Returns:
        Probabilidad en rango [0.0, 1.0]:
            - retorno > 0 → prob > 0.5 (alcista)
            - retorno < 0 → prob < 0.5 (bajista)
            - retorno = 0 → prob = 0.5 (neutral)

    Examples:
        >>> sigmoid_transform(0.02, 50.0)  # +2% retorno
        0.7310585786300049  # ~73% probabilidad alcista
        
        >>> sigmoid_transform(-0.02, 50.0)  # -2% retorno
        0.2689414213699951  # ~27% probabilidad alcista (73% bajista)
        
        >>> sigmoid_transform(0.0, 50.0)  # sin cambio
        0.5  # 50% probabilidad (neutral)
    """
    try:
        return 1.0 / (1.0 + math.exp(-log_return * scale))
    except OverflowError:
        # Si el exponente es muy grande, retornar límites
        return 0.0 if log_return < 0 else 1.0


def combine_predictions(
    bigru_return: float,
    xgb_probability: float,
    weights: Dict[str, float] = None,
) -> Tuple[float, float]:
    """
    Combina predicciones de BiGRU y XGBoost en un score final ponderado.

    Args:
        bigru_return: Retorno logarítmico predicho por el ensemble BiGRU.
        xgb_probability: Probabilidad de subida predicha por XGBoost [0.0, 1.0].
        weights: Diccionario con pesos {"bigru": float, "xgboost": float}.
                 Si None, usa META_ENSEMBLE_WEIGHTS de config.

    Returns:
        Tupla (final_score, bigru_prob):
            - final_score: Score combinado en rango [0.0, 1.0]
            - bigru_prob: Probabilidad BiGRU transformada (para debugging)

    Raises:
        ValueError: Si los pesos no suman 1.0 (con tolerancia de 1e-6).

    Examples:
        >>> combine_predictions(0.02, 0.65, {"bigru": 0.6, "xgboost": 0.4})
        (0.6986351471380029, 0.7310585786300049)
        # BiGRU predice +2% (73% prob), XGBoost 65% prob
        # Score final: 0.6 * 0.73 + 0.4 * 0.65 = 0.698
    """
    if weights is None:
        weights = META_ENSEMBLE_WEIGHTS

    w_bigru = weights["bigru"]
    w_xgb = weights["xgboost"]

    # Validar que los pesos sumen 1.0
    weight_sum = w_bigru + w_xgb
    if abs(weight_sum - 1.0) > 1e-6:
        raise ValueError(
            f"Los pesos del meta-ensemble deben sumar 1.0, "
            f"pero suman {weight_sum:.6f}. "
            f"Pesos actuales: bigru={w_bigru}, xgboost={w_xgb}"
        )

    # Convertir retorno BiGRU a probabilidad
    bigru_prob = sigmoid_transform(bigru_return)

    # Combinar con pesos configurables
    final_score = w_bigru * bigru_prob + w_xgb * xgb_probability

    return final_score, bigru_prob


def classify_trend(
    score: float,
    delta: float = META_ENSEMBLE_TREND_DELTA,
) -> str:
    """
    Clasifica la tendencia basándose en el score del meta-ensemble.

    La zona neutral permite evitar señales falsas en mercados laterales:
        - score > 0.5 + delta → ALCISTA (alta confianza de subida)
        - score < 0.5 - delta → BAJISTA (alta confianza de bajada)
        - score ∈ [0.5 - delta, 0.5 + delta] → LATERAL (sin tendencia clara)

    Args:
        score: Score del meta-ensemble en rango [0.0, 1.0].
        delta: Semi-anchura de la zona neutral (default: 0.05).
               Un delta mayor hace que más predicciones sean LATERAL.

    Returns:
        Tendencia: "ALCISTA", "BAJISTA" o "LATERAL".

    Examples:
        >>> classify_trend(0.65, 0.05)  # score > 0.55
        'ALCISTA'
        
        >>> classify_trend(0.35, 0.05)  # score < 0.45
        'BAJISTA'
        
        >>> classify_trend(0.52, 0.05)  # score en [0.45, 0.55]
        'LATERAL'
        
        >>> classify_trend(0.52, 0.0)  # sin zona neutral
        'ALCISTA'  # cualquier score > 0.5 es alcista
    """
    upper_threshold = 0.5 + delta
    lower_threshold = 0.5 - delta

    if score > upper_threshold:
        return "ALCISTA"
    elif score < lower_threshold:
        return "BAJISTA"
    else:
        return "LATERAL"


def get_meta_ensemble_prediction(
    bigru_return: float,
    xgb_probability: float,
    weights: Dict[str, float] = None,
    delta: float = META_ENSEMBLE_TREND_DELTA,
) -> Dict[str, float]:
    """
    Ejecuta el pipeline completo del meta-ensemble.

    Combina predicciones de BiGRU y XGBoost, calcula el score final
    y clasifica la tendencia con zona neutral configurable.

    Args:
        bigru_return: Retorno logarítmico del ensemble BiGRU.
        xgb_probability: Probabilidad de subida de XGBoost [0.0, 1.0].
        weights: Pesos del meta-ensemble (opcional).
        delta: Semi-anchura de zona neutral (opcional).

    Returns:
        Diccionario con:
            - meta_trend: "ALCISTA", "BAJISTA" o "LATERAL"
            - meta_score: Score final [0.0, 1.0]
            - bigru_prob: Probabilidad BiGRU transformada
            - xgb_prob: Probabilidad XGBoost (pasada directamente)
            - weights_used: Pesos aplicados

    Examples:
        >>> result = get_meta_ensemble_prediction(0.02, 0.65)
        >>> result["meta_trend"]
        'ALCISTA'
        >>> result["meta_score"]
        0.6986351471380029
    """
    if weights is None:
        weights = META_ENSEMBLE_WEIGHTS

    final_score, bigru_prob = combine_predictions(
        bigru_return, xgb_probability, weights
    )
    meta_trend = classify_trend(final_score, delta)

    return {
        "meta_trend": meta_trend,
        "meta_score": final_score,
        "bigru_prob": bigru_prob,
        "xgb_prob": xgb_probability,
        "weights_used": weights,
    }
