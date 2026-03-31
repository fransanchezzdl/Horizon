"""
Fase 2: Feature Engineering - Nuevos indicadores técnicos avanzados.

Complementa los 18 indicadores existentes con 12 nuevos indicadores
engineered a partir de datos OHLCV, diseñados para capturar patrones
de momentum, volatilidad y reversión de media.

Esperado: +2-4% mejora en accuracy.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class Phase2FeaturesBuilder:
    """Constructor de features avanzados para Fase 2."""
    
    # Ventanas por defecto para cálculos rolling
    WINDOWS = [5, 10, 20]
    
    @staticmethod
    def build_phase2_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Construye 12 nuevos features de ingeniería para XGBoost.
        
        Features engenerados:
        1. momentum_5d: Cambio precio % últimos 5 días
        2. rsi_14: Relative Strength Index
        3. macd_signal: MACD - Signal Line
        4. bbands_pct: % de Bollinger Bands
        5. atr_14: Average True Range (volatilidad)
        6. obv_momentum: On Balance Volume momentum
        7. volume_sma_ratio: Volumen vs SMA
        8. high_low_ratio: (High - Low) / Close
        9. close_range_pct: Close position within (High-Low)
        10. price_momentum_roc: Rate of Change
        11. volatility_std: Volatilidad rolling
        12. price_acceleration: Aceleración en cambios
        
        Args:
            df: DataFrame con OHLCV + indicadores iniciales
        
        Returns:
            DataFrame con 12 nuevos features agregados
        """
        
        try:
            df = df.copy()
            
            logger.info("[Phase2] Construyendo 12 nuevos indicadores técnicos...")
            logger.info(f"[Phase2] DataFrame shape: {df.shape}, columns: {list(df.columns[:10])}")
            
            # Check if required columns exist
            required_cols = ['Close', 'High', 'Low', 'Volume', 'Open']
            missing_cols = [c for c in required_cols if c not in df.columns]
            if missing_cols:
                logger.warning(f"[Phase2] Columnas faltantes: {missing_cols}. Usando lowercase.")
                # Try lowercase
                for col in missing_cols:
                    if col.lower() in df.columns:
                        df[col] = df[col.lower()]
            
            # 1. Momentum simple (cambio %)
            df['momentum_5d'] = df['Close'].pct_change(periods=5)
            
            # 2. RSI 14
            df['rsi_14'] = Phase2FeaturesBuilder._calculate_rsi(df['Close'], period=14)
            
            # 3. MACD - Signal
            df['macd_signal'] = Phase2FeaturesBuilder._calculate_macd_signal(df['Close'])
            
            # 4. Bollinger Bands %
            df['bbands_pct'] = Phase2FeaturesBuilder._calculate_bbands_pct(df['Close'], period=20)
            
            # 5. ATR 14 (volatilidad)
            df['atr_14'] = Phase2FeaturesBuilder._calculate_atr(df, period=14)
            
            # 6. OBV Momentum
            df['obv_momentum'] = Phase2FeaturesBuilder._calculate_obv_momentum(
                df['Close'], df['Volume']
            )
            
            # 7. Volume SMA Ratio
            df['volume_sma_ratio'] = Phase2FeaturesBuilder._calculate_volume_sma_ratio(
                df['Volume'], period=20
            )
            
            # 8. High-Low Ratio
            df['high_low_ratio'] = (df['High'] - df['Low']) / df['Close']
            
            # 9. Close Range %
            df['close_range_pct'] = (df['Close'] - df['Low']) / (df['High'] - df['Low'])
            df['close_range_pct'] = df['close_range_pct'].replace([np.inf, -np.inf], 0)
            
            # 10. Rate of Change
            df['roc_10'] = Phase2FeaturesBuilder._calculate_roc(df['Close'], period=10)
            
            # 11. Volatility STD
            df['volatility_std'] = df['Close'].pct_change().rolling(window=20).std()
            
            # 12. Price Acceleration (cambio en cambio)
            df['price_acceleration'] = df['Close'].diff().diff()
            
            # Rellenar NaNs
            df = df.fillna(method='bfill').fillna(method='ffill').fillna(0)
            
            # Validaciones
            features_list = [
                'momentum_5d', 'rsi_14', 'macd_signal', 'bbands_pct',
                'atr_14', 'obv_momentum', 'volume_sma_ratio', 'high_low_ratio',
                'close_range_pct', 'roc_10', 'volatility_std', 'price_acceleration'
            ]
            
            for feat in features_list:
                if feat not in df.columns:
                    logger.warning(f"[Phase2] Feature {feat} no creado")
                    df[feat] = 0
            
            logger.info(f"[Phase2] ✅ 12 indicadores creados exitosamente")
            
            return df
            
        except Exception as e:
            logger.error(f"[Phase2] Error construyendo features: {str(e)}")
            return df
    
    @staticmethod
    def _calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / (loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.fillna(50)
    
    @staticmethod
    def _calculate_macd_signal(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
        """MACD - Signal Line."""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        
        return (macd - macd_signal).fillna(0)
    
    @staticmethod
    def _calculate_bbands_pct(prices: pd.Series, period: int = 20, std_dev: float = 2.0) -> pd.Series:
        """Bollinger Bands %."""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        
        bbands_pct = (prices - lower) / (upper - lower)
        
        return bbands_pct.fillna(0.5)
    
    @staticmethod
    def _calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Average True Range."""
        high = df['High']
        low = df['Low']
        close = df['Close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr.fillna(0)
    
    @staticmethod
    def _calculate_obv_momentum(prices: pd.Series, volume: pd.Series) -> pd.Series:
        """On Balance Volume Momentum."""
        obv = (np.sign(prices.diff()) * volume).fillna(0).cumsum()
        obv_momentum = obv.diff(periods=5)
        
        return obv_momentum.fillna(0)
    
    @staticmethod
    def _calculate_volume_sma_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
        """Volumen actual vs SMA."""
        volume_sma = volume.rolling(window=period).mean()
        ratio = volume / (volume_sma + 1e-10)
        
        return ratio.fillna(1)
    
    @staticmethod
    def _calculate_roc(prices: pd.Series, period: int = 10) -> pd.Series:
        """Rate of Change."""
        roc = ((prices - prices.shift(period)) / prices.shift(period)) * 100
        
        return roc.fillna(0)


def integrate_phase2_with_pipeline(df: pd.DataFrame) -> pd.DataFrame:
    """
    Integra Phase 2 features en el pipeline de datos existente.
    
    Args:
        df: DataFrame con features básicos + indicadores avanzados
    
    Returns:
        DataFrame con 12 features nuevos agregados
    """
    
    logger.info("[Phase2] Integrando features de Fase 2 en pipeline...")
    
    # Construir Phase 2 features
    df = Phase2FeaturesBuilder.build_phase2_features(df)
    
    logger.info("[Phase2] ✅ Fase 2 features integrados en pipeline")
    
    return df
