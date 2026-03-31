"""
Integración de features de sentimiento en el pipeline de datos.

Complementa los features técnicos existentes (OHLCV stats) con
features de sentimiento de noticias.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
import os
import json

from ..services.news_service import NewsService
from ..services.sentiment_service import SentimentService

logger = logging.getLogger(__name__)


class SentimentFeaturesBuilder:
    """Constructor de features de sentimiento para ML."""
    
    def __init__(self, ticker: str, cache_dir: str = "backend/models/saved_models"):
        """
        Inicializa builder.
        
        Args:
            ticker: Símbolo del ticker
            cache_dir: Directorio para cachear noticias
        """
        self.ticker = ticker
        self.cache_dir = cache_dir
        self.articles = []
        self.daily_stats = {}
        self.rolling_features = {}
    
    def fetch_articles(
        self,
        days_back: int = 180,
        max_articles: int = 500
    ) -> bool:
        """
        Obtiene noticias para el ticker.
        
        Args:
            days_back: Días atrás a buscar
            max_articles: Máximo de artículos
        
        Returns:
            bool: True si éxito
        """
        
        try:
            logger.info(f"Fetching articles for {self.ticker}...")
            
            # Intentar desde cache primero
            cached = NewsService.load_cached_news(self.ticker, self.cache_dir)
            if cached:
                logger.info(f"Loaded {len(cached)} cached articles for {self.ticker}")
                self.articles = cached
                return True
            
            # Si no hay cache, obtener desde API
            self.articles = NewsService.get_news_for_ticker(
                self.ticker,
                days_back=days_back,
                max_articles=max_articles
            )
            
            # Cachear
            if self.articles:
                NewsService.cache_news_to_file(self.ticker, self.articles, self.cache_dir)
            
            logger.info(f"Fetched {len(self.articles)} articles for {self.ticker}")
            return len(self.articles) > 0
        
        except Exception as e:
            logger.error(f"Error fetching articles: {str(e)}")
            return False
    
    def analyze_sentiment(self, initialize_model: bool = True) -> bool:
        """
        Analiza sentimiento de artículos usando FinBERT.
        
        Args:
            initialize_model: Si debe inicializar FinBERT
        
        Returns:
            bool: True si éxito
        """
        
        try:
            if not self.articles:
                logger.warning(f"No articles to analyze for {self.ticker}")
                return False
            
            if initialize_model:
                if not SentimentService.initialize_model():
                    logger.warning("Failed to initialize FinBERT model")
                    # Seguir sin sentimiento
                    return False
            
            logger.info(f"Analyzing sentiment for {len(self.articles)} articles...")
            
            self.articles = SentimentService.analyze_articles(self.articles)
            
            logger.info(f"Sentiment analysis complete")
            return True
        
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return False
    
    def build_daily_stats(self) -> bool:
        """
        Agrega sentimiento por día.
        
        Returns:
            bool: True si éxito
        """
        
        try:
            self.daily_stats = SentimentService.aggregate_daily_sentiment(
                self.articles,
                date_field="publishedAt"
            )
            
            logger.info(f"Built daily stats for {len(self.daily_stats)} days")
            return len(self.daily_stats) > 0
        
        except Exception as e:
            logger.error(f"Error building daily stats: {str(e)}")
            return False
    
    def build_rolling_features(self, windows: List[int] = [5, 10, 20]) -> bool:
        """
        Calcula features rolling.
        
        Args:
            windows: Ventanas (días)
        
        Returns:
            bool: True si éxito
        """
        
        try:
            if not self.daily_stats:
                logger.warning("No daily stats to build rolling features")
                return False
            
            self.rolling_features = SentimentService.rolling_sentiment_features(
                self.daily_stats,
                windows=windows
            )
            
            logger.info(f"Built rolling features with windows: {windows}")
            return len(self.rolling_features) > 0
        
        except Exception as e:
            logger.error(f"Error building rolling features: {str(e)}")
            return False
    
    def get_features_dataframe(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Retorna features de sentimiento como DataFrame.
        
        Args:
            start_date: Fecha inicio (YYYY-MM-DD)
            end_date: Fecha fin (YYYY-MM-DD)
        
        Returns:
            DataFrame con índice de fecha y columns de sentimiento
        """
        
        if not self.rolling_features:
            logger.warning("No rolling features available")
            return pd.DataFrame()
        
        # Convertir a DataFrame
        df = pd.DataFrame.from_dict(
            self.rolling_features,
            orient="index"
        )
        df.index.name = "date"
        df.index = pd.to_datetime(df.index)
        
        # Filtrar por rango si se especifica
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]
        
        # Llenar NaN con 0 (días sin noticias)
        df = df.fillna(0.0)
        
        logger.info(f"Generated features DataFrame with shape {df.shape}")
        return df
    
    def save_features(self, output_path: Optional[str] = None) -> bool:
        """
        Guarda features a CSV.
        
        Args:
            output_path: Ruta de salida (default: cache_dir/ticker_sentiment.csv)
        
        Returns:
            bool: True si éxito
        """
        
        try:
            if output_path is None:
                output_path = os.path.join(
                    self.cache_dir,
                    f"{self.ticker}_sentiment_features.csv"
                )
            
            df = self.get_features_dataframe()
            
            if df.empty:
                logger.warning(f"DataFrame is empty, not saving")
                return False
            
            df.to_csv(output_path)
            logger.info(f"Saved sentiment features to {output_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving features: {str(e)}")
            return False
    
    def get_feature_names(self) -> List[str]:
        """Retorna nombres de features de sentimiento."""
        
        if not self.rolling_features:
            return []
        
        # Usar primer día como template
        first_day = list(self.rolling_features.values())[0]
        return list(first_day.keys())


