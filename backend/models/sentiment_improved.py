"""
Sentimiento Mejorado: Análisis técnico con LAG temporal y normalización por volatilidad.

Idea: El sentimiento de AYER predice el movimiento de HOY
      - Alpha Vantage proporciona noticias históricas
      - Calcular sentimiento BINARIO (palabras positivas/negativas)
      - Crear features con lag 1-5 días
      - Normalizar por volatilidad (noticias en calma > en turbulencia)
"""

import numpy as np
import pandas as pd
import logging
from typing import Tuple, Dict, List
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Palabras positivas/negativas para análisis de sentimiento básico
POSITIVE_WORDS = {
    'beat', 'growth', 'profit', 'gain', 'surge', 'rally', 'bull', 'optimism',
    'strength', 'recovery', 'upgrade', 'buy', 'strong', 'success', 'positive',
    'winner', 'surge', 'jump', 'rise', 'peak', 'record', 'outperform'
}

NEGATIVE_WORDS = {
    'loss', 'decline', 'fall', 'bear', 'pessimism', 'weakness', 'downgrade',
    'sell', 'weak', 'failure', 'negative', 'loser', 'plunge', 'crash', 'drop',
    'miss', 'bankruptcy', 'scandal', 'underperform', 'risk', 'recession'
}

class ImprovedSentimentAnalyzer:
    """
    Análisis de sentimiento TÉCNICO con características temporales.
    """
    
    def __init__(self, window_size: int = 30):
        """
        Args:
            window_size: días históricos para calcular sentimiento medio
        """
        self.window_size = window_size
    
    def calculate_news_sentiment_score(self, text: str) -> float:
        """
        Calcula sentimiento BINARIO de un texto de noticia.
        
        Retorna:
            float: -1.0 (muy negativo) a +1.0 (muy positivo)
        """
        if not text or not isinstance(text, str):
            return 0.0
        
        text_lower = text.lower()
        
        positive_count = sum(1 for word in POSITIVE_WORDS if word in text_lower)
        negative_count = sum(1 for word in NEGATIVE_WORDS if word in text_lower)
        
        total = positive_count + negative_count
        
        if total == 0:
            return 0.0
        
        # Normalizar entre -1.0 y +1.0
        sentiment = (positive_count - negative_count) / total
        
        return np.clip(sentiment, -1.0, 1.0)
    
    def create_sentiment_features_with_lag(
        self, 
        df: pd.DataFrame,
        sentiment_column: str = 'daily_sentiment',
        volatility_column: str = 'volatility_std'
    ) -> pd.DataFrame:
        """
        Crea features de sentimiento con lag 1-5 días y normalización.
        
        Args:
            df: DataFrame con índice temporal (fecha como index)
            sentiment_column: nombre de columna con sentimiento diario
            volatility_column: nombre de columna con volatilidad
        
        Retorna:
            DataFrame con columnas adicionales de sentimiento laggeado
        """
        
        # Crear copia para no modificar original
        df_features = df.copy()
        
        # Asegurar que el sentimiento está presente
        if sentiment_column not in df_features.columns:
            logger.warning(f"Columna '{sentiment_column}' no encontrada, creando con valor 0")
            df_features[sentiment_column] = 0.0
        
        # Asegurar volatilidad (si no existe, estimarla)
        if volatility_column not in df_features.columns:
            # Calcular volatilidad como desviación estándar de returns
            if 'Close' in df_features.columns:
                returns = df_features['Close'].pct_change()
                df_features[volatility_column] = returns.rolling(window=5).std()
                df_features[volatility_column].fillna(method='bfill', inplace=True)
                df_features[volatility_column].fillna(0.01, inplace=True)
            else:
                df_features[volatility_column] = 0.01  # Valor por defecto
        
        # ────── CREAR FEATURES DE LAG ──────
        
        # 1. Sentimiento simple con lag 1-5 días
        for lag in range(1, 6):
            df_features[f'sentiment_lag_{lag}d'] = df_features[sentiment_column].shift(lag)
        
        # 2. Promedio móvil de sentimiento (media móvil 3 y 5 días)
        df_features['sentiment_ma_3d'] = df_features[sentiment_column].rolling(window=3, min_periods=1).mean()
        df_features['sentiment_ma_5d'] = df_features[sentiment_column].rolling(window=5, min_periods=1).mean()
        
        # 3. NORMALIZACIÓN POR VOLATILIDAD (clave)
        # Sentimiento más importante en épocas tranquilas ayuda a predecir
        vol_normalized = df_features[sentiment_column] / (df_features[volatility_column] + 0.001)
        df_features['sentiment_vol_normalized'] = vol_normalized
        
        # Versión laggeada también
        for lag in range(1, 3):
            vol_normalized_lag = df_features[sentiment_column].shift(lag) / (df_features[volatility_column] + 0.001)
            df_features[f'sentiment_vol_norm_lag_{lag}d'] = vol_normalized_lag
        
        # 4. MOMENTUM de sentimiento
        # ¿El sentimiento está mejorando o empeorando?
        df_features['sentiment_momentum_5d'] = df_features[sentiment_column].diff(5)
        
        # 5. CAMBIO RECIENTE vs HISTÓRICO
        # Desviación del sentimiento promedio
        hist_sentiment_mean = df_features[sentiment_column].rolling(window=self.window_size, min_periods=1).mean()
        df_features['sentiment_deviation'] = df_features[sentiment_column] - hist_sentiment_mean
        
        # Llenar NaN con 0 (sin sentimiento conocido)
        for col in df_features.columns:
            if col.startswith('sentiment_'):
                df_features[col].fillna(0, inplace=True)
        
        return df_features
    
    def get_feature_names(self) -> List[str]:
        """Retorna lista de nombres de features de sentimiento creadas"""
        return [
            'sentiment_lag_1d', 'sentiment_lag_2d', 'sentiment_lag_3d', 
            'sentiment_lag_4d', 'sentiment_lag_5d',
            'sentiment_ma_3d', 'sentiment_ma_5d',
            'sentiment_vol_normalized',
            'sentiment_vol_norm_lag_1d', 'sentiment_vol_norm_lag_2d',
            'sentiment_momentum_5d',
            'sentiment_deviation'
        ]


