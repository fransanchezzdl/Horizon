"""
Módulo para obtener features adicionales desde Alpha Vantage MCP.

Proporciona datos fundamentales, técnicos avanzados y macroeconómicos
para mejorar el accuracy del modelo de predicción.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Features fundamentales que vamos a obtener de Alpha Vantage
FUNDAMENTAL_FEATURES = [
    "PE_Ratio",           # Price-to-Earnings ratio
    "EPS",                # Earnings Per Share
    "Dividend_Yield",     # Rendimiento de dividendos
    "Book_Value",         # Valor en libros por acción
    "ROE",                # Return on Equity
    "ROA",                # Return on Assets
    "Debt_to_Equity",     # Ratio deuda/capital
    "Current_Ratio",      # Ratio corriente (liquidez)
    "Quick_Ratio",        # Ratio rápido (liquidez inmediata)
    "Profit_Margin",      # Margen de beneficio
]

# Indicadores técnicos avanzados de Alpha Vantage
ADVANCED_TECHNICAL_FEATURES = [
    "ADX",                # Average Directional Index (fuerza de tendencia)
    "CCI",                # Commodity Channel Index
    "Stochastic_K",       # Oscilador estocástico %K
    "Stochastic_D",       # Oscilador estocástico %D
    "Williams_R",         # Williams %R
]

# Indicadores macroeconómicos
MACRO_FEATURES = [
    "GDP_Growth",         # Crecimiento del PIB (trimestral)
    "Interest_Rate",      # Tasa de interés de referencia (Federal Funds Rate)
    "Inflation_Rate",     # Tasa de inflación (CPI)
]

# Todas las features de Alpha Vantage (18 en total)
ALL_AV_FEATURES = FUNDAMENTAL_FEATURES + ADVANCED_TECHNICAL_FEATURES + MACRO_FEATURES


"""
Módulo para calcular features técnicas avanzadas.

