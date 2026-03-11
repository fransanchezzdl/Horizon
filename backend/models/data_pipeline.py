"""
Pipeline de datos para el modelo Horizon Predictor.

Maneja descarga de datos históricos, cálculo de features técnicas,
escalado y creación de secuencias para entrenamiento.
"""

import os
import pickle
import numpy as np
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import torch
from sklearn.preprocessing import MinMaxScaler
from typing import Tuple, Dict

from .config import (
    FEATURE_COLS,
    BASE_FEATURE_COLS,
    VOLATILE_FEATURE_COLS,
    SENTIMENT_FEATURE_COLS,
    MARKET_CONTEXT_TICKERS,
    PREDICTION_HORIZON,
    TRAIN_RATIO,
    VAL_RATIO,
    SAVED_MODELS_DIR,
    USE_SENTIMENT,
    get_feature_cols,
    get_asset_type,
)


def download_data(ticker: str) -> pd.DataFrame:
    """
    Descarga datos históricos desde Yahoo Finance desde 2018-01-01.

    Args:
        ticker: Símbolo del activo (ej: 'KO', 'TSLA', 'BTC-USD').

    Returns:
        DataFrame con columnas OHLCV y fechas como índice.

    Raises:
        ValueError: Si no se pueden descargar datos o el DataFrame está vacío.
    """
    print(f"📥 Descargando datos de {ticker} desde 2018-01-01...")
    df = yf.download(ticker, start="2018-01-01", progress=False, auto_adjust=True)

    if df.empty:
        raise ValueError(f"No se pudieron descargar datos para {ticker}.")

    # Aplanar MultiIndex si yfinance lo devuelve
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    print(f"✅ Datos descargados: {len(df)} filas para {ticker}.")
    return df


