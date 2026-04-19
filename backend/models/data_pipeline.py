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
import logging
from sklearn.preprocessing import MinMaxScaler
from typing import Tuple, Dict

logger = logging.getLogger(__name__)

from .config import (
    FEATURE_COLS,
    BASE_FEATURE_COLS,
    VOLATILE_FEATURE_COLS,
    SENTIMENT_FEATURE_COLS,
    MACRO_COMMODITY_COLS,
    ADVANCED_TECHNICAL_COLS,
    MARKET_CONTEXT_TICKERS,
    PREDICTION_HORIZON,
    TRAIN_RATIO,
    VAL_RATIO,
    SAVED_MODELS_DIR,
    USE_SENTIMENT,
    USE_ADVANCED_FEATURES,
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
    print(f"[Downloading {ticker} from 2018-01-01...]")
    df = yf.download(ticker, start="2018-01-01", progress=False, auto_adjust=True)

    if df.empty:
        raise ValueError(f"No se pudieron descargar datos para {ticker}.")

    # Aplanar MultiIndex si yfinance lo devuelve
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    print(f"[OK] Datos descargados: {len(df)} filas para {ticker}.")
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

    # === FEATURES DE RÉGIMEN DE MERCADO (3) ===
    # Estas features dan contexto sobre el estado macro del mercado,
    # algo que los indicadores técnicos de corto plazo no capturan.

    # 1. Posición respecto a SMA200: ¿estamos en tendencia alcista o bajista?
    sma200 = df["Close"].rolling(200).mean()
    df["SMA200_Dist"] = (df["Close"] - sma200) / sma200  # % de distancia normalizado

    # 2. Pendiente de SMA50: momentum de medio plazo (¿la tendencia acelera o frena?)
    sma50 = df["Close"].rolling(50).mean()
    df["SMA50_Slope"] = sma50.diff(5) / sma50.shift(5)  # cambio % en 5 días

    # 3. Volatilidad realizada 20 días: régimen de volatilidad actual
    df["Realized_Vol"] = df["Log_Return"].rolling(20).std() * (252 ** 0.5)  # anualizada

    # 4. Régimen de mercado discreto (−1/0/+1) basado en SMA200 + zona neutra ±2%
    #    +1 = uptrend  (precio > SMA200 * 1.02): señal técnica más fiable al alza
    #    -1 = downtrend(precio < SMA200 * 0.98): señal técnica más fiable a la baja
    #     0 = neutro   (precio dentro de ±2% de SMA200): zona de incertidumbre
    #
    #    SHAP puede interpretar esta feature igual que cualquier otra continua/ordinal.
    #    El modelo aprende implícitamente a condicionar sus predicciones al régimen,
    #    sin necesidad de reglas hard-coded externas.
    #
    #    Referencia: Faber (2007) "A Quantitative Approach to Tactical Asset Allocation"
    df["SMA200_Regime"] = np.where(
        df["Close"] > sma200 * 1.02,  1.0,   # uptrend
        np.where(
            df["Close"] < sma200 * 0.98, -1.0,  # downtrend
            0.0                                  # neutro
        )
    )
    # Rellenar NaN del warmup de SMA200 con 0 (neutro)
    df["SMA200_Regime"] = df["SMA200_Regime"].fillna(0.0)
    # === PHASE 2 FEATURES (12 nuevos indicadores técnicos) ===
    # Se agregan después de los indicadores base para tener acceso a OHLCV
    try:
        from .phase2_features import Phase2FeaturesBuilder
        logger.info("[Phase2] Agregando 12 nuevos indicadores técnicos...")
        df = Phase2FeaturesBuilder.build_phase2_features(df)
        logger.info("[Phase2] ✅ 12 indicadores agregados: momentum_5d, rsi_14, macd_signal, bbands_pct, atr_14, obv_momentum, volume_sma_ratio, high_low_ratio, close_range_pct, roc_10, volatility_std, price_acceleration")
    except Exception as e:
        logger.warning(f"[Phase2] No se pudieron agregar indicadores Phase 2: {str(e)}. Continuando sin ellos.")
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

    # Añadir features técnicas avanzadas ANTES de dropna() si está habilitado
    if USE_ADVANCED_FEATURES:
        try:
            from .advanced_features import add_advanced_technical_features
            df = add_advanced_technical_features(df)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "No se pudieron calcular features técnicas avanzadas: %s. "
                "Usando valores por defecto.",
                exc
            )
            # Añadir valores por defecto para todas las features avanzadas
            for col in ADVANCED_TECHNICAL_COLS:
                if col in ["Stochastic_K", "Stochastic_D", "MFI"]:
                    df[col] = 50.0
                elif col in ["Williams_R"]:
                    df[col] = -50.0
                elif col in ["ADX"]:
                    df[col] = 25.0
                else:
                    df[col] = 0.0

    # Eliminar filas con NaN producidos por los indicadores
    df.dropna(inplace=True)

    # === FEATURES DE SENTIMIENTO (3) ===
    # Se agregan DESPUÉS de dropna porque vienen de fuente externa (Alpha Vantage + DistilRoBERTa)
    if USE_SENTIMENT and ticker:
        try:
            from . import sentiment
            print(f"[*] Agregando features de sentimiento para {ticker} (Alpha Vantage + DistilRoBERTa)...")
            
            # Get date range from dataframe
            start_date = df.index.min().strftime("%Y-%m-%d")
            end_date = df.index.max().strftime("%Y-%m-%d")
            
            # Compute historical sentiment using Alpha Vantage + DistilRoBERTa
            sentiment_df = sentiment.compute_historical_sentiment(ticker, start_date, end_date)
            
            if not sentiment_df.empty:
                # Left join para preservar todas las fechas técnicas y llenar con neutrales si falta sentimiento
                df = df.join(sentiment_df, how="left")
                # Fill any missing sentiment values with neutral (0.0, 0.0, 0)
                df["sentiment_score"] = df["sentiment_score"].fillna(0.0)
                df["sentiment_magnitude"] = df["sentiment_magnitude"].fillna(0.0)
                df["news_volume"] = df["news_volume"].fillna(0).astype(int)
                print(f"[OK] Features de sentimiento agregadas: {len(df)} filas")
            else:
                print(f"[!] No sentiment data from Alpha Vantage, adding neutral values")
                df["sentiment_score"] = 0.0
                df["sentiment_magnitude"] = 0.0
                df["news_volume"] = 0
                
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "No se pudieron obtener features de sentimiento: %s. "
                "Continuando sin sentimiento.",
                exc
            )
            # Añadir valores neutros para features de sentimiento
            df["sentiment_score"] = 0.0
            df["sentiment_magnitude"] = 0.0
            df["news_volume"] = 0
        
        # === AGREGAR FEATURES MEJORADAS DE SENTIMIENTO CON LAG ===
        # Crear features temporales (lag 1-5 días) para capturar predictibilidad
        try:
            from .sentiment_improved import ImprovedSentimentAnalyzer
            
            analyzer = ImprovedSentimentAnalyzer(window_size=30)
            print(f"[*] Agregando features mejoradas de sentimiento con LAG para {ticker}...")
            
            # Asegurar que sentiment_score existe (puede ser 0.0)
            if "sentiment_score" not in df.columns:
                df["sentiment_score"] = 0.0
            
            # Calcular volatilidad si no existe
            if "volatility_std" not in df.columns:
                returns = df["Close"].pct_change()
                df["volatility_std"] = returns.rolling(window=5).std()
                df["volatility_std"].fillna(0.01, inplace=True)
            
            # Crear features de lag
            df_improved = analyzer.create_sentiment_features_with_lag(
                df, 
                sentiment_column='sentiment_score',
                volatility_column='volatility_std'
            )
            
            # Agregar nuevas features al dataframe original
            for col in analyzer.get_feature_names():
                if col in df_improved.columns:
                    df[col] = df_improved[col]
            
            print(f"[OK] {len(analyzer.get_feature_names())} features de sentimiento CON LAG agregadas")
            
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "No se pudieron crear features mejoradas de sentimiento: %s",
                exc
            )
            # Continuar si falla (features de lag no son críticos)

    # Seleccionar columnas base + avanzadas (todo lo que ya está en df)
    # Las columnas de sentimiento BÁSICAS (3) se reagregan después
    # Las columnas de sentimiento con LAG (12) se mantienen
    all_feature_cols = get_feature_cols(ticker)
    
    # Excluir SOLO los 3 features básicos de sentimiento (que se reagregacn después)
    # MANTENER los 12 lag features que ya fueron creados
    # IMPORTANTE: Filtrar SOLO features que existen en el DataFrame (algunos no se crean si include_market_context=False)
    BASIC_SENTIMENT_COLS = ["sentiment_score", "sentiment_magnitude", "news_volume"]
    non_sentiment_cols = [c for c in all_feature_cols 
                         if c not in BASIC_SENTIMENT_COLS and c not in MACRO_COMMODITY_COLS
                         and c in df.columns]  # Asegurar que la columna existe
    tech_df = df[non_sentiment_cols].copy()

    # === FEATURES MACRO PARA COMMODITIES (GC=F, SI=F) ===
    # Indicadores especializados que capturan regímenes de riesgo macro
    # DEBEN agregarse ANTES de sentiment para poder usarlas
    if ticker in ["GC=F", "SI=F"]:
        try:
            from .commodity_macro import augment_commodity_features
            tech_df = augment_commodity_features(tech_df, ticker)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "No se pudieron agregar features macro para %s: %s",
                ticker, exc
            )

    # Añadir features de sentimiento si está habilitado
    if USE_SENTIMENT and ticker:
        try:
            from .sentiment import compute_historical_sentiment
            start_date = tech_df.index.min().strftime("%Y-%m-%d")
            end_date = tech_df.index.max().strftime("%Y-%m-%d")
            sentiment_df = compute_historical_sentiment(ticker, start_date, end_date)
            sentiment_df = sentiment_df.reindex(tech_df.index)
            sentiment_df = sentiment_df.ffill(limit=5).fillna(
                {"sentiment_score": 0.0, "sentiment_magnitude": 0.0, "news_volume": 0}
            )
            # Solo agregar los 3 features BÁSICOS de sentimiento
            # Los 12 lag features ya fueron agregados en líneas 257-291
            BASIC_SENTIMENT_COLS = ["sentiment_score", "sentiment_magnitude", "news_volume"]
            for col in BASIC_SENTIMENT_COLS:
                if col not in tech_df.columns:  # Solo si no existen ya
                    tech_df[col] = sentiment_df[col].values
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "No se pudieron calcular features de sentimiento para %s: %s. "
                "Usando valores neutros.",
                ticker, exc
            )
            # Solo llenar campos BÁSICOS si no existen
            BASIC_SENTIMENT_COLS = ["sentiment_score", "sentiment_magnitude", "news_volume"]
            for col in BASIC_SENTIMENT_COLS:
                if col not in tech_df.columns:
                    if col == "news_volume":
                        tech_df[col] = 0
                    else:
                        tech_df[col] = 0.0

    return tech_df


