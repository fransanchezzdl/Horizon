"""
Servicio de finanzas: Wrapper alrededor de Yahoo Finance.

Proporciona métodos de alto nivel para obtener datos de mercado,
precios actuales, volatilidad histó rica, etc.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from cachetools import TTLCache
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache de precios (TTL: 5 minutos)
price_cache = TTLCache(maxsize=100, ttl=300)


class FinanceService:
    """Servicio para interactuar con mercados financieros."""
    
    RISK_FREE_RATE = 0.03  # 3% anual
    TRADING_DAYS_PER_YEAR = 252
    
    @staticmethod
    def get_current_price(ticker: str) -> Optional[float]:
        """
        Obtiene el precio actual de un ticker.
        
        Args:
            ticker: Símbolo (ej: "AAPL")
        
        Returns:
            float: Precio actual o None si error
        """
        try:
            # Intentar usar cache primero
            cache_key = f"{ticker}_price"
            if cache_key in price_cache:
                logger.info(f"📦 Usando precio cacheado para {ticker}")
                return price_cache[cache_key]
            
            # Descargar precio actual
            data = yf.Ticker(ticker)
            price = data.info.get('currentPrice') or data.info.get('regularMarketPrice')
            
            if price:
                price_cache[cache_key] = price
                logger.info(f"💰 Precio actual de {ticker}: ${price:.2f}")
                return price
            else:
                logger.warning(f"⚠️ No se pudo obtener precio para {ticker}")
                return None
        
        except Exception as e:
            logger.error(f"❌ Error obteniendo precio para {ticker}: {e}")
            return None
    
    @staticmethod
    def get_historical_prices(
        ticker: str,
        start_date: str = None,
        end_date: str = None,
        period: str = "1y"
    ) -> Optional[pd.DataFrame]:
        """
        Obtiene datos históricos de precios.
        
        Args:
            ticker: Símbolo
            start_date: Fecha inicio (YYYY-MM-DD), opcional si se usa period
            end_date: Fecha fin, défault: hoy
            period: Período ("1d", "1mo", "1y"), défault: "1y"
        
        Returns:
            DataFrame con datos históricos o None si error
        """
        try:
            if start_date and end_date:
                data = yf.download(ticker, start=start_date, end=end_date, progress=False)
            else:
                data = yf.download(ticker, period=period, progress=False)
            
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            logger.info(f"📊 Descargados {len(data)} días de datos para {ticker}")
            return data
        
        except Exception as e:
            logger.error(f"❌ Error descargando datos para {ticker}: {e}")
            return None
    
    @staticmethod
    def calculate_volatility(
        ticker: str,
        period_days: int = 252
    ) -> Optional[float]:
        """
        Calcula volatilidad histórica.
        
        Args:
            ticker: Símbolo
            period_days: Período en días (défault: 252 = 1 año)
        
        Returns:
            float: Volatilidad anualizada (ej: 0.25 = 25%)
        """
        try:
            periods = period_days // 252 + 1  # Convertir a años
            data = yf.download(
                ticker,
                start=datetime.now() - timedelta(days=period_days),
                progress=False
            )
            
            returns = data['Close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(FinanceService.TRADING_DAYS_PER_YEAR)
            
            logger.info(f"📈 Volatilidad de {ticker}: {volatility*100:.2f}%")
            return volatility
        
        except Exception as e:
            logger.error(f"❌ Error calculando volatilidad para {ticker}: {e}")
            return None
    
    @staticmethod
    def calculate_returns(
        ticker: str,
        period_days: int = 252
    ) -> Optional[Dict[str, float]]:
        """
        Calcula retornos históricos en varios plazos.
        
        Args:
            ticker: Símbolo
            period_days: Período máximo en días
        
        Returns:
            Dict con retornos diarios, mensuales, anuales
        """
        try:
            data = yf.download(
                ticker,
                start=datetime.now() - timedelta(days=period_days),
                progress=False
            )
            
            price_initial = data['Close'].iloc[0]
            price_current = data['Close'].iloc[-1]
            
            total_return = (price_current - price_initial) / price_initial
            daily_returns = data['Close'].pct_change().dropna()
            annual_return = daily_returns.mean() * FinanceService.TRADING_DAYS_PER_YEAR
            
            return {
                'return_total': total_return,
                'return_annual': annual_return,
                'return_daily_mean': daily_returns.mean(),
                'return_daily_std': daily_returns.std()
            }
        
        except Exception as e:
            logger.error(f"❌ Error calculando retornos para {ticker}: {e}")
            return None
    
    @staticmethod
    def get_multiple_prices(tickers: List[str]) -> Dict[str, Optional[float]]:
        """
        Obtiene precios actuales para múltiples tickers.
        
        Args:
            tickers: Lista de símbolos
        
        Returns:
            Dict con {ticker: precio}
        """
        prices = {}
        for ticker in tickers:
            prices[ticker] = FinanceService.get_current_price(ticker)
        return prices
    
    @staticmethod
    def validate_ticker(ticker: str) -> bool:
        """
        Valida si un ticker existe y es válido.
        
        Args:
            ticker: Símbolo
        
        Returns:
            bool: True si válido, False si no
        """
        try:
            data = yf.Ticker(ticker)
            info = data.info
            
            # Si consigue algún dato básico, es válido
            is_valid = bool(info.get('regularMarketPrice') or info.get('currentPrice'))
            
            if is_valid:
                logger.info(f"✅ Ticker {ticker} es válido")
            else:
                logger.warning(f"⚠️ Ticker {ticker} no parece válido")
            
            return is_valid
        
        except Exception as e:
            logger.error(f"❌ Error validando {ticker}: {e}")
            return False
    


def get_finance_service() -> FinanceService:
    """Helper para obtener la instancia del servicio."""
    return FinanceService()
