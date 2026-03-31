"""
Macro Indicators para commodities (oro, plata).

Características especializadas para mejorar predicción de:
- Oro (GC=F): Sensible a DXY (US Dollar Index), tasas reales, riesgo geopolítico
- Plata (SI=F): Sensible a demanda industrial, CRB index, copper ratio

Estas features capturan regímenes de riesgo que no están en technical puro.
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional
import warnings

warnings.filterwarnings('ignore')


class CommodityMacroIndicators:
    """
    Indicadores macro para commodities.
    
    Métodos para calcular:
    - USD Index proxy (usando correlation con other assets)
    - Real yield signals  
    - Market regime indicators
    - Cross-commodity spreads
    """
    
    @staticmethod
    def calculate_dollar_proxy(close_prices: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Calcula proxy de US Dollar movement usando volatilidad y volumen.
        
        Lógica:
        - Días con caída de precio + volumen alto = riesgo-off = USD strong
        - Días con subida de precio + volumen alto = riesgo-on = USD weak
        
        Args:
            close_prices: Array de precios de cierre
            volume: Array de volúmenes
            
        Returns:
            Array de dollar_proxy [-1, 1] donde 1 = USD fuerte
        """
        returns = np.diff(close_prices) / close_prices[:-1]
        volume_norm = (volume[1:] - volume[1:].mean()) / (volume[1:].std() + 1e-6)
        
        # Dollar proxy: neg return + high volume = $ strong
        dollar_proxy = -returns * volume_norm
        
        # Normalizar
        dollar_proxy = (dollar_proxy - dollar_proxy.mean()) / (dollar_proxy.std() + 1e-6)
        dollar_proxy = np.clip(dollar_proxy, -1, 1)
        
        return np.concatenate([[0], dollar_proxy])  # align shape
    
    @staticmethod
    def calculate_real_rates_proxy(close_prices: np.ndarray, window: int = 20) -> np.ndarray:
        """
        Proxy de tasas reales usando momentum y volatilidad.
        
        Tasas reales altas (inflación baja) → oro débil
        Tasas reales bajas (inflación alta) → oro fuerte
        
        Args:
            close_prices: Array de precios
            window: Ventana para calcular volatilidad
            
        Returns:
            Array de real_rates_proxy donde valores altos = tasas reales altas = oro débil
        """
        # Volatilidad realizada = tasa real proxy  (simplificado)
        returns = np.diff(close_prices) / (close_prices[:-1] + 1e-8)
        realized_vol = pd.Series(returns).rolling(window=window).std().values
        
        # Align shape - agregar 0 al principio
        realized_vol = np.concatenate([[0], realized_vol])
        
        # Normalizar
        realized_vol = (realized_vol - np.nanmean(realized_vol)) / (np.nanstd(realized_vol) + 1e-6)
        realized_vol = np.nan_to_num(realized_vol)
        
        return realized_vol
    
    @staticmethod
    def calculate_risk_sentiment(close_prices: np.ndarray, volume: np.ndarray, window: int = 20) -> np.ndarray:
        """
        Indicador de sentimiento de riesgo (risk-on vs risk-off).
        
        Risk-on: Precios subiendo + volumen creciente
        Risk-off: Precios cayendo + volumen decreciente
        
        Args:
            close_prices: Array de precios
            volume: Array de volúmenes
            window: Ventana de promedio móvil
            
        Returns:
            Array de risk_sentiment [-1, 1] donde 1 = risk-on
        """
        returns = np.diff(close_prices) / (close_prices[:-1] + 1e-8)
        volume_change = np.diff(volume) / (volume[:-1] + 1e-8)
        
        # Risk sentiment = return * (volume change)
        risk_sentiment = returns * np.sign(volume_change)
        
        # Smooth con SMA
        risk_sentiment = pd.Series(risk_sentiment).rolling(window=window, center=True).mean().values
        
        # Align - agregar 0 al inicio
        risk_sentiment = np.concatenate([[0], risk_sentiment])
        
        # Normalizar
        risk_sentiment = (risk_sentiment - np.nanmean(risk_sentiment)) / (np.nanstd(risk_sentiment) + 1e-6)
        risk_sentiment = np.nan_to_num(np.clip(risk_sentiment, -1, 1))
        
        return risk_sentiment
    
    @staticmethod
    def calculate_industrial_demand_proxy(volume: np.ndarray, volatility: np.ndarray, window: int = 20) -> np.ndarray:
        """
        Proxy de demanda industrial (especialmente para plata).
        
        Demanda industrial alta → volumen de trading alto + baja volatilidad
        Demanda industrial baja → volumen bajo + volatilidad variable
        
        Args:
            volume: Array de volúmenes
            volatility: Array de volatilidades realizadas
            window: Ventana de promedio
            
        Returns:
            Array de industrial_demand_proxy
        """
        # Indicador compositoo: vol alto + vol de volatilidad baja = demanda industrial
        volume_norm = (volume - volume.mean()) / (volume.std() + 1e-6)
        volatility_norm = (volatility - volatility.mean()) / (volatility.std() + 1e-6)
        
        # Industrial demand = high volume + low vol volatility
        industrial_demand = volume_norm - volatility_norm
        
        # Smooth
        industrial_demand = pd.Series(industrial_demand).rolling(window=window, center=True).mean().values
        industrial_demand = np.nan_to_num(industrial_demand)
        
        return industrial_demand
    
    @staticmethod
    def create_macro_features_dataframe(
        close_prices: np.ndarray,
        volume: np.ndarray,
        dates: np.ndarray,
        realized_volatility: np.ndarray
    ) -> pd.DataFrame:
        """
        Crea DataFrame con todas las macro features para commodities.
        
        Args:
            close_prices: Array de precios (n,)
            volume: Array de volúmenes (n,)
            dates: Array de fechas
            realized_volatility: Array de volatilidad realizada
            
        Returns:
            DataFrame con columnas de macro features
        """
        df = pd.DataFrame({
            'date': dates,
            'close': close_prices,
            'volume': volume,
            'realized_vol': realized_volatility
        })
        
        # Calcular indicators
        df['dollar_proxy'] = CommodityMacroIndicators.calculate_dollar_proxy(close_prices, volume)
        df['real_rates_proxy'] = CommodityMacroIndicators.calculate_real_rates_proxy(close_prices)
        df['risk_sentiment'] = CommodityMacroIndicators.calculate_risk_sentiment(close_prices, volume)
        df['industrial_demand'] = CommodityMacroIndicators.calculate_industrial_demand_proxy(
            volume,
            realized_volatility
        )
        
        return df