def merge_sentiment_with_ohlcv(
    ohlcv_df: pd.DataFrame,
    sentiment_df: pd.DataFrame,
    method: str = "forward_fill"
) -> pd.DataFrame:
    """
    Combina features de OHLCV con features de sentimiento.
    
    Args:
        ohlcv_df: DataFrame con datos OHLCV (índice: fecha)
        sentiment_df: DataFrame con features de sentimiento (índice: fecha)
        method: "forward_fill", "bfill", o "interpolate"
    
    Returns:
        DataFrame combinado
    """
    
    try:
        # Alinear índices
        merged = ohlcv_df.join(sentiment_df, how="left")
        
        # Rellenar NaN
        if method == "forward_fill":
            merged = merged.fillna(method="ffill")
        elif method == "bfill":
            merged = merged.fillna(method="bfill")
        elif method == "interpolate":
            merged = merged.interpolate(method="linear")
        
        # Llenar finales con 0
        merged = merged.fillna(0.0)
        
        logger.info(f"Merged OHLCV and sentiment: {merged.shape}")
        return merged
    
    except Exception as e:
        logger.error(f"Error merging dataframes: {str(e)}")
        return ohlcv_df


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    
    print("Testing SentimentFeaturesBuilder...")
    
    # Usar AAPL como test
    builder = SentimentFeaturesBuilder("AAPL")
    
    # Step 1: Fetch (usará cache si existe)
    if not builder.fetch_articles(days_back=30):
        print("Failed to fetch articles. Check NewsAPI key:")
        print("  Set: export NEWSAPI_KEY=your_key")
        exit(1)
    
    # Step 2: Analyze sentiment (usará CPU si GPU no disponible)
    print("(This may take a few minutes on first run without GPU)")
    if not builder.analyze_sentiment():
        print("Warning: Sentiment analysis failed, continuing without sentiment features")
    
    # Step 3: Build daily stats
    if not builder.build_daily_stats():
        print("Failed to build daily stats")
        exit(1)
    
    # Step 4: Build rolling features
    if not builder.build_rolling_features():
        print("Failed to build rolling features")
        exit(1)
    
    # Step 5: Get DataFrame
    df = builder.get_features_dataframe()
    print(f"\nGenerated sentiment features:")
    print(f"  Shape: {df.shape}")
    print(f"  Columns: {list(df.columns)}")
    print(f"  Date range: {df.index.min()} to {df.index.max()}")
    print(f"\nFirst rows:")
    print(df.head())
    
    # Step 6: Save
    builder.save_features()
