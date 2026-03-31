"""
Servicio para obtener noticias de activos financieros.

Utiliza NewsAPI para obtener noticias recientes sobre tickers.
Respaldo: Puede usar fuentes RSS si NewsAPI no está disponible.
"""

import requests
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# NewsAPI key (https://newsapi.org/)
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "not_configured")
NEWSAPI_ENDPOINT = "https://newsapi.org/v2/everything"


class NewsService:
    """Servicio para obtener y procesar noticias de activos."""
    
    @staticmethod
    def get_news_for_ticker(
        ticker: str,
        days_back: int = 7,
        max_articles: int = 30,
        sort_by: str = "popularity"
    ) -> List[Dict]:
        """
        Obtiene noticias recientes para un ticker usando /top-headlines (optimizado).
        
        Args:
            ticker: Símbolo del ticker (AAPL, MSFT, etc.)
            days_back: Cuántos días atrás buscar noticias (ignorado en top-headlines)
            max_articles: Máximo número de artículos a retornar (máx 50)
            sort_by: Campo para ordenar (popularity, relevancy, publishedAt)
        
        Returns:
            List[Dict] con estructura:
            {
                "title": str,
                "description": str,
                "publishedAt": str (ISO 8601),
                "source": str,
                "url": str,
                "sentiment": None (será llenado por SentimentService)
            }
        """
        
        if not NEWSAPI_KEY or NEWSAPI_KEY == "not_configured":
            logger.warning(f"NewsAPI key not configured. Retornando lista vacía para {ticker}")
            return []
        
        try:
            # Query: ticker o nombre completo si es especial
            query = NewsService._get_search_query(ticker)
            
            # Usar /top-headlines endpoint (más eficiente)
            # Solo busca las noticias principales (más relevantes)
            params = {
                "q": query,
                "sortBy": sort_by,  # popularity (default) es mejor para noticias importantes
                "pageSize": min(max_articles, 50),  # API limit en free tier
                "apiKey": NEWSAPI_KEY
            }
            
            logger.debug(f"Obteniendo top headlines para {ticker}: {query}")
            
            # Usar endpoint optimizado de top-headlines
            endpoint = "https://newsapi.org/v2/top-headlines"
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("status") != "ok":
                logger.warning(f"NewsAPI error: {data.get('message', 'Unknown error')}")
                return []
            
            articles = data.get("articles", [])
            logger.info(f"Encontradas {len(articles)} top headlines para {ticker} (optimizado)")
            
            # Normalizar respuesta
            normalized = []
            for article in articles:
                normalized.append({
                    "ticker": ticker,
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "publishedAt": article.get("publishedAt", ""),
                    "source": article.get("source", {}).get("name", "Unknown"),
                    "url": article.get("url", ""),
                    "content": article.get("content", ""),
                    "sentiment": None  # Será asignado por SentimentService
                })
            
            return normalized
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching news for {ticker}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in get_news_for_ticker: {str(e)}")
            return []
    
    @staticmethod
    def get_news_batch(
        tickers: List[str],
        days_back: int = 7,
        max_articles: int = 100
    ) -> Dict[str, List[Dict]]:
        """
        Obtiene noticias para múltiples tickers.
        
        Args:
            tickers: Lista de tickers
            days_back: Días atrás
            max_articles: Max artículos por ticker
        
        Returns:
            Dict[ticker] -> List[articles]
        """
        
        results = {}
        for ticker in tickers:
            articles = NewsService.get_news_for_ticker(
                ticker,
                days_back=days_back,
                max_articles=max_articles
            )
            results[ticker] = articles
            logger.info(f"  {ticker}: {len(articles)} artículos")
        
        return results
    
    @staticmethod
    def _get_search_query(ticker: str) -> str:
        """Convierte ticker a query de búsqueda."""
        
        # Casos especiales
        mapping = {
            "BTC-USD": "Bitcoin",
            "ETH-USD": "Ethereum",
            "GC=F": "Gold",
            "CL=F": "Crude Oil",
        }
        
        if ticker in mapping:
            return mapping[ticker]
        
        # Para nombres completos conocidos
        names = {
            "AAPL": "Apple",
            "MSFT": "Microsoft",
            "GOOGL": "Alphabet Google",
            "AMZN": "Amazon",
            "META": "Meta Facebook",
            "NVDA": "Nvidia",
            "TSLA": "Tesla",
            "NFLX": "Netflix",
            "INTC": "Intel",
            "KO": "Coca Cola",
            "BABA": "Alibaba",
        }
        
        return names.get(ticker, ticker)
    
    @staticmethod
    def cache_news_to_file(
        ticker: str,
        articles: List[Dict],
        cache_dir: str = "backend/models/saved_models"
    ) -> bool:
        """
        Cachea artículos a JSON para análisis posterior.
        
        Args:
            ticker: Símbolo del ticker
            articles: Lista de artículos
            cache_dir: Directorio para cachear
        
        Returns:
            bool: True si successful
        """
        
        try:
            import json
            
            os.makedirs(cache_dir, exist_ok=True)
            cache_path = os.path.join(cache_dir, f"{ticker}_news.json")
            
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(articles, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Cached {len(articles)} articles for {ticker} to {cache_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error caching news for {ticker}: {str(e)}")
            return False
    
    @staticmethod
    def load_cached_news(
        ticker: str,
        cache_dir: str = "backend/models/saved_models"
    ) -> List[Dict]:
        """Carga noticias cacheadas."""
        
        try:
            import json
            
            cache_path = os.path.join(cache_dir, f"{ticker}_news.json")
            
            if not os.path.exists(cache_path):
                return []
            
            with open(cache_path, "r", encoding="utf-8") as f:
                articles = json.load(f)
            
            logger.debug(f"Loaded {len(articles)} cached articles for {ticker}")
            return articles
        
        except Exception as e:
            logger.warning(f"Error loading cached news for {ticker}: {str(e)}")
            return []


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.DEBUG)
    
    print("Testing NewsService...")
    
    # Test single ticker
    articles = NewsService.get_news_for_ticker("AAPL", days_back=3, max_articles=5)
    print(f"\nAPPL articles: {len(articles)}")
    if articles:
        print(f"First: {articles[0]['title'][:80]}...")
    
    # Test batch
    print("\nTesting batch...")
    batch = NewsService.get_news_batch(["AAPL", "MSFT"], days_back=3, max_articles=3)
    for ticker, arts in batch.items():
        print(f"  {ticker}: {len(arts)} articles")
