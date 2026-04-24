"""
Módulo de análisis de sentimiento para el predictor Horizon.

Usa DistilRoBERTa fine-tuned en noticias financieras
(mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis)
con noticias obtenidas desde Alpha Vantage News Sentiment API.

Ventajas sobre FinBERT + Finnhub:
    - DistilRoBERTa: 82M params, ~50ms/texto en CPU, fine-tuned en financial news
    - Alpha Vantage: historial de noticias más largo, sin límite diario agresivo
    - Sin dependencia de Finnhub (que tiene límite de 60 req/min en free tier)

Genera 3 features por día:
    - sentiment_score:     media ponderada por confianza [-1.0, +1.0]
    - sentiment_magnitude: media de confianza del modelo [0.0, 1.0]
    - news_volume:         número de artículos procesados

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

# ── Singleton DistilRoBERTa ────────────────────────────────────────────────────

_distilroberta_pipeline = None
_distilroberta_loaded = False

MODEL_NAME = "mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis"

# Mapeo de etiquetas del modelo → puntuación numérica
_LABEL_TO_SCORE = {
    "positive": 1.0,
    "negative": -1.0,
    "neutral": 0.0,
}


def _get_model():
    """
    Carga DistilRoBERTa la primera vez (singleton, lazy loading).
    Corre en CPU. Devuelve None si falla la carga.
    """
    global _distilroberta_pipeline, _distilroberta_loaded
    if _distilroberta_loaded:
        return _distilroberta_pipeline
    _distilroberta_loaded = True

    try:
        from transformers import pipeline
        import torch

        logger.info("Cargando DistilRoBERTa financial sentiment en CPU...")
        _distilroberta_pipeline = pipeline(
            "text-classification",
            model=MODEL_NAME,
            tokenizer=MODEL_NAME,
            device=torch.device("cpu"),
            top_k=None,
        )
        logger.info("DistilRoBERTa cargado correctamente.")
    except Exception as exc:
        logger.warning("No se pudo cargar DistilRoBERTa: %s. Usando scores neutros.", exc)
        _distilroberta_pipeline = None

    return _distilroberta_pipeline


# ── Análisis de titulares ──────────────────────────────────────────────────────

def _analyze_headlines(headlines: list) -> tuple:
    """
    Analiza una lista de titulares con DistilRoBERTa.

    Args:
        headlines: Lista de strings con titulares de noticias.

    Returns:
        Tupla (sentiment_score, sentiment_magnitude):
            - sentiment_score:     media ponderada por confianza [-1.0, +1.0]
            - sentiment_magnitude: media de confianza [0.0, 1.0]
    """
    if not headlines:
        return 0.0, 0.0

    nlp = _get_model()
    if nlp is None:
        return 0.0, 0.0

    try:
        truncated = [h[:512] for h in headlines if isinstance(h, str) and h.strip()]
        if not truncated:
            return 0.0, 0.0

        results = nlp(truncated, truncation=True, max_length=512)

        scores = []
        magnitudes = []
        for result in results:
            # top_k=None devuelve lista de {label, score} para todas las clases
            best = max(result, key=lambda x: x["score"])
            label_score = _LABEL_TO_SCORE.get(best["label"].lower(), 0.0)
            scores.append(label_score * best["score"])
            magnitudes.append(best["score"])

        return float(np.mean(scores)), float(np.mean(magnitudes))

    except Exception as exc:
        logger.warning("Error en DistilRoBERTa durante análisis: %s", exc)
        return 0.0, 0.0


# ── Alpha Vantage News ─────────────────────────────────────────────────────────

def _fetch_news_alpha_vantage(
    ticker: str,
    from_date: str,
    to_date: str,
    limit: int = 50,
) -> list:
    """
    Descarga noticias de Alpha Vantage News Sentiment API.

    Endpoint: NEWS_SENTIMENT
    Documentación: https://www.alphavantage.co/documentation/#news-sentiment

    Args:
        ticker:    Símbolo del activo (ej: 'KO', 'TSLA').
        from_date: Fecha inicio 'YYYY-MM-DD'.
        to_date:   Fecha fin 'YYYY-MM-DD'.
        limit:     Máximo de artículos a descargar (max 1000 en premium, 50 en free).

    Returns:
        Lista de titulares (strings).
    """
    api_key = os.environ.get("ALPHA_VANTAGE_API_KEY", "").strip()
    if not api_key:
        logger.info("ALPHA_VANTAGE_API_KEY no configurada. Usando scores neutros.")
        return []

    try:
        import requests

        # Alpha Vantage espera formato YYYYMMDDTHHMM
        time_from = from_date.replace("-", "") + "T0000"
        time_to   = to_date.replace("-", "") + "T2359"

        url = "https://www.alphavantage.co/query"
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": ticker,
            "time_from": time_from,
            "time_to": time_to,
            "limit": limit,
            "apikey": api_key,
        }

        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if "feed" not in data:
            logger.debug("Alpha Vantage no devolvió 'feed' para %s (%s→%s): %s",
                         ticker, from_date, to_date, list(data.keys()))
            return []

        headlines = []
        for article in data["feed"]:
            title = article.get("title", "")
            summary = article.get("summary", "")
            # Combinar título + resumen para más contexto semántico
            text = f"{title}. {summary}".strip(". ")
            if text:
                headlines.append(text)

        return headlines

    except Exception as exc:
        logger.warning("Error descargando noticias de Alpha Vantage (%s, %s→%s): %s",
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

    Agrupa las noticias por semana (no por día) para maximizar el número
    de artículos por ventana y reducir el ruido. Luego hace forward-fill
    para propagar el sentimiento semanal a los días hábiles.

    Args:
        ticker:     Símbolo del activo.
        start_date: Fecha inicio 'YYYY-MM-DD'.
        end_date:   Fecha fin 'YYYY-MM-DD'.

    Returns:
        DataFrame indexado por fecha (días hábiles) con columnas:
            - sentiment_score       [-1.0, +1.0]
            - sentiment_magnitude   [0.0, 1.0]
            - news_volume           [int ≥ 0]
    """
    idx = pd.date_range(start=start_date, end=end_date, freq="B")
    neutral_df = pd.DataFrame(
        {"sentiment_score": 0.0, "sentiment_magnitude": 0.0, "news_volume": 0},
        index=idx,
    )

    api_key = os.environ.get("ALPHA_VANTAGE_API_KEY", "").strip()
    if not api_key:
        return neutral_df

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt   = datetime.strptime(end_date,   "%Y-%m-%d").date()
    except ValueError:
        logger.warning("Formato de fecha inválido en compute_historical_sentiment.")
        return neutral_df

    # Alpha Vantage free tier: historial limitado a ~1 año
    today = date.today()
    effective_start = max(start_dt, today - timedelta(days=365))
    if effective_start > end_dt:
        return neutral_df

    rows = {}

    # Iterar por semanas para reducir llamadas a la API
    current = effective_start
    while current <= end_dt:
        week_end = min(current + timedelta(days=6), end_dt)
        from_str = current.strftime("%Y-%m-%d")
        to_str   = week_end.strftime("%Y-%m-%d")

        headlines = _fetch_news_alpha_vantage(ticker, from_str, to_str, limit=50)
        if headlines:
            score, magnitude = _analyze_headlines(headlines)
            # Asignar el sentimiento semanal al lunes de esa semana
            rows[pd.Timestamp(current)] = {
                "sentiment_score": score,
                "sentiment_magnitude": magnitude,
                "news_volume": len(headlines),
            }

        current = week_end + timedelta(days=1)

    if rows:
        fetched_df = pd.DataFrame.from_dict(rows, orient="index")
        combined_df = pd.DataFrame(index=idx)
        combined_df = combined_df.join(fetched_df, how="left")
        # Forward-fill hasta 7 días (propaga sentimiento semanal a días hábiles)
        combined_df = combined_df.ffill(limit=7)
        combined_df = combined_df.fillna(0.0)
        combined_df["news_volume"] = combined_df["news_volume"].fillna(0).astype(int)
        return combined_df

    return neutral_df


def get_daily_sentiment(ticker: str, days_back: int = 7) -> dict:
    """
    Obtiene el sentimiento agregado de los últimos N días para inferencia.

    Args:
        ticker:    Símbolo del activo.
        days_back: Número de días hacia atrás para agregar noticias.

    Returns:
        Diccionario con:
            - sentiment_score       float [-1.0, +1.0]
            - sentiment_magnitude   float [0.0, 1.0]
            - news_volume           int
            - available             bool
    """
    neutral = {
        "sentiment_score": 0.0,
        "sentiment_magnitude": 0.0,
        "news_volume": 0,
        "available": False,
    }

    end_dt   = date.today()
    start_dt = end_dt - timedelta(days=days_back)

    headlines = _fetch_news_alpha_vantage(
        ticker,
        start_dt.strftime("%Y-%m-%d"),
        end_dt.strftime("%Y-%m-%d"),
        limit=50,
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
