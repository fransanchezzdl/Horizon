"""
Configuración del modelo Horizon Predictor.
Dos perfiles de configuración según tipo de activo.
"""

import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Variables de entorno
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", None)
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", None)
SAVED_MODELS_DIR = os.getenv("SAVED_MODELS_DIR", "backend/models/saved_models")
USE_SENTIMENT = os.getenv("USE_SENTIMENT", "False").lower() == "true"  # Phase 3: Disabled - sentiment reduced performance from 41.22% to 57.42%
USE_ADVANCED_FEATURES = os.getenv("USE_ADVANCED_FEATURES", "True").lower() == "true"
USE_ATTENTION_MODEL = os.getenv("USE_ATTENTION_MODEL", "True").lower() == "true"

# Catálogo de tickers - Actualizado de la BD
# stable = estabilidad TRUE en BD
# volatile = estabilidad FALSE en BD
TICKERS = {
    "stable": ["KO", "AAPL", "GC=F", "SI=F", "GOOGL", "MSFT"],
    "volatile": ["TSLA", "NVDA", "BTC-USD", "ETH-USD", "AMZN", "BABA", "INTC", "META", "NFLX"] # type: ignore
}


def get_tickers_from_database():
    """
    Carga los tickers desde la BD Supabase (RECOMENDADO).
    Retorna dict con {stable: list, volatile: list}
    
    Uso:
        TICKERS = get_tickers_from_database()
    """
    try:
        from ..daos.activo_dao import ActivoDAO
        
        all_activos = ActivoDAO.obtener_todos()  # type: ignore
        stable = []
        volatile = []
        
        for activo in all_activos:
            if hasattr(activo, 'ticker') and activo.ticker:
                if hasattr(activo, 'estabilidad') and activo.estabilidad:
                    stable.append(activo.ticker)
                else:
                    volatile.append(activo.ticker)
        
        if stable or volatile:
            print(f"[OK] Cargados {len(stable) + len(volatile)} tickers de BD:")
            print(f"   • Stable: {stable}")
            print(f"   • Volatile: {volatile}")
            return {"stable": stable, "volatile": volatile}
    
    except Exception as e:
        print(f"[WARNING] No se pudo cargar de BD: {e}")
    
    # Fallback a hardcoded
    return TICKERS

# Configuración por tipo de activo
STABLE_CONFIG = {
    "window_size": 30,
    "hidden_dim": 64,
    "num_layers": 2,
    "dropout": 0.2,        # Subido de 0.1 — el modelo attention es más expresivo
    "learning_rate": 0.0005,  # Bajado de 0.001 — más estable con attention
    "epochs": 200,         # Subido de 150 — más tiempo para converger
    "batch_size": 16,
    "trend_threshold": 0.01,
    "early_stopping_patience": 30,  # Subido de 20 — más paciencia
}

VOLATILE_CONFIG = {
    "window_size": 60,
    "hidden_dim": 64,
    "num_layers": 2,
    "dropout": 0.3,
    "learning_rate": 0.0003,  # Bajado de 0.0005
    "epochs": 250,         # Subido de 200
    "batch_size": 32,
    "trend_threshold": 0.03,
    "early_stopping_patience": 35,  # Subido de 25
}

# Variaciones de hiperparámetros para diversificar el ensemble.
# Cada modelo del ensemble usa una configuración ligeramente diferente.
# Para pruebas rápidas: solo 1 variación por tipo
ENSEMBLE_VARIATIONS = {
    "stable": [
        {"hidden_dim": 64, "window_size": 30, "dropout": 0.35, "num_layers": 2},
    ],
    "volatile": [
        {"hidden_dim": 64, "window_size": 60, "dropout": 0.35, "num_layers": 2},
    ],
}

# Features de contexto de mercado (solo para activos volátiles)
MARKET_CONTEXT_TICKERS = {
    "VIX": "^VIX",      # Índice de volatilidad (miedo del mercado)
    "NASDAQ": "^IXIC",   # Índice NASDAQ Composite
}