def compute_features(
    df: pd.DataFrame,
    include_market_context: bool = False,
    ticker: str = "",
) -> pd.DataFrame:
    """
    Calcula las features técnicas del modelo.

    Features base calculadas (9):
        1. Close         — precio de cierre
        2. Volume        — volumen de transacciones
        3. RSI(14)       — Relative Strength Index
        4. MACD          — línea MACD (12, 26, 9)
        5. EMA(50)       — Media Móvil Exponencial 50 períodos
        6. Bollinger_PctB— Bollinger Bands %B
        7. ATR(14)       — Average True Range
        8. Log_Return    — retorno logarítmico diario
        9. Volume_Ratio  — ratio volumen vs media móvil 20 días

    Features adicionales de contexto de mercado (2, solo si include_market_context=True):
        10. VIX_Close    — precio de cierre del índice VIX
        11. NASDAQ_Return — retorno logarítmico diario del NASDAQ

    Features de sentimiento (3, solo si USE_SENTIMENT=True y ticker proporcionado):
        12. sentiment_score      — sentimiento medio [-1.0, +1.0]
        13. sentiment_magnitude  — confianza media [0.0, 1.0]
        14. news_volume          — número de artículos

    Args:
        df: DataFrame con columnas OHLCV (Open, High, Low, Close, Volume).
        include_market_context: Si True, añade VIX_Close y NASDAQ_Return.
        ticker: Símbolo del activo para obtener sentimiento (opcional).

    Returns:
        DataFrame con las features calculadas, sin NaNs.
    """
    df = df.copy()

    # RSI de 14 períodos
    rsi = ta.rsi(df["Close"], length=14)
    df["RSI"] = rsi

    # MACD: línea MACD (diferencia EMA12 - EMA26)
    macd_df = ta.macd(df["Close"], fast=12, slow=26, signal=9)
    df["MACD"] = macd_df["MACD_12_26_9"]

    # EMA de 50 períodos
    df["EMA"] = ta.ema(df["Close"], length=50)

    # Bollinger Bands %B (búsqueda robusta de columna para compatibilidad con pandas_ta)
    bbands = ta.bbands(df["Close"], length=20, std=2)
    bbp_col = [col for col in bbands.columns if col.startswith("BBP")]
    if not bbp_col:
        raise ValueError(
            f"No se encontró la columna BBP en Bollinger Bands. "
            f"Columnas disponibles: {list(bbands.columns)}"
        )
    df["Bollinger_PctB"] = bbands[bbp_col[0]]

    # ATR de 14 períodos
    df["ATR"] = ta.atr(df["High"], df["Low"], df["Close"], length=14)

    # Retorno logarítmico diario
    df["Log_Return"] = np.log(df["Close"] / df["Close"].shift(1))

    # Ratio de volumen (volumen / media móvil 20 días)
    df["Volume_Ratio"] = df["Volume"] / df["Volume"].rolling(20).mean()

    # Contexto de mercado: VIX y NASDAQ (solo para activos volátiles)
    if include_market_context:
        start_date = df.index.min().strftime("%Y-%m-%d")
        end_date = df.index.max().strftime("%Y-%m-%d")

        vix_df = yf.download(
            MARKET_CONTEXT_TICKERS["VIX"],
            start=start_date,
            end=end_date,
            progress=False,
            auto_adjust=True,
        )
        nasdaq_df = yf.download(
            MARKET_CONTEXT_TICKERS["NASDAQ"],
            start=start_date,
            end=end_date,
            progress=False,
            auto_adjust=True,
        )

        # Aplanar MultiIndex si yfinance lo devuelve
        if isinstance(vix_df.columns, pd.MultiIndex):
            vix_df.columns = vix_df.columns.get_level_values(0)
        if isinstance(nasdaq_df.columns, pd.MultiIndex):
            nasdaq_df.columns = nasdaq_df.columns.get_level_values(0)

        vix_close = vix_df["Close"].rename("VIX_Close")
        nasdaq_return = np.log(
            nasdaq_df["Close"] / nasdaq_df["Close"].shift(1)
        ).rename("NASDAQ_Return")

        df = df.join(vix_close, how="left").join(nasdaq_return, how="left")
        # Rellenar hacia adelante fechas sin datos (ej: fines de semana para crypto)
        df["VIX_Close"] = df["VIX_Close"].ffill()
        df["NASDAQ_Return"] = df["NASDAQ_Return"].ffill()

    # Eliminar filas con NaN producidos por los indicadores
    df.dropna(inplace=True)

    # Seleccionar columnas técnicas finales
    if include_market_context:
        tech_df = df[VOLATILE_FEATURE_COLS].copy()
    else:
        tech_df = df[BASE_FEATURE_COLS].copy()

    # Añadir features de sentimiento si está habilitado
    if USE_SENTIMENT and ticker:
        try:
            from .sentiment import compute_historical_sentiment
            start_date = tech_df.index.min().strftime("%Y-%m-%d")
            end_date = tech_df.index.max().strftime("%Y-%m-%d")
            sentiment_df = compute_historical_sentiment(ticker, start_date, end_date)
            # Reindexar al índice de tech_df y rellenar hacia adelante
            # con límite de 5 días para no propagar sentimiento obsoleto
            sentiment_df = sentiment_df.reindex(tech_df.index)
            sentiment_df = sentiment_df.ffill(limit=5).fillna(
                {"sentiment_score": 0.0, "sentiment_magnitude": 0.0, "news_volume": 0}
            )
            for col in SENTIMENT_FEATURE_COLS:
                tech_df[col] = sentiment_df[col].values
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "No se pudieron calcular features de sentimiento para %s: %s. "
                "Usando valores neutros.",
                ticker, exc
            )
            for col in SENTIMENT_FEATURE_COLS:
                if col == "news_volume":
                    tech_df[col] = 0
                else:
                    tech_df[col] = 0.0

    return tech_df


def compute_target(df: pd.DataFrame, horizon: int = PREDICTION_HORIZON) -> pd.Series:
    """
    Calcula el target: retorno logarítmico acumulado a 'horizon' días.

    target_t = log(Close_{t+horizon} / Close_t)

    Args:
        df: DataFrame que contiene la columna 'Close'.
        horizon: Número de días de trading hacia adelante (default: 5).

    Returns:
        Serie con el retorno acumulado por fila.
    """
    target = np.log(df["Close"].shift(-horizon) / df["Close"])
    return target


