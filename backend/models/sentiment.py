"""
Módulo de análisis de sentimiento para el predictor Horizon.

Utiliza FinBERT (ProsusAI/finbert) para analizar noticias financieras
obtenidas desde la API de Finnhub, generando 3 features por día:
    - sentiment_score:     media de sentimientos (-1.0 a +1.0)
    - sentiment_magnitude: media de confianza FinBERT (0.0 a 1.0)
    - news_volume:         número de artículos (sin normalizar)

Funciones principales:
    - compute_historical_sentiment(ticker, start_date, end_date) → DataFrame
    - get_daily_sentiment(ticker, days_back=7) → dict
"""

import os
import logging
from datetime import datetime, timedelta, date
from typing import Optional

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# ── Carga perezosa de FinBERT (singleton) ─────────────────────────────────────

_finbert_pipeline = None
_finbert_loaded = False


def _get_finbert():
    """
    Carga FinBERT la primera vez que se invoca (singleton).

    Usa CPU explícitamente para evitar conflictos con CUDA si está disponible.
    Devuelve None si la carga falla (ej. sin conexión, sin transformers).
    """
    global _finbert_pipeline, _finbert_loaded
    if _finbert_loaded:
        return _finbert_pipeline
    _finbert_loaded = True

    try:
        from transformers import pipeline
        import torch

        logger.info("Cargando FinBERT (ProsusAI/finbert) en CPU...")
        _finbert_pipeline = pipeline(
            "text-classification",
            model="ProsusAI/finbert",
            tokenizer="ProsusAI/finbert",
            device=torch.device("cpu"),
            top_k=None,
        )
        logger.info("FinBERT cargado correctamente.")
    except Exception as exc:
        logger.warning("No se pudo cargar FinBERT: %s. Se usarán scores neutros.", exc)
        _finbert_pipeline = None

    return _finbert_pipeline


# ── Mapeo de etiquetas FinBERT → puntuación numérica ──────────────────────────

_LABEL_TO_SCORE = {
    "positive": 1.0,
    "negative": -1.0,
    "neutral": 0.0,
}


def _analyze_headlines(headlines: list) -> tuple:
    """
    Analiza una lista de titulares con FinBERT.

    Args:
        headlines: Lista de strings con titulares de noticias.

    Returns:
        Tupla (sentiment_score, sentiment_magnitude) donde:
            - sentiment_score: media ponderada por confianza [-1.0, +1.0]
            - sentiment_magnitude: media de confianza de la predicción ganadora [0.0, 1.0]
    """
    if not headlines:
        return 0.0, 0.0

    nlp = _get_finbert()
    if nlp is None:
        return 0.0, 0.0

    try:
        # Truncar titulares a 512 caracteres para evitar errores de longitud en el tokenizador
        # (el tokenizador de FinBERT después gestiona el límite de tokens internamente)
        truncated = [h[:512] for h in headlines if isinstance(h, str) and h.strip()]
        if not truncated:
            return 0.0, 0.0

        results = nlp(truncated, truncation=True, max_length=512)

        scores = []
        magnitudes = []
        for result in results:
            # result es una lista de dicts con label + score (top_k=None devuelve los 3)
            best = max(result, key=lambda x: x["score"])
            label_score = _LABEL_TO_SCORE.get(best["label"].lower(), 0.0)
            scores.append(label_score * best["score"])
            magnitudes.append(best["score"])

        return float(np.mean(scores)), float(np.mean(magnitudes))

    except Exception as exc:
        logger.warning("Error en FinBERT durante análisis: %s", exc)
        return 0.0, 0.0


# ── Acceso a Finnhub ───────────────────────────────────────────────────────────

def _get_finnhub_client():
    """
    Devuelve un cliente finnhub inicializado con FINNHUB_API_KEY.
    Devuelve None si la clave no está disponible o el paquete no está instalado.
    """
    api_key = os.environ.get("FINNHUB_API_KEY", "").strip()
    if not api_key:
        logger.info("FINNHUB_API_KEY no configurada. Se usarán scores neutros.")
        return None

    try:
        import finnhub
        return finnhub.Client(api_key=api_key)
    except ImportError:
        logger.warning("Paquete 'finnhub-python' no instalado. Se usarán scores neutros.")
        return None
    except Exception as exc:
        logger.warning("Error inicializando cliente Finnhub: %s", exc)
        return None


