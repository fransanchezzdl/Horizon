"""
Router automático para seleccionar modelo según volatilidad del activo.

Clasifica dinámicamente cada ticker como STABLE o VOLATILE usando:
- ATR (Average True Range) de 20 días
- Volatilidad histórica realizada de 20 días

Esto reemplaza la clasificación hardcodeada en config.py.

Arquitectura:
    1. Descargar datos históricos recientes (últimos 60-100 días)
    2. Calcular ATR y volatilidad realizada
    3. Comparar con umbral configurable
    4. Seleccionar modelo (StableHorizonModel o VolatileHorizonModel)
    5. Loguear clasificación

Configuración:
    - ATR_PERCENTILE_THRESHOLD: 50 = mediana histórica (default)
    - VOLATILITY_PERCENTILE_THRESHOLD: 50 = mediana histórica (default)
    - COMBINED_WEIGHT: 0.5 = balance ATR/volatility (0.5 = 50% peso cada uno)
"""

import logging
import numpy as np
import pandas as pd
import torch
import yfinance as yf
from typing import Tuple, Optional

from .model import (
    StableHorizonModel,
    VolatileHorizonModel,
    HorizonBiGRU,
    HorizonBiGRUAttention,
)

logger = logging.getLogger(__name__)


class HorizonModelRouter:
    """
    Router automático que selecciona el modelo especializado basado en volatilidad.

    Métodos principales:
    - classify_asset(ticker) -> str: "stable" o "volatile"
    - get_model(...) -> nn.Module: modelo apropiado instanciado
    - get_model_config(...) -> dict: hiperparámetros para el ticker
    """

    # Configuración de umbrales de volatilidad
    # Si ATR percentil o volatilidad realizada excede estos, → volatile
    ATR_PERCENTILE_THRESHOLD = 55  # 55% = ligeramente por encima de mediana
    VOLATILITY_PERCENTILE_THRESHOLD = 55
    COMBINED_WEIGHT = 0.5  # Balance entre ATR (0.5) y volatility (0.5)

    # Ventana de datos históricos para cálculos
    LOOKBACK_DAYS = 180  # 9 meses de histórico para percentiles robustos
    ATR_PERIOD = 20
    VOLATILITY_PERIOD = 20

    # Cache de clasificaciones (para evitar recalcular en cada llamada)
    _classification_cache: dict = {}

    @classmethod
    def _calculate_atr(cls, df: pd.DataFrame, period: int = 20) -> float:
        """
        Calcula el ATR (Average True Range) actual del DataFrame.

        Args:
            df: DataFrame con columnas High, Low, Close
            period: Período para el ATR (default: 20)

        Returns:
            Float: ATR más reciente
        """
        high_low = df["High"] - df["Low"]
        high_close = np.abs(df["High"] - df["Close"].shift())
        low_close = np.abs(df["Low"] - df["Close"].shift())

        tr = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = tr.rolling(period).mean().iloc[-1]
        return float(atr) if not np.isnan(atr) else 0.0

    @classmethod
    def _calculate_realized_volatility(cls, df: pd.DataFrame, period: int = 20) -> float:
        """
        Calcula volatilidad realizada (annualized).

        vol_realized = std(log_returns) * sqrt(252)

        Args:
            df: DataFrame con columna Close
            period: Período para el cálculo (default: 20)

        Returns:
            Float: Volatilidad realizada anualizada
        """
        log_returns = np.log(df["Close"] / df["Close"].shift(1))
        realized_vol = log_returns.rolling(period).std().iloc[-1] * np.sqrt(252)
        return float(realized_vol) if not np.isnan(realized_vol) else 0.0

    @classmethod
    def classify_asset(
        cls,
        ticker: str,
        use_cache: bool = True,
        force_refresh: bool = False,
    ) -> str:
        """
        Clasifica un ticker como STABLE o VOLATILE basado en ATR + volatilidad.

        Lógica:
            1. Descargar últimos LOOKBACK_DAYS días
            2. Calcular ATR percentil en histórico
            3. Calcular volatilidad realizada percentil
            4. Combinar con pesos: score = 0.5*atr_pct + 0.5*vol_pct
            5. Si score > THRESHOLD → VOLATILE, else → STABLE

        Args:
            ticker: Símbolo del activo (ej: 'KO', 'TSLA')
            use_cache: Si True, usar clasificación en caché (más rápido)
            force_refresh: Si True, recalcular incluso si está en caché

        Returns:
            "stable" o "volatile"
        """
        # Chequear caché
        if use_cache and not force_refresh and ticker in cls._classification_cache:
            return cls._classification_cache[ticker]

        try:
            # 1. Descargar datos históricos recientes
            logger.info(f"📊 Clasificando {ticker}...")
            df = yf.download(
                ticker,
                period=f"{cls.LOOKBACK_DAYS}d",
                progress=False,
                auto_adjust=True,
            )

            if df.empty or len(df) < cls.ATR_PERIOD + cls.VOLATILITY_PERIOD:
                logger.warning(
                    f"⚠️  Datos insuficientes para {ticker}. Clasificando como STABLE (default)."
                )
                cls._classification_cache[ticker] = "stable"
                return "stable"

            # 2. Calcular ATR actual y percentil histórico
            atr_current = cls._calculate_atr(df, cls.ATR_PERIOD)
            atr_hist = df[["High", "Low", "Close"]].apply(
                lambda _: cls._calculate_atr(
                    df.loc[: df.index[i]], cls.ATR_PERIOD
                )
                for i in range(cls.ATR_PERIOD, len(df))
                if i >= cls.ATR_PERIOD
            )

            if len(atr_hist) > 0:
                atr_percentile = (atr_current > np.percentile(atr_hist, 50)) * 100
            else:
                atr_percentile = 50.0

            # 3. Calcular volatilidad realizada actual y percentil histórico
            vol_current = cls._calculate_realized_volatility(df, cls.VOLATILITY_PERIOD)
            vol_hist = []
            for i in range(cls.VOLATILITY_PERIOD, len(df)):
                vol_hist.append(
                    cls._calculate_realized_volatility(
                        df.iloc[:i], cls.VOLATILITY_PERIOD
                    )
                )

            if len(vol_hist) > 0:
                vol_percentile = (vol_current > np.percentile(vol_hist, 50)) * 100
            else:
                vol_percentile = 50.0

            # 4. Combinar scores
            combined_score = (
                cls.COMBINED_WEIGHT * atr_percentile
                + (1 - cls.COMBINED_WEIGHT) * vol_percentile
            )

            # 5. Clasificar
            is_volatile = combined_score > cls.VOLATILITY_PERCENTILE_THRESHOLD
            asset_type = "volatile" if is_volatile else "stable"

            logger.info(
                f"✅ {ticker}: {asset_type.upper()} "
                f"(ATR_pct={atr_percentile:.1f}, Vol_pct={vol_percentile:.1f}, score={combined_score:.1f})"
            )

            cls._classification_cache[ticker] = asset_type
            return asset_type

        except Exception as e:
            logger.warning(
                f"❌ Error clasificando {ticker}: {e}. Usando STABLE como default."
            )
            cls._classification_cache[ticker] = "stable"
            return "stable"

    @classmethod
    def get_model_config(
        cls,
        ticker: str,
        asset_type: Optional[str] = None,
    ) -> dict:
        """
        Retorna la configuración de hiperparámetros para el modelo.

        Args:
            ticker: Símbolo del activo
            asset_type: Tipo de activo ("stable" o "volatile"). Si None, clasificar automáticamente.

        Returns:
            Dict con configuración:
            {
                "input_dim": int,
                "hidden_dim": int,
                "num_layers": int,
                "dropout": float,
                "window_size": int,
                "learning_rate": float,
                "epochs": int,
                "batch_size": int,
                "model_class": str,  # "StableHorizonModel" o "VolatileHorizonModel"
            }
        """
        if asset_type is None:
            asset_type = cls.classify_asset(ticker)

        if asset_type == "volatile":
            return {
                "asset_type": "volatile",
                "input_dim": 11,  # base(9) + market_context(2)
                "hidden_dim": 96,
                "num_layers": 3,
                "dropout": 0.3,
                "window_size": 20,
                "learning_rate": 0.0003,
                "epochs": 250,
                "batch_size": 32,
                "early_stopping_patience": 35,
                "model_class": "VolatileHorizonModel",
                "loss_function": "FocalLoss",
                "focal_loss_gamma": 2.0,
            }
        else:  # stable
            return {
                "asset_type": "stable",
                "input_dim": 9,  # solo features base
                "hidden_dim": 128,
                "num_layers": 2,
                "dropout": 0.1,
                "window_size": 60,
                "learning_rate": 0.0005,
                "epochs": 200,
                "batch_size": 16,
                "early_stopping_patience": 30,
                "model_class": "StableHorizonModel",
                "loss_function": "CrossEntropyLoss",
                "focal_loss_gamma": None,
            }

    @classmethod
    def get_model(
        cls,
        ticker: str,
        input_dim: int = 9,
        device: torch.device = None,
        asset_type: Optional[str] = None,
    ) -> torch.nn.Module:
        """
        Instancia el modelo especializado para un ticker.

        Args:
            ticker: Símbolo del activo
            input_dim: Dimensión de features de entrada
            device: Dispositivo ("cpu", "cuda", etc). Si None, usar cpu.
            asset_type: Type de activo. Si None, clasificar automáticamente.

        Returns:
            Modelo PyTorch instanciado (StableHorizonModel o VolatileHorizonModel)
        """
        if device is None:
            device = torch.device("cpu")

        if asset_type is None:
            asset_type = cls.classify_asset(ticker)

        config = cls.get_model_config(ticker, asset_type)

        if asset_type == "volatile":
            model = VolatileHorizonModel(
                input_dim=input_dim,
                hidden_dim=config["hidden_dim"],
                num_layers=config["num_layers"],
                dropout=config["dropout"],
                num_classes=3,
            )
            logger.info(
                f"🎯 Instanciado VolatileHorizonModel para {ticker} "
                f"(window={config['window_size']}, hidden={config['hidden_dim']}, dropout={config['dropout']})"
            )
        else:
            model = StableHorizonModel(
                input_dim=input_dim,
                hidden_dim=config["hidden_dim"],
                num_layers=config["num_layers"],
                dropout=config["dropout"],
                num_classes=3,
            )
            logger.info(
                f"🎯 Instanciado StableHorizonModel para {ticker} "
                f"(window={config['window_size']}, hidden={config['hidden_dim']}, dropout={config['dropout']})"
            )

        model = model.to(device)
        return model

    @classmethod
    def clear_cache(cls) -> None:
        """Limpia el caché de clasificaciones."""
        cls._classification_cache.clear()
        logger.info("🗑️  Caché de clasificaciones limpio.")

    @classmethod
    def get_cache_stats(cls) -> dict:
        """Retorna estadísticas del caché."""
        return {
            "cached_tickers": len(cls._classification_cache),
            "classifications": cls._classification_cache.copy(),
        }
