"""
Configuración del modelo Horizon Predictor.
Dos perfiles de configuración según tipo de activo.
"""

# Catálogo de tickers iniciales
TICKERS = {
    "stable": ["KO", "AAPL", "GC=F", "SI=F"],
    "volatile": ["TSLA", "NVDA", "BTC-USD", "ETH-USD"] # type: ignore
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

# Alias para compatibilidad con código existente
FEATURE_COLS = BASE_FEATURE_COLS

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
    """Devuelve la lista de features según el tipo de activo."""
    if ticker in TICKERS["volatile"]:
        return VOLATILE_FEATURE_COLS.copy()
    return BASE_FEATURE_COLS.copy()