def create_sequences(
    data: np.ndarray,
    targets: np.ndarray,
    window_size: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Crea secuencias con ventana deslizante.

    Args:
        data: Array de features escaladas [n_samples, n_features].
        targets: Array de targets [n_samples].
        window_size: Tamaño de la ventana temporal.

    Returns:
        Tupla (X, y) donde:
            X: [n_sequences, window_size, n_features]
            y: [n_sequences]
    """
    X, y = [], []
    for i in range(len(data) - window_size):
        X.append(data[i : i + window_size])
        y.append(targets[i + window_size])
    return np.array(X), np.array(y)


def prepare_data(ticker: str, config: dict) -> dict:
    """
    Descarga datos, calcula features, escala y crea tensores listos para entrenar.

    Realiza el split cronológico: 70% train / 15% validación / 15% test.
    El scaler se ajusta SOLO con datos de entrenamiento y se guarda en disco.

    Args:
        ticker: Símbolo del activo.
        config: Diccionario de configuración (de get_config()).

    Returns:
        Diccionario con:
            - X_train, y_train: tensores de entrenamiento
            - X_val, y_val: tensores de validación
            - X_test, y_test: tensores de test
            - scaler: MinMaxScaler ajustado
            - dates_test: fechas del conjunto de test
            - close_test: precios de cierre reales del test
    """
    window_size = config["window_size"]

    # 1. Descargar y calcular features
    raw_df = download_data(ticker)
    include_market_context = get_asset_type(ticker) == "volatile"
    feat_df = compute_features(
        raw_df,
        include_market_context=include_market_context,
        ticker=ticker,
    )

    feature_cols = get_feature_cols(ticker)

    # 2. Calcular target (retorno a 5 días) y eliminar NaNs resultantes
    target = compute_target(feat_df)
    feat_df = feat_df.copy()
    feat_df["_target"] = target
    feat_df.dropna(inplace=True)

    targets_array = feat_df["_target"].values
    features_array = feat_df[feature_cols].values
    dates = feat_df.index
    close_prices = feat_df["Close"].values

    n = len(features_array)
    train_end = int(n * TRAIN_RATIO)
    val_end = int(n * (TRAIN_RATIO + VAL_RATIO))

    # 3. Split cronológico ANTES de escalar
    train_features = features_array[:train_end]
    val_features = features_array[train_end:val_end]
    test_features = features_array[val_end:]

    train_targets = targets_array[:train_end]
    val_targets = targets_array[train_end:val_end]
    test_targets = targets_array[val_end:]

    dates_test = dates[val_end:]
    close_test = close_prices[val_end:]

    # 4. Escalar features: fit solo en train
    scaler = MinMaxScaler(feature_range=(0, 1))
    train_scaled = scaler.fit_transform(train_features)
    val_scaled = scaler.transform(val_features)
    test_scaled = scaler.transform(test_features)

    # 5. Guardar scaler en disco
    os.makedirs(SAVED_MODELS_DIR, exist_ok=True)
    scaler_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_scaler.pkl")
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)
    print(f"💾 Scaler guardado en {scaler_path}")

    # 6. Crear secuencias con ventana deslizante
    X_train, y_train = create_sequences(train_scaled, train_targets, window_size)
    X_val, y_val = create_sequences(val_scaled, val_targets, window_size)
    X_test, y_test = create_sequences(test_scaled, test_targets, window_size)

    # 7. Convertir a tensores PyTorch
    def to_tensors(X, y):
        return (
            torch.from_numpy(X).float(),
            torch.from_numpy(y).float().unsqueeze(1),
        )

    X_train_t, y_train_t = to_tensors(X_train, y_train)
    X_val_t, y_val_t = to_tensors(X_val, y_val)
    X_test_t, y_test_t = to_tensors(X_test, y_test)

    print(
        f"📊 Split: train={len(X_train_t)}, val={len(X_val_t)}, test={len(X_test_t)} secuencias."
    )

    return {
        "X_train": X_train_t,
        "y_train": y_train_t,
        "X_val": X_val_t,
        "y_val": y_val_t,
        "X_test": X_test_t,
        "y_test": y_test_t,
        "scaler": scaler,
        "dates_test": dates_test,
        "close_test": close_test,
    }


def load_scaler(ticker: str) -> MinMaxScaler:
    """
    Carga el scaler guardado para un ticker dado.

    Args:
        ticker: Símbolo del activo.

    Returns:
        MinMaxScaler ajustado.

    Raises:
        FileNotFoundError: Si el archivo del scaler no existe.
    """
    scaler_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_scaler.pkl")
    if not os.path.exists(scaler_path):
        raise FileNotFoundError(
            f"Scaler no encontrado para {ticker}: {scaler_path}"
        )
    with open(scaler_path, "rb") as f:
        scaler = pickle.load(f)
    return scaler