def augment_commodity_features(
    X: pd.DataFrame,
    ticker: str,
    lookback: int = 20
) -> pd.DataFrame:
    """
    Aña de features macro específicas para commodities.
    
    Si ticker es GC=F o SI=F, agrega macro indicators.
    Si es otro, devuelve sin cambios.
    
    Args:
        X: DataFrame de features
        ticker: Símbolo del ticker
        lookback: Ventana para cálculos
        
    Returns:
        DataFrame with extra columns if commodity, otherwise unchanged
    """
    if ticker not in ['GC=F', 'SI=F']:
        return X
    
    print(f"   📊 Augmentando features para commodity {ticker}...")
    
    # Asegurar que existen columnas necesarias
    required_cols = ['close', 'volume', 'realized_vol']
    missing = [c for c in required_cols if c not in X.columns]
    
    if missing:
        print(f"      ⚠️  Faltan columnas: {missing} - usando defaults")
        if 'close' not in X.columns and 'Close' in X.columns:
            X = X.copy()
            X['close'] = X['Close']
        if 'volume' not in X.columns and 'Volume' in X.columns:
            X = X.copy()
            X['volume'] = X['Volume']
        if 'realized_vol' not in X.columns:
            returns = np.diff(X['close'].values) / X['close'].values[:-1]
            X = X.copy()
            X['realized_vol'] = np.concatenate([
                [0],
                pd.Series(returns).rolling(window=lookback).std().values
            ])
    
    try:
        # Extraer arrays
        close_prices = X['close'].values
        volume = X['volume'].values
        realized_vol = X['realized_vol'].values
        
        # Calcular macro indicators
        X = X.copy()
        X['dollar_proxy'] = CommodityMacroIndicators.calculate_dollar_proxy(close_prices, volume)
        X['real_rates_proxy'] = CommodityMacroIndicators.calculate_real_rates_proxy(close_prices)
        X['risk_sentiment'] = CommodityMacroIndicators.calculate_risk_sentiment(close_prices, volume)
        X['industrial_demand'] = CommodityMacroIndicators.calculate_industrial_demand_proxy(volume, realized_vol)
        
        print(f"      ✅ {len(['dollar_proxy', 'real_rates_proxy', 'risk_sentiment', 'industrial_demand'])} macro features añadidas")
        
    except Exception as e:
        print(f"      ❌ Error añadiendo macro features: {e}")
        pass
    
    return X


if __name__ == "__main__":
    # Test
    print("Testing CommodityMacroIndicators\n")
    
    # Simulación de datos de oro
    n = 500
    dates = pd.date_range('2023-01-01', periods=n)
    close = 1800 + np.cumsum(np.random.randn(n)) * 5
    volume = 100000 + np.random.randint(-20000, 20000, n)
    realized_vol = np.abs(np.random.randn(n)) * 0.02
    
    df = CommodityMacroIndicators.create_macro_features_dataframe(close, volume, dates, realized_vol)
    
    print(f"Created DataFrame with {len(df)} rows and {len(df.columns)} columns")
    print(f"\nColumns: {list(df.columns)}")
    print(f"\nFirst 5 rows:")
    print(df.head())
    print(f"\nStatistics:")
    print(df.describe())
