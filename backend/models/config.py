"""
Configuración del modelo Horizon Predictor.
Dos perfiles de configuración según tipo de activo.
"""

# Catálogo de tickers iniciales
TICKERS = {
    "stable": ["KO"], #, "AAPL", "GC=F", "SI=F"],
    "volatile": ["TSLA"] #, "NVDA", "BTC-USD", "ETH-USD"]
}

# Configuración por tipo de activo
STABLE_CONFIG = {
    "window_size": 30,
    "hidden_dim": 64,
    "num_layers": 2,
    "dropout": 0.1,
    "learning_rate": 0.001,
    "epochs": 150,
    "batch_size": 16,
    "trend_threshold": 0.01,  # ±1.0% para tendencia alcista/bajista
    "early_stopping_patience": 20,
}

VOLATILE_CONFIG = {
    "window_size": 60,
    "hidden_dim": 64,
    "num_layers": 2,
    "dropout": 0.3,
    "learning_rate": 0.0005,
    "epochs": 200,
    "batch_size": 32,
    "trend_threshold": 0.03,  # ±3.0% para activos volátiles
    "early_stopping_patience": 25,
}

# Variaciones de hiperparámetros para diversificar el ensemble.
# Cada modelo del ensemble usa una configuración ligeramente diferente.
ENSEMBLE_VARIATIONS = {
    "stable": [
        {"hidden_dim": 64, "window_size": 30, "dropout": 0.10, "num_layers": 2},
        {"hidden_dim": 48, "window_size": 30, "dropout": 0.15, "num_layers": 2},
        {"hidden_dim": 80, "window_size": 30, "dropout": 0.05, "num_layers": 2},
        {"hidden_dim": 64, "window_size": 20, "dropout": 0.10, "num_layers": 2},
        {"hidden_dim": 64, "window_size": 40, "dropout": 0.20, "num_layers": 3},
    ],
    "volatile": [
        {"hidden_dim": 64, "window_size": 60, "dropout": 0.30, "num_layers": 2},
        {"hidden_dim": 48, "window_size": 60, "dropout": 0.35, "num_layers": 2},
        {"hidden_dim": 80, "window_size": 60, "dropout": 0.25, "num_layers": 2},
        {"hidden_dim": 64, "window_size": 45, "dropout": 0.30, "num_layers": 2},
        {"hidden_dim": 64, "window_size": 75, "dropout": 0.30, "num_layers": 3},
    ],
}

# Features de contexto de mercado (solo para activos volátiles)
MARKET_CONTEXT_TICKERS = {
    "VIX": "^VIX",      # Índice de volatilidad (miedo del mercado)
    "NASDAQ": "^IXIC",   # Índice NASDAQ Composite
}

# Features base (9 features, para todos los activos)
BASE_FEATURE_COLS = [
    "Close", "Volume", "RSI", "MACD", "EMA",
    "Bollinger_PctB", "ATR", "Log_Return", "Volume_Ratio"
]

# Features adicionales para activos volátiles (2 extras)
VOLATILE_EXTRA_COLS = ["VIX_Close", "NASDAQ_Return"]

# Features completas para volátiles (11 features)
VOLATILE_FEATURE_COLS = BASE_FEATURE_COLS + VOLATILE_EXTRA_COLS

# Features de sentimiento (3 extras, opcionales si USE_SENTIMENT=True)
SENTIMENT_FEATURE_COLS = ["sentiment_score", "sentiment_magnitude", "news_volume"]

# Features combinadas con sentimiento (12 / 14 features)
BASE_WITH_SENTIMENT_COLS = BASE_FEATURE_COLS + SENTIMENT_FEATURE_COLS       # 12
VOLATILE_WITH_SENTIMENT_COLS = VOLATILE_FEATURE_COLS + SENTIMENT_FEATURE_COLS  # 14

# Alias para compatibilidad con código existente
FEATURE_COLS = BASE_FEATURE_COLS

# Activar análisis de sentimiento (requiere FINNHUB_API_KEY y paquete transformers)
USE_SENTIMENT = True

# Ensemble
ENSEMBLE_SIZE = 5

# Predicción
PREDICTION_HORIZON = 5  # 5 días de trading

# Split de datos
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

# Rutas
SAVED_MODELS_DIR = "backend/models/saved_models"

# Configuración XGBoost
XGBOOST_CONFIG = {
    "n_estimators": 300,
    "max_depth": 6,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "early_stopping_rounds": 20,
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

    Si USE_SENTIMENT=True incluye las 3 features de sentimiento.
    """
    if ticker in TICKERS["volatile"]:
        base = VOLATILE_WITH_SENTIMENT_COLS if USE_SENTIMENT else VOLATILE_FEATURE_COLS
    else:
        base = BASE_WITH_SENTIMENT_COLS if USE_SENTIMENT else BASE_FEATURE_COLS
    return base.copy()