# Features base (10 features, para todos los activos)
BASE_FEATURE_COLS = [
    "Close", "Volume", "RSI", "MACD", "EMA",
    "Bollinger_PctB", "ATR", "Log_Return", "Volume_Ratio",
    # Features de régimen de mercado (4) — siempre incluidas
    "SMA200_Dist", "SMA50_Slope", "Realized_Vol",
    # Régimen discreto: +1 uptrend, 0 neutro, -1 downtrend (Faber 2007)
    # SHAP la interpreta como cualquier feature ordinal.
    "SMA200_Regime",
]

# Features adicionales para activos volátiles (2 extras)
VOLATILE_EXTRA_COLS = ["VIX_Close", "NASDAQ_Return"]

# Features completas para volátiles (11 features)
VOLATILE_FEATURE_COLS = BASE_FEATURE_COLS + VOLATILE_EXTRA_COLS

# Features de sentimiento (3 básicas + 12 mejoradas con LAG = 15 totales si USE_SENTIMENT=True)
SENTIMENT_FEATURE_COLS = [
    # Básicas (Alpha Vantage + DistilRoBERTa)
    "sentiment_score", "sentiment_magnitude", "news_volume",
    # Mejoradas con LAG y normalización (v2 de sentiment)
    "sentiment_lag_1d", "sentiment_lag_2d", "sentiment_lag_3d", "sentiment_lag_4d", "sentiment_lag_5d",
    "sentiment_ma_3d", "sentiment_ma_5d",
    "sentiment_vol_normalized", "sentiment_vol_norm_lag_1d", "sentiment_vol_norm_lag_2d",
    "sentiment_momentum_5d", "sentiment_deviation"
]

# Features macro para commodities (4 extras, solo para GC=F y SI=F)
MACRO_COMMODITY_COLS = ["dollar_proxy", "real_rates_proxy", "risk_sentiment", "industrial_demand"]

# Features técnicas avanzadas (10 seleccionadas por correlación > 0.03)
# Eliminadas por baja correlación: ADX, Stochastic_K/D, Williams_R, MFI, ROC, Keltner_PctB, Donchian_PctB
ADVANCED_TECHNICAL_COLS = [
    # Volumen (2) - alta correlación
    "CMF",                # Chaikin Money Flow (0.0954)
    "OBV",                # On Balance Volume (0.0699)
    
    # Tendencia (4) - correlación media-alta
    "Aroon_Up",           # Aroon Up (0.0666)
    "Aroon_Down",         # Aroon Down (0.0402)
    "DX",                 # Directional Movement Index (0.0408)
    "CCI",                # Commodity Channel Index (0.0391)
    
    # Momentum (3) - correlación media
    "TSI",                # True Strength Index (0.0407)
    "KST",                # Know Sure Thing (0.0405)
    "CMO",                # Chande Momentum Oscillator (0.0368)
    
    # Osciladores (1) - correlación media
    "Ultimate_Osc",       # Ultimate Oscillator (0.0310)
]

# PHASE 2 FEATURES (12 nuevos indicadores técnicos de ingeniería)
PHASE2_FEATURE_COLS = [
    "momentum_5d",        # Momentum simple de 5 días
    "rsi_14",             # RSI adicional con período 14
    "macd_signal",        # MACD - Signal divergence
    "bbands_pct",         # Bollinger Bands percentage
    "atr_14",             # ATR adicional period 14
    "obv_momentum",       # On Balance Volume momentum
    "volume_sma_ratio",   # Volumen / SMA ratio
    "high_low_ratio",     # (High-Low)/Close ratio
    "close_range_pct",    # Close posición dentro de (High-Low)
    "roc_10",             # Rate of Change (10 períodos)
    "volatility_std",     # Rolling volatility STD (20 períodos)
    "price_acceleration", # Aceleración del precio (cambio en cambio)
]

# Features combinadas con sentimiento (12 / 14 features)
BASE_WITH_SENTIMENT_COLS = BASE_FEATURE_COLS + SENTIMENT_FEATURE_COLS       # 12
VOLATILE_WITH_SENTIMENT_COLS = VOLATILE_FEATURE_COLS + SENTIMENT_FEATURE_COLS  # 14