def _fetch_news_finnhub(
    client,
    ticker: str,
    from_date: str,
    to_date: str,
) -> list:
    """
    Descarga noticias de Finnhub para un ticker en el rango de fechas dado.

    Args:
        client: Cliente finnhub ya inicializado.
        ticker: Símbolo del activo.
        from_date: Fecha inicio 'YYYY-MM-DD'.
        to_date: Fecha fin 'YYYY-MM-DD'.

    Returns:
        Lista de titulares (strings).
    """
    try:
        news = client.company_news(ticker, _from=from_date, to=to_date)
        return [item.get("headline", "") for item in news if item.get("headline")]
    except Exception as exc:
        logger.warning("Error descargando noticias de Finnhub (%s, %s→%s): %s",
                       ticker, from_date, to_date, exc)
        return []


# ── API pública ────────────────────────────────────────────────────────────────

def compute_historical_sentiment(
    ticker: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """
    Calcula features de sentimiento diario para el rango histórico dado.

    Dado que Finnhub free tier solo provee noticias recientes, las fechas
    sin datos se rellenan con valores neutros (0.0, 0.0, 0) para que el
    pipeline de entrenamiento funcione aunque el historial sea parcial.

    Args:
        ticker: Símbolo del activo (ej: 'KO', 'TSLA').
        start_date: Fecha inicio en formato 'YYYY-MM-DD'.
        end_date: Fecha fin en formato 'YYYY-MM-DD'.

    Returns:
        DataFrame indexado por fecha con columnas:
            - sentiment_score       [-1.0, +1.0]
            - sentiment_magnitude   [0.0, 1.0]
            - news_volume           [int ≥ 0]
    """
    idx = pd.date_range(start=start_date, end=end_date, freq="B")  # días hábiles
    neutral_df = pd.DataFrame(
        {
            "sentiment_score": 0.0,
            "sentiment_magnitude": 0.0,
            "news_volume": 0,
        },
        index=idx,
    )

    client = _get_finnhub_client()
    if client is None:
        return neutral_df

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        logger.warning("Formato de fecha inválido en compute_historical_sentiment.")
        return neutral_df

    # Limitar rango a máximo 1 año atrás para respetar límites del tier gratuito
    today = date.today()
    effective_start = max(start_dt, today - timedelta(days=365))
    if effective_start > end_dt:
        return neutral_df

    rows = {}
    current = effective_start
    while current <= end_dt:
        date_str = current.strftime("%Y-%m-%d")
        headlines = _fetch_news_finnhub(client, ticker, date_str, date_str)
        if headlines:
            score, magnitude = _analyze_headlines(headlines)
            rows[pd.Timestamp(current)] = {
                "sentiment_score": score,
                "sentiment_magnitude": magnitude,
                "news_volume": len(headlines),
            }
        current += timedelta(days=1)

    if rows:
        fetched_df = pd.DataFrame.from_dict(rows, orient="index")
        fetched_df.index.name = neutral_df.index.name
        # Actualizar solo las fechas disponibles
        neutral_df.update(fetched_df)

    return neutral_df


def get_daily_sentiment(ticker: str, days_back: int = 7) -> dict:
    """
    Obtiene el sentimiento agregado de los últimos N días para inferencia.

    Args:
        ticker: Símbolo del activo.
        days_back: Número de días hacia atrás para agregar noticias.

    Returns:
        Diccionario con:
            - sentiment_score       float [-1.0, +1.0]
            - sentiment_magnitude   float [0.0, 1.0]
            - news_volume           int
            - available             bool (False si no había API key o error)
    """
    neutral = {
        "sentiment_score": 0.0,
        "sentiment_magnitude": 0.0,
        "news_volume": 0,
        "available": False,
    }

    client = _get_finnhub_client()
    if client is None:
        return neutral

    end_dt = date.today()
    start_dt = end_dt - timedelta(days=days_back)

    headlines = _fetch_news_finnhub(
        client,
        ticker,
        start_dt.strftime("%Y-%m-%d"),
        end_dt.strftime("%Y-%m-%d"),
    )

    if not headlines:
        return neutral

    score, magnitude = _analyze_headlines(headlines)
    return {
        "sentiment_score": round(score, 6),
        "sentiment_magnitude": round(magnitude, 6),
        "news_volume": len(headlines),
        "available": True,
    }