def compute_target(df: pd.DataFrame, horizon: int = PREDICTION_HORIZON) -> pd.Series:
    """
    Calcula el target: retorno logarítmico acumulado a 'horizon' días.
    Usado internamente para calcular el threshold dinámico y las clases.
    """
    return np.log(df["Close"].shift(-horizon) / df["Close"])


def compute_class_target(
    returns: np.ndarray,
    threshold: float,
) -> np.ndarray:
    """
    Convierte retornos continuos en clases balanceadas de 3 categorías.

    Clases:
        0 → BAJISTA  (retorno < -threshold)
        1 → LATERAL  (retorno en [-threshold, +threshold])
        2 → ALCISTA  (retorno > +threshold)

    El threshold se calcula dinámicamente sobre el conjunto de train
    para garantizar que las clases estén aproximadamente balanceadas
    (cada clase ~33% del total).

    Args:
        returns:   Array de retornos logarítmicos.
        threshold: Umbral dinámico calculado con compute_dynamic_threshold().

    Returns:
        Array de enteros [0, 1, 2] con la clase de cada muestra.
    """
    classes = np.ones(len(returns), dtype=np.int64)  # default: LATERAL
    classes[returns > threshold] = 2   # ALCISTA
    classes[returns < -threshold] = 0  # BAJISTA
    return classes


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
        f"[INFO] Split: train={len(X_train_t)}, val={len(X_val_t)}, test={len(X_test_t)} secuencias."
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


