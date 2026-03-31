"""
Entrenamiento XGBoost con Phase 2 Features - Feature Engineering.

Este script integra 12 nuevos indicadores técnicos (Phase 2) en el pipeline
y entrena el modelo XGBoost con todos los features disponibles.

Mejora esperada: +2-4% accuracy vs baseline (83.6% → 85-87%)
"""

import os
import sys
import logging
import pickle
import numpy as np
import pandas as pd
import warnings
from pathlib import Path

# Suprimir advertencias innecesarias
warnings.filterwarnings('ignore')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Añadir directory raíz al path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from backend.models.data_pipeline import download_data, compute_features, prepare_data_multi_window
from backend.models.phase2_features import Phase2FeaturesBuilder, integrate_phase2_with_pipeline
from backend.models.config import (
    PREDICTION_HORIZON, TRAIN_RATIO, VAL_RATIO, SAVED_MODELS_DIR,
    get_feature_cols, get_asset_type, get_config
)

# Importar XGBoost
try:
    import xgboost as xgb
except ImportError:
    logger.error("XGBoost no instalado. Instalar con: pip install xgboost")
    sys.exit(1)

from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix


class Phase2XGBoostTrainer:
    """Entrenador de XGBoost con Phase 2 Features."""
    
    def __init__(self, ticker: str, use_phase2: bool = True):
        """
        Inicializa el entrenador.
        
        Args:
            ticker: Símbolo del activo (ej: 'AAPL')
            use_phase2: Si True, usa todos los features de Phase 2
        """
        self.ticker = ticker
        self.use_phase2 = use_phase2
        self.model = None
        self.scaler = MinMaxScaler()
        self.feature_names = []
        
    def prepare_data(self, lookback: int = 60) -> tuple:
        """
        Prepara datos usando la pipeline original (multi-window) con Phase 2 features.
        
        Args:
            lookback: Ventana de lookback (no usado, compatible con multi-window)
        
        Returns:
            (X_train, y_train, X_val, y_val, X_test, y_test, feature_names)
        """
        logger.info(f"\n[Phase2] Preparando datos con pipeline original +Phase 2...")
        
        # Get config for ticker
        config = get_config(self.ticker)
        window_sizes = [30]  # Use single window for Phase 2
        
        # Use original multi-window preparation
        prepared_data = prepare_data_multi_window(self.ticker, config, window_sizes)
        
        # Extract data for window_size=30
        ws_data = prepared_data[30]
        
        X_train = ws_data['X_train'].numpy() if hasattr(ws_data['X_train'], 'numpy') else ws_data['X_train']
        y_train = ws_data['y_train'].numpy() if hasattr(ws_data['y_train'], 'numpy') else ws_data['y_train']
        X_val = ws_data['X_val'].numpy() if hasattr(ws_data['X_val'], 'numpy') else ws_data['X_val']
        y_val = ws_data['y_val'].numpy() if hasattr(ws_data['y_val'], 'numpy') else ws_data['y_val']
        X_test = ws_data['X_test'].numpy() if hasattr(ws_data['X_test'], 'numpy') else ws_data['X_test']
        y_test = ws_data['y_test'].numpy() if hasattr(ws_data['y_test'], 'numpy') else ws_data['y_test']
        
        logger.info(f"✅ Datos preparados: {X_train.shape[0]} train, "
                   f"{X_val.shape[0]} val, {X_test.shape[0]} test")
        logger.info(f"   Shape features: {X_train.shape[1]}")
        
        # Feature names are from the config
        self.feature_names = get_feature_cols(self.ticker)
        
        logger.info(f"✅ Total {len(self.feature_names)} features")
        
        return X_train, y_train, X_val, y_val, X_test, y_test, self.feature_names
    
    def train(self, X_train, y_train, X_val, y_val, epochs: int = 150):
        """
        Entrena modelo XGBoost con los datos preparados.
        
        Args:
            X_train: Datos de entrenamiento
            y_train: Labels de entrenamiento
            X_val: Datos de validación
            y_val: Labels de validación
            epochs: Número de rondas de boosting
        """
        logger.info(f"\n[Phase2] Entrenando XGBoost para {self.ticker}...")
        
        # Convertir a [0, 1, 2] para multi-class
        # Los datos ya vienen en este formato de prepare_data_multi_window
        y_train_adj = y_train
        y_val_adj = y_val
        
        # Crear dataset para XGBoost
        dtrain = xgb.DMatrix(X_train, label=y_train_adj)
        dval = xgb.DMatrix(X_val, label=y_val_adj)
        
        #Parámetros optimizados
        params = {
            'max_depth': 6,
            'learning_rate': 0.1,
            'objective': 'multi:softprob',
            'num_class': 3,
            'random_state': 42,
            'n_jobs': -1,
            'device': 'cpu'
        }
        
        # Entrenar con early stopping
        evals = [(dtrain, 'train'), (dval, 'eval')]
        evals_result = {}
        
        self.model = xgb.train(
            params,
            dtrain,
            num_boost_round=epochs,
            evals=evals,
            evals_result=evals_result,
            early_stopping_rounds=20,
            verbose_eval=10 if logger.level <= logging.INFO else False
        )
        
        logger.info(f"✅ Entrenamiento completado en {self.model.best_iteration} rondas")
        
    def evaluate(self, X_test, y_test) -> dict:
        """
        Evalúa modelo en test set.
        
        Args:
            X_test: Datos de test
            y_test: Labels de test (en escala [0, 1, 2])
        
        Returns:
            Dict con métricas
        """
        logger.info(f"\n[Phase2] Evaluando en test set...")
        
        # Predicciones
        dtest = xgb.DMatrix(X_test)
        y_pred_proba = self.model.predict(dtest)
        y_pred = np.argmax(y_pred_proba, axis=1)  # Ya está en [0, 1, 2]
        
        # Calcular métricas
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
        recall = recall_score(y_test, y_pred, average='weighted', zero_division=0)
        f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
        
        conf_matrix = confusion_matrix(y_test, y_pred, labels=[0, 1, 2])
        
        logger.info(f"✅ Resultados para {self.ticker}:")
        logger.info(f"   Accuracy:  {accuracy:.4f} ({accuracy*100:.2f}%)")
        logger.info(f"   Precision: {precision:.4f}")
        logger.info(f"   Recall:    {recall:.4f}")
        logger.info(f"   F1-Score:  {f1:.4f}")
        logger.info(f"\n   Matriz de confusión:")
        logger.info(f"   {conf_matrix}")
        
        return {
            'ticker': self.ticker,
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'confusion_matrix': conf_matrix
        }
    
    def save_model(self):
        """Guarda modelo entrenado."""
        if self.model is None:
            logger.warning("No hay modelo para guardar")
            return
        
        model_dir = Path(SAVED_MODELS_DIR)
        model_dir.mkdir(parents=True, exist_ok=True)
        
        model_path = model_dir / f"xgboost_phase2_{self.ticker}.pkl"
        scaler_path = model_dir / f"scaler_phase2_{self.ticker}.pkl"
        features_path = model_dir / f"features_phase2_{self.ticker}.pkl"
        
        # Guardar modelo
        self.model.save_model(str(model_path).replace('.pkl', '.json'))
        
        # Guardar scaler y feature names
        with open(scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)
        
        with open(features_path, 'wb') as f:
            pickle.dump(self.feature_names, f)
        
        logger.info(f"✅ Modelo guardado:")
        logger.info(f"   Modelo: {model_path}")
        logger.info(f"   Scaler: {scaler_path}")
        logger.info(f"   Features: {features_path}")


