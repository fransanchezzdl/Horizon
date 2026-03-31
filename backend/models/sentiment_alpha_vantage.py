"""
Módulo de análisis de sentimiento financiero usando Alpha Vantage News Sentiment API.

Integra:
- API de Alpha Vantage (noticias + sentimiento)
- Cache en Supabase tabla `sentimientos`
- Feature engineering para features de sentimiento
"""

import os
import json
import requests
import pandas as pd
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

# Importar Supabase si está disponible
try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


# API configuration
ALPHAVANTAGE_API_URL = "https://www.alphavantage.co/query"
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "demo")  # Use .env for production

# Supabase config (optional)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


class AlphaVantageSentiment:
    """Client para Alpha Vantage News Sentiment API."""
    
    @staticmethod
    def fetch_news_sentiment(
        ticker: str,
        limit: int = 100,
        time_period: str = "1day",  # 1day, 5day, 7day, 30day, 60day, 90day, 180day
    ) -> Dict:
        """
        Obtiene noticias y sentimiento para un ticker desde Alpha Vantage.
        
        Args:
            ticker: Símbolo del activo (ej: 'KO', 'TSLA')
            limit: Número máximo de artículos a retornar (max 1000)
            time_period: Período de tiempo para las noticias
        
        Returns:
            Dict con estructura:
            {
                'ticker': str,
                'sentiment_score': float [-1.0, 1.0],
                'sentiment_magnitude': float [0.0, 1.0],
                'news_count': int,
                'articles': list[{
                    'title': str,
                    'url': str,
                    'summary': str,
                    'ticker_sentiment_score': float,
                    'ticker_sentiment_label': str (Positive/Negative/Neutral),
                    'publish_utc': str,
                }],
                'timestamp': str (ISO format),
            }
        
        Raises:
            ValueError: Si la API retorna error
        """
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": ticker,
            "apikey": ALPHAVANTAGE_API_KEY,
            "limit": min(limit, 1000),  # Max 1000 per API
            "time_period": time_period,
        }
        
        print(f"[*] Consultando Alpha Vantage para {ticker}...")
        response = requests.get(ALPHAVANTAGE_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Validar respuesta
        if "Error Message" in data:
            raise ValueError(f"Alpha Vantage Error: {data['Error Message']}")
        
        if "Note" in data:
            raise ValueError(f"Alpha Vantage Rate Limit: {data['Note']}")
        
        # Procesar datos
        feed = data.get("feed", [])
        
        if not feed:
            print(f"[!] No hay noticias para {ticker}")
            return {
                "ticker": ticker,
                "sentiment_score": 0.0,
                "sentiment_magnitude": 0.0,
                "news_count": 0,
                "articles": [],
                "timestamp": datetime.utcnow().isoformat(),
            }
        
        # Calcular sentimiento agregado
        scores = []
        magnitudes = []
        
        for article in feed:
            # Obtener sentimiento para este ticker específicamente
            ticker_sentiments = article.get("ticker_sentiment", [])
            for ts in ticker_sentiments:
                if ts.get("ticker") == ticker:
                    score = float(ts.get("ticker_sentiment_score", 0.0))
                    magnitude = float(ts.get("ticker_sentiment_magnitude", 0.0))
                    scores.append(score)
                    magnitudes.append(magnitude)
                    break
        
        # Promedio ponderado por magnitud
        if scores:
            weighted_score = np.average(scores, weights=magnitudes if magnitudes else None)
            avg_magnitude = np.mean(magnitudes)
        else:
            weighted_score = 0.0
            avg_magnitude = 0.0
        
        print(f"[OK] Alpha Vantage: sentiment_score={weighted_score:.4f}, n_articles={len(feed)}")
        
        return {
            "ticker": ticker,
            "sentiment_score": float(weighted_score),
            "sentiment_magnitude": float(avg_magnitude),
            "news_count": len(feed),
            "articles": feed[:10],  # Guardar solo primeros 10 para no saturar BD
            "timestamp": datetime.utcnow().isoformat(),
        }


class SentimentCache:
    """Cache de sentimientos en Supabase."""
    
    def __init__(self):
        self.available = SUPABASE_AVAILABLE and SUPABASE_URL and SUPABASE_KEY
        if self.available:
            try:
                self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
            except Exception as e:
                print(f"[!] No se pudo conectar a Supabase: {e}")
                self.available = False
    
    def get_cached_sentiment(
        self,
        ticker: str,
        max_age_hours: int = 24,
    ) -> Optional[Dict]:
        """
        Obtiene sentimiento del cache si está fresco.
        
        Args:
            ticker: Símbolo del activo
            max_age_hours: Edad máxima permitida en horas
        
        Returns:
            Dict con sentimientos o None si no hay en cache
        """
        if not self.available:
            return None
        
        try:
            cutoff_time = (datetime.utcnow() - timedelta(hours=max_age_hours)).isoformat()
            
            response = self.client.table("sentimientos").select("*").eq("ticker", ticker).gt(
                "created_at", cutoff_time
            ).order("created_at", desc=True).limit(1).execute()
            
            if response.data:
                return response.data[0]
            return None
        
        except Exception as e:
            print(f"[!] Error al consultar cache: {e}")
            return None
    
    def save_sentiment(self, sentiment_data: Dict) -> bool:
        """
        Guarda sentimiento en Supabase.
        
        Args:
            sentiment_data: Dict con datos de sentimiento
        
        Returns:
            True si se guardó exitosamente
        """
        if not self.available:
            return False
        
        try:
            record = {
                "ticker": sentiment_data["ticker"],
                "sentiment_score": sentiment_data["sentiment_score"],
                "sentiment_magnitude": sentiment_data["sentiment_magnitude"],
                "news_count": sentiment_data["news_count"],
                "articles_json": json.dumps(sentiment_data.get("articles", [])),
                "fetched_at": sentiment_data["timestamp"],
            }
            
            self.client.table("sentimientos").insert(record).execute()
            print(f"[OK] Sentimiento guardado para {sentiment_data['ticker']}")
            return True
        
        except Exception as e:
            print(f"[!] Error al guardar en Supabase: {e}")
            return False


def get_sentiment_features(
    ticker: str,
    use_cache: bool = True,
    cache_max_age_hours: int = 24,
) -> Tuple[float, float, int]:
    """
    Obtiene features de sentimiento para un ticker.
    
    Intenta obtener del cache primero, si no, consulta Alpha Vantage.
    
    Args:
        ticker: Símbolo del activo
        use_cache: Si True, utiliza cache de Supabase
        cache_max_age_hours: Edad máxima del cache
    
    Returns:
        Tupla (sentiment_score, sentiment_magnitude, news_volume)
    
    Ejemplo:
        >>> sentiment_score, magnitude, n_news = get_sentiment_features("AAPL")
        >>> print(f"Apple sentiment: {sentiment_score:.3f} (magnitude: {magnitude:.3f})")
    """
    cache = SentimentCache()
    
    # Intentar cache
    if use_cache:
        cached = cache.get_cached_sentiment(ticker, max_age_hours=cache_max_age_hours)
        if cached:
            print(f"[*] Usando cache para {ticker}")
            return (
                float(cached.get("sentiment_score", 0.0)),
                float(cached.get("sentiment_magnitude", 0.0)),
                int(cached.get("news_count", 0)),
            )
    
    # Consultar API
    try:
        sentiment_data = AlphaVantageSentiment.fetch_news_sentiment(ticker)
        
        # Guardar en cache
        if use_cache:
            cache.save_sentiment(sentiment_data)
        
        return (
            sentiment_data["sentiment_score"],
            sentiment_data["sentiment_magnitude"],
            sentiment_data["news_count"],
        )
    
    except Exception as e:
        print(f"[!] Error obteniendo sentimiento: {e}")
        # Retornar valores neutros en caso de error
        return 0.0, 0.0, 0


def create_sentiment_features_df(
    ticker: str,
    dates: pd.DatetimeIndex,
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Crea un DataFrame con features de sentimiento para cada fecha.
    
    Como el sentimiento es más lento en cambiar que precios, usamos 
    el mismo valor para varias fechas (actualización diaria o más lenta).
    
    Args:
        ticker: Símbolo del activo
        dates: Índice de fechas (de features dataset)
        use_cache: Si True, utiliza cache
    
    Returns:
        DataFrame con columns: sentiment_score, sentiment_magnitude, news_volume
    """
    # Obtener sentimiento actual
    score, magnitude, n_news = get_sentiment_features(ticker, use_cache=use_cache)
    
    # Crear DataFrame con mismo valor para todas las fechas
    # (En una solución más avanzada, podrías actualizar por día)
    df = pd.DataFrame(
        {
            "sentiment_score": score,
            "sentiment_magnitude": magnitude,
            "news_volume": n_news,
        },
        index=dates,
    )
    
    print(f"[OK] Features de sentimiento creadas: {len(df)} fechas")
    return df


if __name__ == "__main__":
    # Test rápido
    print("[*] Testeando Alpha Vantage Sentiment...")
    
    try:
        sentiment_score, magnitude, n_news = get_sentiment_features("AAPL", use_cache=False)
        print(f"[OK] Apple: score={sentiment_score:.3f}, magnitude={magnitude:.3f}, news={n_news}")
    except Exception as e:
        print(f"[ERROR] {e}")