def compute_dynamic_threshold(targets: np.ndarray, percentile: float = 60.0) -> float:
    """
    Calcula un threshold dinámico basado en la distribución real de retornos.

    Usa el percentil dado de los retornos absolutos del conjunto de train.
    Esto adapta el threshold a la volatilidad real del activo:
    - KO (baja vol): threshold ~0.003-0.005
    - TSLA (alta vol): threshold ~0.04-0.06
    - GC=F (media vol): threshold ~0.01-0.02

    Args:
        targets: Array de retornos logarítmicos a 5 días (solo train).
        percentile: Percentil de la distribución de |retornos|. Default: 60.

    Returns:
        Float con el threshold adaptativo.
    """
    abs_returns = np.abs(targets)
    if len(abs_returns) == 0:
        raise ValueError("Cannot compute dynamic threshold from empty targets array.")
    threshold = float(np.percentile(abs_returns, percentile))
    return threshold


def returns_to_classes(returns: np.ndarray, threshold: float) -> np.ndarray:
    """
    Convierte retornos continuos a clases balanceadas de 3 categorías.

    Clases:
        0 → BAJISTA  (retorno ≤ -threshold)
        1 → LATERAL  (retorno ∈ (-threshold, +threshold))
        2 → ALCISTA  (retorno > +threshold)

    Este cambio de regresión a clasificación es la **BUG FIX #1**,
    porque el modelo anterior (HorizonBiGRUAttention) predecía regresión
    pero se usaba como clasificación, causando 53% accuracy.

    Args:
        returns: Array de retornos logarítmicos.
        threshold: Umbral dinámico calculado sobre train.

    Returns:
        Array de enteros [0, 1, 2] con las clases.
    """
    classes = np.ones(len(returns), dtype=np.int64)  # default: LATERAL (1)
    classes[returns > threshold] = 2   # ALCISTA
    classes[returns < -threshold] = 0  # BAJISTA
    return classes