def extract_daily_sentiment(df: pd.DataFrame, text_column: str = 'news_summary') -> pd.Series:
    """
    Extrae sentimiento diario agregado de un DataFrame.
    
    Args:
        df: DataFrame con noticias (debe tener columna de fecha y texto)
        text_column: nombre de columna con texto de noticia
    
    Retorna:
        Series con sentimiento agregado por fecha
    """
    
    analyzer = ImprovedSentimentAnalyzer()
    
    if text_column not in df.columns:
        logger.warning(f"Columna '{text_column}' no encontrada")
        return pd.Series(0.0)
    
    # Calcular sentimiento por cada noticia
    df['sentiment_score'] = df[text_column].apply(analyzer.calculate_news_sentiment_score)
    
    # Agregar por fecha (promedio diario)
    if 'date' in df.columns or 'Date' in df.columns:
        date_col = 'date' if 'date' in df.columns else 'Date'
        daily_sentiment = df.groupby(date_col)['sentiment_score'].mean()
    elif df.index.name and 'date' in df.index.name.lower():
        daily_sentiment = df.groupby(df.index.date)['sentiment_score'].mean()
    else:
        # Si no hay fecha clara, calcular promedio general
        daily_sentiment = pd.Series(df['sentiment_score'].mean())
    
    return daily_sentiment


if __name__ == '__main__':
    # Test básico
    print("[TEST] Improved Sentiment Analyzer")
    
    analyzer = ImprovedSentimentAnalyzer()
    
    # Test 1: Cálculo de sentimiento de texto
    test_texts = [
        "Company beat earnings expectations with strong growth",  # Positivo
        "Stock crashes on bankruptcy news",  # Negativo
        "Price remains stable",  # Neutral
    ]
    
    print("\n1️⃣ Análisis de texto:")
    for text in test_texts:
        sentiment = analyzer.calculate_news_sentiment_score(text)
        print(f"   '{text}' → Sentiment: {sentiment:+.2f}")
    
    # Test 2: Features con lag
    print("\n2️⃣ Features con lag:")
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=20, freq='D')
    df_test = pd.DataFrame({
        'date': dates,
        'Close': np.random.randn(20).cumsum() + 100,
        'daily_sentiment': np.random.randn(20) * 0.3,  # Sentimiento aleatorio
    })
    df_test.set_index('date', inplace=True)
    
    df_features = analyzer.create_sentiment_features_with_lag(df_test)
    
    print(f"   Features creadas: {analyzer.get_feature_names()}")
    print(f"   Columnas totales: {len(df_features.columns)}")
    print(f"\n   Últimas 3 filas:")
    print(df_features[['daily_sentiment', 'sentiment_lag_1d', 'sentiment_vol_normalized']].tail(3))
    
    print("\n✅ Test completado")
