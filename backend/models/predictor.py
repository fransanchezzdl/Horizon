"""
Módulo de inferencia de alto nivel para el predictor Horizon.

Interfaz principal que utilizarán los endpoints de FastAPI para
obtener predicciones de tendencia a 5 días para cualquier ticker.
"""

from datetime import datetime, timezone
from typing import Dict

from .config import get_config, get_asset_type, PREDICTION_HORIZON
from .ensemble import predict_ensemble


def get_prediction(ticker: str) -> Dict:
    """
    Obtiene la predicción de tendencia a 5 días para un ticker.

    Descarga los datos más recientes, calcula features, escala con
    el scaler entrenado y ejecuta el ensemble de modelos BiGRU.

    Args:
        ticker: Símbolo del activo (ej: 'KO', 'TSLA', 'BTC-USD').

    Returns:
        Diccionario con toda la información necesaria para el frontend:
        {
            "ticker": "KO",
            "asset_type": "stable",
            "current_price": 79.34,
            "prediction": {
                "trend": "ALCISTA",
                "confidence": 0.80,
                "predicted_price": 80.15,
                "price_upper": 81.02,
                "price_lower": 79.30,
                "predicted_return_pct": 1.02,
                "horizon_days": 5
            },
            "individual_models": [
                {"model_id": 1, "predicted_return": 0.012},
                ...
            ],
            "timestamp": "2026-03-04T12:00:00Z"
        }

    En caso de error devuelve:
        {"ticker": ..., "error": <mensaje de error>}
    """
    try:
        asset_type = get_asset_type(ticker)
        ensemble_result = predict_ensemble(ticker)

        predicted_return_pct = round(ensemble_result["predicted_return"] * 100, 4)

        return {
            "ticker": ticker,
            "asset_type": asset_type,
            "current_price": round(ensemble_result["current_price"], 4),
            "prediction": {
                "trend": ensemble_result["trend"],
                "confidence": round(ensemble_result["confidence"], 4),
                "predicted_price": round(ensemble_result["predicted_price"], 4),
                "price_upper": round(ensemble_result["price_upper"], 4),
                "price_lower": round(ensemble_result["price_lower"], 4),
                "predicted_return_pct": predicted_return_pct,
                "horizon_days": PREDICTION_HORIZON,
            },
            "individual_models": ensemble_result["individual_predictions"],
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    except FileNotFoundError as exc:
        print(f"❌ Modelos no encontrados para {ticker}: {exc}")
        return {"ticker": ticker, "error": str(exc)}
    except ValueError as exc:
        print(f"❌ Datos insuficientes para {ticker}: {exc}")
        return {"ticker": ticker, "error": str(exc)}
    except Exception as exc:
        print(f"❌ Error inesperado al predecir {ticker}: {exc}")
        return {"ticker": ticker, "error": str(exc)}