def prepare_data_multi_window(ticker: str, config: dict, window_sizes: list) -> dict:
    """
    Prepara datos una sola vez y crea secuencias para múltiples window_sizes.
    Los targets son clases (0=BAJISTA, 1=LATERAL, 2=ALCISTA) balanceadas
    usando el threshold dinámico calculado sobre train.
    """
    # 1. Descargar y calcular features UNA SOLA VEZ
    raw_df = download_data(ticker)
    include_market_context = get_asset_type(ticker) == "volatile"
    feat_df = compute_features(raw_df, include_market_context=include_market_context, ticker=ticker)
    feature_cols = get_feature_cols(ticker)

    # 2. Calcular retornos continuos y convertir a clases
    target = compute_target(feat_df)
    feat_df = feat_df.copy()
    feat_df["_target"] = target
    feat_df.dropna(inplace=True)

    returns_array = feat_df["_target"].values
    features_array = feat_df[feature_cols].values
    dates = feat_df.index
    close_prices = feat_df["Close"].values

    n = len(features_array)
    train_end = int(n * TRAIN_RATIO)
    val_end = int(n * (TRAIN_RATIO + VAL_RATIO))

    # 3. Split cronológico ANTES de escalar
    train_features = features_array[:train_end]
    val_features   = features_array[train_end:val_end]
    test_features  = features_array[val_end:]

    train_returns = returns_array[:train_end]
    val_returns   = returns_array[train_end:val_end]
    test_returns  = returns_array[val_end:]

    dates_test = dates[val_end:]
    close_test = close_prices[val_end:]

    # 4. Threshold dinámico calculado SOLO sobre train (percentil 60 de |retornos|)
    dynamic_threshold = compute_dynamic_threshold(train_returns, percentile=60.0)
    print(f"📏 Threshold dinámico: ±{dynamic_threshold:.4f} ({dynamic_threshold*100:.2f}%)")

    # Convertir retornos continuos a clases (0=BAJISTA, 1=LATERAL, 2=ALCISTA)
    # BUG FIX #1: Cambiar de regresión a clasificación pura
    train_classes = returns_to_classes(train_returns, dynamic_threshold)
    val_classes   = returns_to_classes(val_returns, dynamic_threshold)
    test_classes  = returns_to_classes(test_returns, dynamic_threshold)

    # Distribución de clases en train
    up_pct = float(np.mean(train_classes == 2)) * 100
    down_pct = float(np.mean(train_classes == 0)) * 100
    neutral_pct = float(np.mean(train_classes == 1)) * 100
    print(f"   ALCISTA: {up_pct:.1f}% | LATERAL: {neutral_pct:.1f}% | BAJISTA: {down_pct:.1f}%")

    # Calcular class weights para balancear desbalanceo
    class_counts = np.bincount(train_classes, minlength=3)
    class_weights = 1.0 / (class_counts + 1e-8)
    class_weights = class_weights / class_weights.sum() * 3  # Normalizar a suma=3
    print(f"   Class weights: {class_weights}")

    # Targets son ahora clases (enteros) para CrossEntropyLoss
    train_targets = train_classes
    val_targets   = val_classes
    test_targets  = test_classes

    # 5. Escalar UNA SOLA VEZ (fit solo en train)
    scaler = MinMaxScaler(feature_range=(0, 1))
    train_scaled = scaler.fit_transform(train_features)
    val_scaled   = scaler.transform(val_features)
    test_scaled  = scaler.transform(test_features)

    # 6. Guardar scaler y threshold
    os.makedirs(SAVED_MODELS_DIR, exist_ok=True)
    scaler_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_scaler.pkl")
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)
    print(f"💾 Scaler guardado en {scaler_path}")

    result: dict = {
        "scaler": scaler,
        "dynamic_threshold": dynamic_threshold,
        "class_weights": torch.from_numpy(class_weights).float(),  # Para CrossEntropyLoss
        # Guardar retornos continuos para inferencia de precio
        "train_returns": train_returns,
        "val_returns": val_returns,
        "test_returns": test_returns,
    }

    # 7. Crear secuencias para cada window_size
    for ws in window_sizes:
        X_train, y_train_classes = create_sequences(train_scaled, train_targets, ws)
        X_val,   y_val_classes   = create_sequences(val_scaled,   val_targets,   ws)
        X_test,  y_test_classes  = create_sequences(test_scaled,  test_targets,  ws)

        # Tensores PyTorch: y son clases (long) para CrossEntropyLoss
        X_train_t = torch.from_numpy(X_train).float()
        y_train_t = torch.from_numpy(y_train_classes).long()  # BUG FIX: long, not float
        X_val_t   = torch.from_numpy(X_val).float()
        y_val_t   = torch.from_numpy(y_val_classes).long()
        X_test_t  = torch.from_numpy(X_test).float()
        y_test_t  = torch.from_numpy(y_test_classes).long()

        # También guardar retornos continuos alineados con las secuencias
        # (para calcular precio predicho en inferencia)
        _, y_train_ret = create_sequences(train_scaled, train_returns, ws)
        _, y_val_ret   = create_sequences(val_scaled,   val_returns,   ws)
        _, y_test_ret  = create_sequences(test_scaled,  test_returns,  ws)

        print(f"[INFO] Split (ws={ws}): train={len(X_train_t)}, val={len(X_val_t)}, test={len(X_test_t)}")
        print(
            f"   Train class distribution: {np.bincount(y_train_classes[y_train_classes.size - len(y_train_t):], minlength=3)}"
        )

        result[ws] = {
            "X_train": X_train_t,
            "y_train": y_train_t,
            "X_val":   X_val_t,
            "y_val":   y_val_t,
            "X_test":  X_test_t,
            "y_test":  y_test_t,
            "y_train_returns": y_train_ret,
            "y_val_returns":   y_val_ret,
            "y_test_returns":  y_test_ret,
            "dates_test":  dates_test,
            "close_test":  close_test,
        }

    return result


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