Proporciona indicadores técnicos adicionales calculados localmente
para mejorar el accuracy del modelo de predicción.
"""

import logging
import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Dict

logger = logging.getLogger(__name__)

# Features técnicas avanzadas (18 en total, todas varían diariamente)
ADVANCED_TECHNICAL_FEATURES = [
    # Indicadores de tendencia (5)
    "ADX",                # Average Directional Index (fuerza de tendencia)
    "CCI",                # Commodity Channel Index
    "Aroon_Up",           # Aroon Up (tendencia alcista)
    "Aroon_Down",         # Aroon Down (tendencia bajista)
    "DX",                 # Directional Movement Index
    
    # Osciladores (5)
    "Stochastic_K",       # Oscilador estocástico %K
    "Stochastic_D",       # Oscilador estocástico %D
    "Williams_R",         # Williams %R
    "MFI",                # Money Flow Index (RSI con volumen)
    "Ultimate_Osc",       # Ultimate Oscillator
    
    # Momentum (4)
    "ROC",                # Rate of Change
    "CMO",                # Chande Momentum Oscillator
    "TSI",                # True Strength Index
    "KST",                # Know Sure Thing
    
    # Volatilidad (2)
    "Keltner_PctB",       # Keltner Channels %B
    "Donchian_PctB",      # Donchian Channels %B
    
    # Volumen (2)
    "OBV",                # On Balance Volume
    "CMF",                # Chaikin Money Flow
]


def compute_advanced_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula 18 indicadores técnicos avanzados usando pandas_ta.
    
    Todos estos indicadores varían diariamente y aportan información
    útil para la predicción. Son calculados localmente sin necesidad
    de APIs externas.
    
    Args:
        df: DataFrame con columnas OHLCV (Open, High, Low, Close, Volume)
        
    Returns:
        DataFrame con las 18 features técnicas avanzadas añadidas
    """
    result_df = df.copy()
    
    try:
        # === INDICADORES DE TENDENCIA (5) ===
        
        # ADX (Average Directional Index) - fuerza de tendencia
        adx_df = ta.adx(df["High"], df["Low"], df["Close"], length=14)
        result_df["ADX"] = adx_df["ADX_14"]
        result_df["DX"] = adx_df["DMP_14"] - adx_df["DMN_14"]  # Directional Movement
        
        # CCI (Commodity Channel Index) - normalizar usando percentiles robustos
        cci = ta.cci(df["High"], df["Low"], df["Close"], length=20)
        # Usar percentiles 1 y 99 para normalización robusta
        cci_p01 = cci.quantile(0.01)
        cci_p99 = cci.quantile(0.99)
        result_df["CCI"] = np.clip((cci - cci_p01) / (cci_p99 - cci_p01) * 2 - 1, -1.0, 1.0)
        
        # Aroon (tendencia alcista/bajista)
        aroon_df = ta.aroon(df["High"], df["Low"], length=25)
        result_df["Aroon_Up"] = aroon_df["AROONU_25"]
        result_df["Aroon_Down"] = aroon_df["AROOND_25"]
        
        # === OSCILADORES (5) ===
        
        # Stochastic Oscillator (%K y %D)
        stoch_df = ta.stoch(df["High"], df["Low"], df["Close"], k=14, d=3)
        result_df["Stochastic_K"] = stoch_df["STOCHk_14_3_3"]
        result_df["Stochastic_D"] = stoch_df["STOCHd_14_3_3"]
        
        # Williams %R
        result_df["Williams_R"] = ta.willr(df["High"], df["Low"], df["Close"], length=14)
        
        # MFI (Money Flow Index) - RSI con volumen
        result_df["MFI"] = ta.mfi(
            df["High"], df["Low"], df["Close"], df["Volume"], length=14
        )
        
        # Ultimate Oscillator
        result_df["Ultimate_Osc"] = ta.uo(
            df["High"], df["Low"], df["Close"], fast=7, medium=14, slow=28
        )
        
        # === MOMENTUM (4) ===
        
        # ROC (Rate of Change)
        result_df["ROC"] = ta.roc(df["Close"], length=10)
        
        # CMO (Chande Momentum Oscillator)
        result_df["CMO"] = ta.cmo(df["Close"], length=14)
        
        # TSI (True Strength Index)
        tsi_df = ta.tsi(df["Close"], fast=13, slow=25)
        result_df["TSI"] = tsi_df["TSI_13_25_13"]
        
        # KST (Know Sure Thing) - normalizar usando percentiles
        kst_df = ta.kst(df["Close"])
        kst = kst_df["KST_10_15_20_30_10_10_10_15"]
        # Normalizar a [-1, 1] usando percentiles 1 y 99
        kst_p01 = kst.quantile(0.01)
        kst_p99 = kst.quantile(0.99)
        result_df["KST"] = np.clip((kst - kst_p01) / (kst_p99 - kst_p01) * 2 - 1, -1.0, 1.0)
        
        # === VOLATILIDAD (2) ===
        
        # Keltner Channels %B
        kc_df = ta.kc(df["High"], df["Low"], df["Close"], length=20)
        kc_upper = kc_df["KCUe_20_2"]
        kc_lower = kc_df["KCLe_20_2"]
        result_df["Keltner_PctB"] = (df["Close"] - kc_lower) / (kc_upper - kc_lower)
        
        # Donchian Channels %B
        dc_df = ta.donchian(df["High"], df["Low"], lower_length=20, upper_length=20)
        dc_upper = dc_df["DCU_20_20"]
        dc_lower = dc_df["DCL_20_20"]
        result_df["Donchian_PctB"] = (df["Close"] - dc_lower) / (dc_upper - dc_lower)
        
        # === VOLUMEN (2) ===
        
        # OBV (On Balance Volume) - normalizar usando z-score con clip
        obv = ta.obv(df["Close"], df["Volume"])
        obv_mean = obv.rolling(50).mean()
        obv_std = obv.rolling(50).std()
        result_df["OBV"] = np.clip((obv - obv_mean) / (obv_std + 1e-8), -3.0, 3.0)
        
        # CMF (Chaikin Money Flow)
        result_df["CMF"] = ta.cmf(
            df["High"], df["Low"], df["Close"], df["Volume"], length=20
        )
        
        # Forward-fill para valores NaN
        for col in ADVANCED_TECHNICAL_FEATURES:
            if col in result_df.columns:
                result_df[col] = result_df[col].ffill()
        
        logger.info(f"✅ Calculados 18 indicadores técnicos avanzados")
        
    except Exception as e:
        logger.error(f"Error calculando features técnicas avanzadas: {e}")
        # Usar valores neutros si falla
        for col in ADVANCED_TECHNICAL_FEATURES:
            if col not in result_df.columns:
                if col in ["Stochastic_K", "Stochastic_D", "MFI"]:
                    result_df[col] = 50.0
                elif col in ["Williams_R"]:
                    result_df[col] = -50.0
                elif col in ["ADX"]:
                    result_df[col] = 25.0
                else:
                    result_df[col] = 0.0
    
    return result_df


def add_advanced_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Añade 18 indicadores técnicos avanzados calculados localmente.
    
    Esta es la función principal que debes llamar desde data_pipeline.py
    para enriquecer tus datos con features técnicas que varían diariamente.
    
    Todos los indicadores son calculados con pandas_ta, sin necesidad de APIs externas.
    
    Args:
        df: DataFrame con datos OHLCV
        
    Returns:
        DataFrame con las 18 features técnicas avanzadas añadidas
        
    Example:
        >>> df = compute_features(raw_df, ...)  # Features base (9)
        >>> df = add_advanced_technical_features(df)  # +18 features técnicas
    """
    logger.info(f"Calculando 18 indicadores técnicos avanzados...")
    result_df = compute_advanced_technical_features(df)
    return result_df
