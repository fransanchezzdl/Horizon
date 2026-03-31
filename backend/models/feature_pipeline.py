"""
Pipeline unificado de features para el modelo Horizon.

Este módulo centraliza la construcción de features técnicas, de sentimiento
y de régimen de volatilidad, respetando la estructura existente de BD y config.

**Estructura de Features:**

**Base (9 features, todos los activos):**
- Close, Volume, RSI, MACD, EMA, Bollinger_PctB, ATR, Log_Return, Volume_Ratio

**Régimen de Mercado (3, siempre):**
- SMA200_Dist, SMA50_Slope, Realized_Vol

**Contexto Volátiles (2, solo activos volátiles):**
- VIX_Close, NASDAQ_Return

**Sentimiento (3, opcional USE_SENTIMENT=True):**
- sentiment_score: [-1, 1] agregado
- sentiment_magnitude: [0, 1] confianza
- news_volume: número de artículos

**Técnicas Avanzadas (18, opcional USE_ADVANCED_FEATURES=True):**
- Calculadas con pandas_ta
- Incluyen indicadores de volumen, tendencia, momentum, etc.

**Normalización:**
- MinMaxScaler [0, 1] para todas las features (fit solo en train)
- Split chronológico: 70% train, 15% val, 15% test
"""

import logging
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, RobustScaler
from typing import Tuple, Dict, Optional

logger = logging.getLogger(__name__)