def prepare_data_walk_forward(
    ticker: str,
    config: dict,
    window_size: int = 30,
    n_folds: int = 10,
    gap_days: int = 5,
) -> list:
    """
    Walk-Forward Validation: simula entrenamiento real dividiendo datos en ventanas.
    
    Cada fold representa un período de trading real:
    - train: últimos N días de datos históricos
    - val: siguientes M días (sin overlap)
    - test: siguientes P días (gap entre train y test)
    
    Esto elimina el optimismo de test-bias y es más realista para trading.
    
    Args:
        ticker: Símbolo del activo (ej: 'KO', 'TSLA').
        config: Config dict con parametrización.
        window_size: Window size para secuencias (default 30).
        n_folds: Número de folds a crear (default 10).
        gap_days: Días sin datos entre train y test para evitar leakage (default 5).
    
    Returns:
        Lista de N dicts, cada uno con:
        {
            'fold': int,
            'dates': dict con 'train', 'val', 'test',
            'X_train', 'y_train', 'X_val', 'y_val', 'X_test', 'y_test' (all torch tensors),
            'scaler': MinMaxScaler,
            'threshold': float,
            'class_weights': np.array,
        }
    """
    print(f"\n[*] Preparando Walk-Forward Validation para {ticker} ({n_folds} folds)...")
    
    # 1. Descargar datos
    raw_df = download_data(ticker)
    include_market_context = get_asset_type(ticker) == "volatile"
    feat_df = compute_features(raw_df, include_market_context=include_market_context, ticker=ticker)
    feature_cols = get_feature_cols(ticker)
    
    # 2. Calcular features y targets
    target = compute_target(feat_df)
    feat_df = feat_df.copy()
    feat_df["_target"] = target
    feat_df.dropna(inplace=True)
    
    returns_array = feat_df["_target"].values
    features_array = feat_df[feature_cols].values
    dates_array = feat_df.index.values
    
    n = len(features_array)
    
    # Calcular tamaños de ventana para walk-forward
    total_test_size = int(n * 0.2)  # 20% para testing en total
    fold_test_size = max(10, total_test_size // n_folds)  # Al menos 10 datos por fold
    fold_val_size = max(10, fold_test_size)  # Val = test size
    fold_train_size = max(60, n // (n_folds * 2))  # 60 datos min para train
    
    # Calcular índice inicial (para dejar datos al inicio para calibración inicial)
    min_idx = fold_train_size + fold_val_size + gap_days
    
    # Reajustar para que entren n_folds
    available_data = n - min_idx
    fold_step = max(1, available_data // (n_folds + 1))
    
    folds = []
    
    for fold_idx in range(n_folds):
        # Índices para este fold
        test_end = min_idx + (fold_idx + 1) * fold_step + fold_test_size
        test_start = max(min_idx + (fold_idx + 1) * fold_step, test_end - fold_test_size)
        
        if test_end > n:
            break  # No hay suficiente datos para este fold
        
        gap_start = test_start - gap_days
        val_end = max(min_idx, gap_start - 1)
        val_start = max(min_idx, val_end - fold_val_size)
        
        train_end = max(fold_train_size, val_start - 1)
        train_start = max(0, train_end - fold_train_size)
        
        # Extraer datos
        train_features = features_array[train_start:train_end]
        train_returns = returns_array[train_start:train_end]
        
        val_features = features_array[val_start:val_end]
        val_returns = returns_array[val_start:val_end]
        
        test_features = features_array[test_start:test_end]
        test_returns = returns_array[test_start:test_end]
        
        dates_train = dates_array[train_start:train_end]
        dates_val = dates_array[val_start:val_end]
        dates_test = dates_array[test_start:test_end]
        
        # Escalar usando only training data (prevent leakage)
        scaler = MinMaxScaler()
        train_scaled = scaler.fit_transform(train_features)
        val_scaled = scaler.transform(val_features)
        test_scaled = scaler.transform(test_features)
        
        # Calcular threshold SOLO sobre train
        dynamic_threshold = compute_dynamic_threshold(train_returns, percentile=60.0)
        
        # Convertir a clases
        train_classes = returns_to_classes(train_returns, dynamic_threshold)
        val_classes = returns_to_classes(val_returns, dynamic_threshold)
        test_classes = returns_to_classes(test_returns, dynamic_threshold)
        
        # Class weights
        class_counts = np.bincount(train_classes, minlength=3)
        class_weights = 1.0 / (class_counts + 1e-8)
        class_weights = class_weights / class_weights.sum() * 3
        
        # Crear secuencias
        X_train, y_train_classes = create_sequences(train_scaled, train_returns, window_size)
        X_val, y_val_classes = create_sequences(val_scaled, val_returns, window_size)
        X_test, y_test_classes = create_sequences(test_scaled, test_returns, window_size)
        
        # Convertir a PyTorch
        X_train_t = torch.from_numpy(X_train).float()
        y_train_t = torch.from_numpy(returns_to_classes(y_train_classes, dynamic_threshold)).long()
        X_val_t = torch.from_numpy(X_val).float()
        y_val_t = torch.from_numpy(returns_to_classes(y_val_classes, dynamic_threshold)).long()
        X_test_t = torch.from_numpy(X_test).float()
        y_test_t = torch.from_numpy(returns_to_classes(y_test_classes, dynamic_threshold)).long()
        
        fold_data = {
            "fold": fold_idx,
            "dates": {
                "train": dates_train,
                "val": dates_val,
                "test": dates_test,
            },
            "X_train": X_train_t,
            "y_train": y_train_t,
            "X_val": X_val_t,
            "y_val": y_val_t,
            "X_test": X_test_t,
            "y_test": y_test_t,
            "scaler": scaler,
            "threshold": dynamic_threshold,
            "class_weights": torch.tensor(class_weights, dtype=torch.float32),
        }
        
        folds.append(fold_data)
        
        print(
            f"  Fold {fold_idx:2d}: train=[{pd.Timestamp(dates_train[0]).date()}, {pd.Timestamp(dates_train[-1]).date()}] "
            f"val=[{pd.Timestamp(dates_val[0]).date()}, {pd.Timestamp(dates_val[-1]).date()}] "
            f"test=[{pd.Timestamp(dates_test[0]).date()}, {pd.Timestamp(dates_test[-1]).date()}]"
        )
    
    print(f"[OK] Walk-Forward: {len(folds)} folds preparados\n")
    return folds