# Features combinadas con técnicas avanzadas (19 / 21 features)
BASE_WITH_ADVANCED_COLS = BASE_FEATURE_COLS + ADVANCED_TECHNICAL_COLS  # 19
VOLATILE_WITH_ADVANCED_COLS = VOLATILE_FEATURE_COLS + ADVANCED_TECHNICAL_COLS  # 21

# Features combinadas con PHASE 2 (21 / 23 features)
BASE_WITH_PHASE2_COLS = BASE_FEATURE_COLS + PHASE2_FEATURE_COLS  # 21
VOLATILE_WITH_PHASE2_COLS = VOLATILE_FEATURE_COLS + PHASE2_FEATURE_COLS  # 23

# Features combinadas con todo (34 / 36 features)
BASE_WITH_ALL_COLS = BASE_FEATURE_COLS + SENTIMENT_FEATURE_COLS + ADVANCED_TECHNICAL_COLS + PHASE2_FEATURE_COLS  # 34
VOLATILE_WITH_ALL_COLS = VOLATILE_FEATURE_COLS + SENTIMENT_FEATURE_COLS + ADVANCED_TECHNICAL_COLS + PHASE2_FEATURE_COLS  # 36

# Alias para compatibilidad con código existente
FEATURE_COLS = BASE_FEATURE_COLS

# Ensemble
ENSEMBLE_SIZE = 1  # Cambiar a 1 para pruebas rápidas, 5 para producción

# Predicción
# Comparativa empírica 3d vs 5d (walk-forward 15 tickers, 2026-04-13):
#   - 3d gana: KO+5pp, NVDA+5pp, NFLX+7pp, BABA+4pp → activos con señal técnica corta
#   - 5d gana: AAPL+7pp, META+7pp, INTC+8pp, MSFT+6pp → activos con memoria más larga
#   - Media: 5d = 35.09% BA  vs  3d = 34.01% BA  → 5d es mejor en promedio
# Conclusión: horizonte óptimo es heterogéneo por activo; 5d es el mejor default global.
# Para mejora futura: horizonte per-ticker calibrado individualmente.
PREDICTION_HORIZON = 5  # 5 días de trading (default global óptimo)

# Split de datos
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

# Configuración XGBoost - SEGREGADA por tipo de activo
# STABLE: menos agresivo, datos más predecibles
# OPTIMIZADO v2 (MEJOR): Tuning fino para máximo F1 + Sentiment Lag
XGBOOST_STABLE_CONFIG = {
    "n_estimators": 620,       # ↑ 550→620: más árboles para capturar patterns
    "max_depth": 5,            # ✓ mantener: profundidad óptima
    "learning_rate": 0.042,    # ↓ 0.045→0.042: convergencia más controlada
    "subsample": 0.88,         # ↓ 0.92→0.88: mejor regularización
    "colsample_bytree": 0.88,  # ↓ 0.92→0.88: mejor regularización
    "early_stopping_rounds": 30,   # ↑ 25→30: más paciencia, mejor convergencia
    "min_child_weight": 0.5,   # fine-grained splits
    "gamma": 1.5,              # penaliza complejidad (reduce overfitting)
}

# VOLATILE: más cautela, pero con mejor regularización para recall estable
# OPTIMIZADO v2 (MEJOR): Tuning fino para máximo F1 + Sentiment Lag features
XGBOOST_VOLATILE_CONFIG = {
    "n_estimators": 750,       # ↑ 700→750: más árboles para capturar patterns
    "max_depth": 4,            # ✓ mantener: balance profundidad-bias
    "learning_rate": 0.024,    # ↓ 0.025→0.024: convergencia más controlada
    "subsample": 0.85,         # ↑ 0.8→0.85: balance regularización
    "colsample_bytree": 0.85,  # ↑ 0.8→0.85: balance regularización
    "early_stopping_rounds": 40,   # ↑ 35→40: más paciencia para convergencia
    "min_child_weight": 0.5,   # fine-grained splits
    "gamma": 1.2,              # penaliza complejidad (reduce overfitting)
}

