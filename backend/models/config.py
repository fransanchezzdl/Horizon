"""
Configuración del modelo Horizon Predictor.
Dos perfiles de configuración según tipo de activo.
"""

# Catálogo de tickers iniciales
TICKERS = {
    "stable": ["KO", "AAPL", "GC=F", "SI=F"],
    "volatile": ["TSLA", "NVDA", "BTC-USD", "ETH-USD"]
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
    "early_stopping_patience": 10,
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
    "early_stopping_patience": 15,
}

# Features del modelo (9 features)
FEATURE_COLS = [
    "Close", "Volume", "RSI", "MACD", "EMA",
    "Bollinger_PctB", "ATR", "Log_Return", "Volume_Ratio"
]

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