def train_ticker_phase2(ticker: str) -> dict:
    """
    Entrena un ticker completo con Phase 2 features.
    
    Args:
        ticker: Símbolo del activo
    
    Returns:
        Dict con resultados
    """
    trainer = Phase2XGBoostTrainer(ticker, use_phase2=True)
    
    try:
        # Preparar datos
        X_train, y_train, X_val, y_val, X_test, y_test, features = trainer.prepare_data()
        
        # Entrenar
        trainer.train(X_train, y_train, X_val, y_val, epochs=150)
        
        # Evaluar
        results = trainer.evaluate(X_test, y_test)
        
        # Guardar
        trainer.save_model()
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error entrenando {ticker}: {str(e)}")
        return {'ticker': ticker, 'error': str(e)}


def train_all_phase2():
    """Entrena todos los tickers con Phase 2 features."""
    
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'JPM', 'WMT', 'PFE', 'INTC', 'KO']
    
    logger.info("=" * 70)
    logger.info("FASE 2 - FEATURE ENGINEERING: Entrenamiento de todos los tickers")
    logger.info("=" * 70)
    
    results_all = []
    
    for i, ticker in enumerate(tickers, 1):
        logger.info(f"\n[{i}/{len(tickers)}] Procesando {ticker}...")
        results = train_ticker_phase2(ticker)
        results_all.append(results)
    
    # Resumen final
    logger.info("\n" + "=" * 70)
    logger.info("RESUMEN FINAL - PHASE 2")
    logger.info("=" * 70)
    
    accuracies = [r['accuracy'] for r in results_all if 'accuracy' in r]
    
    for result in results_all:
        if 'accuracy' in result:
            logger.info(f"{result['ticker']}: {result['accuracy']:.4f} ({result['accuracy']*100:.2f}%)")
        else:
            logger.info(f"{result['ticker']}: ERROR - {result.get('error', 'Unknown')}")
    
    if accuracies:
        logger.info(f"\n📊 Accuracy promedio: {np.mean(accuracies):.4f} ({np.mean(accuracies)*100:.2f}%)")
        logger.info(f"   Mín: {np.min(accuracies):.4f} | Máx: {np.max(accuracies):.4f}")
        logger.info(f"   Std: {np.std(accuracies):.4f}")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        # Entrenar ticker específico
        ticker = sys.argv[1].upper()
        logger.info(f"Entrenando {ticker} con Phase 2 features...")
        results = train_ticker_phase2(ticker)
    else:
        # Entrenar todos
        train_all_phase2()