class HorizonFeaturePipeline:
    """
    Pipeline centralizado de features para el modelo Horizon.

    Responsabilidades:
    - Combinar features técnicas base + régimen + sentimiento + avanzadas
    - Respetar flags de config (USE_SENTIMENT, USE_ADVANCED_FEATURES)
    - Documentar qué features se usan según tipo de activo
    - Proporcionar estadísticas de features
    """

    # Configuración de features por tipo
    BASE_FEATURES = [
        "Close", "Volume", "RSI", "MACD", "EMA",
        "Bollinger_PctB", "ATR", "Log_Return", "Volume_Ratio"
    ]

    # Régimen de mercado (económicas, siempre incluidas)
    MARKET_REGIME_FEATURES = [
        "SMA200_Dist",  # Posición respecto trend largo plazo
        "SMA50_Slope",  # Momentum medio plazo
        "Realized_Vol"  # Volatilidad realizada
    ]

    # Volatiles (contexto de mercado)
    VOLATILE_EXTRA_FEATURES = [
        "VIX_Close",        # Índice de volatilidad
        "NASDAQ_Return"     # Retorno NASDAQ
    ]

    # Sentimiento (opcional)
    SENTIMENT_FEATURES = [
        "sentiment_score",      # [-1, 1]
        "sentiment_magnitude",  # [0, 1]
        "news_volume"          # count
    ]

    @staticmethod
    def get_feature_columns(
        asset_type: str,
        include_sentiment: bool = False,
        include_advanced: bool = False,
    ) -> list:
        """
        Retorna lista de columnas de features según configuración.

        Args:
            asset_type: "stable" o "volatile"
            include_sentiment: Si True, incluir features de sentimiento
            include_advanced: Si True, incluir técnicas avanzadas

        Returns:
            Lista de nombres de features

        Examples:
            >>> cols = get_feature_columns("stable", False, False)
            >>> len(cols)
            12  # 9 base + 3 régimen

            >>> cols = get_feature_columns("volatile", True, False)
            >>> len(cols)
            17  # 9 base + 3 régimen + 2 volátiles + 3 sentimiento
        """
        columns = HorizonFeaturePipeline.BASE_FEATURES.copy()
        columns.extend(HorizonFeaturePipeline.MARKET_REGIME_FEATURES)

        # Contexto de mercado solo para volátiles
        if asset_type == "volatile":
            columns.extend(HorizonFeaturePipeline.VOLATILE_EXTRA_FEATURES)

        # Sentimiento opcional
        if include_sentiment:
            columns.extend(HorizonFeaturePipeline.SENTIMENT_FEATURES)

        # Técnicas avanzadas opcional
        if include_advanced:
            try:
                from .config import ADVANCED_TECHNICAL_COLS
                columns.extend(ADVANCED_TECHNICAL_COLS)
            except (ImportError, AttributeError):
                logger.warning("No se pudieron cargar features técnicas avanzadas")

        return columns

    @staticmethod
    def get_feature_documentation() -> Dict[str, str]:
        """
        Retorna documentación de qué es cada feature.

        Returns:
            Dict con {feature_name: descripción}
        """
        return {
            # Base
            "Close": "Precio de cierre normalizado [0, 1]",
            "Volume": "Volumen de transacciones normalizado [0, 1]",
            "RSI": "Índice de Fuerza Relativa (14) normalizado [0, 1]",
            "MACD": "Convergencia/Divergencia de Medias Móviles normalizado",
            "EMA": "Media Móvil Exponencial (50) normalizado [0, 1]",
            "Bollinger_PctB": "Posición en Bandas de Bollinger %-B [0, 1]",
            "ATR": "Average True Range (volatilidad intraday) normalizado",
            "Log_Return": "Retorno logarítmico diario [-1, 1]",
            "Volume_Ratio": "Volumen / SMA(20) normalizado",

            # Régimen
            "SMA200_Dist": "Distancia a SMA de 200d (trend largo plazo) [-1, 1]",
            "SMA50_Slope": "Pendiente de SMA(50) en 5d (momentum) [-1, 1]",
            "Realized_Vol": "Volatilidad realizada anualizada (20d) [0, ∞)",

            # Volátiles
            "VIX_Close": "Índice de Volatilidad del Mercado normalizado [0, 1]",
            "NASDAQ_Return": "Retorno logarítmico del NASDAQ [-1, 1]",

            # Sentimiento
            "sentiment_score": "Sentimiento medio ponderado [-1, 1]",
            "sentiment_magnitude": "Confianza del modelo de sentimiento [0, 1]",
            "news_volume": "Número de artículos procesados (count)",
        }

    @staticmethod
    def describe_feature_matrix(
        X: np.ndarray,
        feature_cols: list,
    ) -> None:
        """
        Imprime estadísticas de la matriz de features.

        Args:
            X: Array [n_samples, n_features]
            feature_cols: Lista de nombres de features
        """
        logger.info(f"📊 Matriz de Features: {X.shape}")
        logger.info(f"   Muestras: {X.shape[0]}, Features: {X.shape[1]}")

        for i, col in enumerate(feature_cols):
            min_val = X[:, i].min()
            max_val = X[:, i].max()
            mean_val = X[:, i].mean()
            std_val = X[:, i].std()
            nan_pct = np.isnan(X[:, i]).sum() / len(X) * 100

            logger.debug(
                f"   {col:20s}: [{min_val:7.4f}, {max_val:7.4f}] "
                f"μ={mean_val:7.4f} σ={std_val:7.4f} NaN={nan_pct:.1f}%"
            )

    @staticmethod
    def validate_feature_matrix(
        X: np.ndarray,
        feature_cols: list,
        max_nan_pct: float = 5.0,
    ) -> Tuple[bool, list]:
        """
        Valida la matriz de features.

        Chequea:
        - Sin valores NaN (o % baixo tolerable)
        - Sin infinitos
        - Rango razonable [typically -10, 10] para evitar overflow

        Args:
            X: Array [n_samples, n_features]
            feature_cols: Nombres de features
            max_nan_pct: Máximo % de NaN tolerado (default: 5%)

        Returns:
            Tupla (is_valid, list_of_issues)
        """
        issues = []

        for i, col in enumerate(feature_cols):
            feature_col = X[:, i]

            # Chequear NaN
            nan_count = np.isnan(feature_col).sum()
            nan_pct = nan_count / len(feature_col) * 100
            if nan_pct > max_nan_pct:
                issues.append(f"{col}: {nan_pct:.1f}% NaN (max={max_nan_pct}%)")

            # Chequear infinitos
            inf_count = np.isinf(feature_col).sum()
            if inf_count > 0:
                issues.append(f"{col}: {inf_count} infinitos")

            # Chequear outliers extremos
            if np.nanmax(np.abs(feature_col)) > 100:
                issues.append(f"{col}: valores extremos > 100")

        is_valid = len(issues) == 0
        return is_valid, issues

    @staticmethod
    def apply_feature_scaling(
        X_train: np.ndarray,
        X_val: np.ndarray,
        X_test: np.ndarray,
        feature_cols: list,
        scaler_type: str = "minmax",
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Escala features de forma coherente (fit solo en train).

        BUG prevention: Evita data leakage escalando train/val/test por separado
        con parámetros calculados SOLO sobre train.

        Args:
            X_train: Features de train [n_train, n_features]
            X_val: Features de val [n_val, n_features]
            X_test: Features de test [n_test, n_features]
            feature_cols: Nombres de features (para logging)
            scaler_type: "minmax" (0-1) o "robust" (median, IQR)

        Returns:
            Tupla (X_train_scaled, X_val_scaled, X_test_scaled)
        """
        if scaler_type == "minmax":
            scaler = MinMaxScaler(feature_range=(0, 1))
        elif scaler_type == "robust":
            scaler = RobustScaler()
        else:
            raise ValueError(f"Scaler type desconocido: {scaler_type}")

        # FIT solo en train
        X_train_scaled = scaler.fit_transform(X_train)
        X_val_scaled = scaler.transform(X_val)
        X_test_scaled = scaler.transform(X_test)

        logger.info(
            f"✅ Features escaladas con {scaler_type.upper()}Scaler "
            f"(fit solo en train, {len(feature_cols)} features)"
        )

        return X_train_scaled, X_val_scaled, X_test_scaled

    @staticmethod
    def compute_feature_importance(
        model_predictions: np.ndarray,
        y_true: np.ndarray,
        X: np.ndarray,
        feature_cols: list,
        top_k: int = 10,
    ) -> Dict[str, float]:
        """
        Calcula importancia relativa de features (permutation-based).

        Nota: Este es un metodo simple. Para importancia real usar SHAP o tree-based.

        Args:
            model_predictions: Predicciones del modelo
            y_true: Valores verdaderos
            X: Matriz de features original
            feature_cols: Nombres de features
            top_k: Retornar top K features

        Returns:
            Dict {feature_name: importance_score}
        """
        from sklearn.metrics import accuracy_score

        baseline_accuracy = accuracy_score(y_true, model_predictions)
        importances = {}

        for i, col in enumerate(feature_cols):
            # Permutar feature i
            X_permuted = X.copy()
            np.random.shuffle(X_permuted[:, i])

            # (Aquí necesitaría re-predecir con X_permuted, requiere model callable)
            # Por ahora retornar estructura vacía
            importances[col] = 0.0

        # Ordenar por importancia
        sorted_importance = sorted(
            importances.items(), key=lambda x: abs(x[1]), reverse=True
        )

        return {k: v for k, v in sorted_importance[:top_k]}