# Para compatibilidad (usar el default stable)
XGBOOST_CONFIG = XGBOOST_STABLE_CONFIG

# Umbrales FIJOS de etiquetado (reproducibles entre reentrenamientos)
# Basados en la distribución histórica de retornos log a 5 días:
#   - BTC/ETH: σ ≈ 0.08, ±1.5% cubre ~30% de cada cola
#   - TSLA/NVDA: σ ≈ 0.06, ±1.5% cubre ~35% de cada cola
#   - KO/AAPL: σ ≈ 0.025, ±1.5% cubre ~30% de cada cola
# Usar percentile 60 del dataset histórico daría ~0.014–0.018, por lo que ±0.015 es empíricamente razonable.
LABELING_FIXED_THRESHOLDS = {
    "bajista": -0.015,  # retorno log a 5 días < -1.5% → BAJISTA
    "alcista":  0.015,  # retorno log a 5 días > +1.5% → ALCISTA
}

# Pesos del meta-ensemble (BiGRU + XGBoost)
META_ENSEMBLE_WEIGHTS = {
    "bigru": 0.6,
    "xgboost": 0.4,
}

# Factor de escala para sigmoid(bigru_return * scale) en el meta-ensemble.
# Un valor de 50 hace que un retorno de ±0.02 (±2%) mapee a probabilidades
# cerca de 0.73/0.27, proporcionando sensibilidad razonable a señales pequeñas.
META_ENSEMBLE_SIGMOID_SCALE = 50.0

# Semi-anchura de la zona neutra en el meta-ensemble (score en [0,1]).
# Un delta de 0.05 define la banda [0.45, 0.55] como LATERAL,
# equilibrando entre señales falsas y detección de tendencias débiles.
META_ENSEMBLE_TREND_DELTA = 0.05


def get_config(ticker: str) -> dict:
    """Devuelve la configuración apropiada según el tipo de activo."""
    if ticker in TICKERS["volatile"]:
        return VOLATILE_CONFIG.copy()
    return STABLE_CONFIG.copy()


def get_asset_type(ticker: str) -> str:
    """Devuelve 'stable' o 'volatile'."""
    if ticker in TICKERS["volatile"]:
        return "volatile"
    return "stable"


def get_feature_cols(ticker: str) -> list:
    """
    Devuelve la lista de features según el tipo de activo.

    Combina features base, contexto de mercado (volátiles), macro (commodities)
    y técnicas avanzadas según las flags USE_SENTIMENT y USE_ADVANCED_FEATURES.
    
    PHASE 3 (CURRENT): Sentiment disabled (reduced performance from 41.22% to 57.42%)
    
    Configuraciones posibles:
    - Stable sin extras: 9 features
    - Stable + macro (GC=F, SI=F): 13 features  
    - Stable + advanced: 27 features
    - Etc.
    
    NOTE: Sentiment features showed ~0 importance in XGBoost despite +6.97pp improvement
    in BA metrics. Removing them revealed they were NOISE, not signal. Final Phase 3
    removed all 12 sentiment lag features, improving average confidence from 41.22% to 57.42%.
    """
    is_volatile = ticker in TICKERS["volatile"]
    
    # Determinar features base según tipo de activo
    if is_volatile:
        base = VOLATILE_FEATURE_COLS.copy()
    else:
        base = BASE_FEATURE_COLS.copy()
    
    # Añadir features macro si es commodity
    if ticker in ["GC=F", "SI=F"]:
        base.extend(MACRO_COMMODITY_COLS)
    
    # Añadir sentimiento si está habilitado
    if USE_SENTIMENT:
        base.extend(SENTIMENT_FEATURE_COLS)
    
    # Añadir técnicas avanzadas si está habilitado
    if USE_ADVANCED_FEATURES:
        base.extend(ADVANCED_TECHNICAL_COLS)
    
    return base
