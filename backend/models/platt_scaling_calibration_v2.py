"""
Platt Scaling Calibration for XGBoost Models (v2)
==================================================

Improved version that:
1. Uses FLAT features (not sequences) matching what models were trained on
2. Applies Platt Scaling for confidence calibration
3. Saves calibrators for inference

Uso:
    python backend/models/platt_scaling_calibration_v2.py
"""

import os
import sys
import pickle
import numpy as np
import logging
from pathlib import Path
from typing import Tuple, Optional

import xgboost as xgb
from sklearn.linear_model import LogisticRegression

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
SAVED_MODELS_DIR = "backend/models/saved_models"

# Import
from backend.models.config import get_config, get_asset_type, TICKERS, get_feature_cols, ENSEMBLE_VARIATIONS
from backend.models.data_pipeline import (
    download_data, compute_features, compute_target, 
    returns_to_classes, compute_dynamic_threshold
)

TRAIN_RATIO = 0.70
VAL_RATIO = 0.20


def get_flat_validation_data(ticker: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    Obtener datos con AGGREGACIÓN TEMPORAL (como en training XGBoost).
    
    XGBoost fue entrenado con agregación: last, mean, std, trend
    Esto convierte secuencias (n, window, features) → (n, 4*features)
    
    Returns:
        (X_val_aggregated, y_val) - Features agregados y labels
    """
    # Obtener datos con sequences
    config = get_config(ticker)
    asset_type = get_asset_type(ticker)
    variations = ENSEMBLE_VARIATIONS[asset_type]
    unique_window_sizes = list(set(v["window_size"] for v in variations))
    max_ws = max(unique_window_sizes)
    
    # Usar data_pipeline para obtener sequences
    from backend.models.data_pipeline import prepare_data_multi_window
    all_data = prepare_data_multi_window(ticker, config, [max_ws])
    data_ws = all_data[max_ws]
    
    X_val_seq = data_ws["X_val"].numpy()  # Shape: (n_samples, window_size, n_features)
    y_val = data_ws["y_val"].numpy()      # Shape: (n_samples,)
    
    logger.info(f"✓ Loaded {len(X_val_seq)} sequences of size {X_val_seq.shape[1:]} for {ticker}")
    
    # Aplicar la MISMA agregación que usa XGBoost en training
    def aggregate_xgb_features(X_seq):
        """
        Agregar features temporales como en training:
        [last, mean, std, trend] × n_features
        """
        last  = X_seq[:, -1, :]           # (n, features)
        mean  = X_seq.mean(axis=1)        # (n, features)
        std   = X_seq.std(axis=1)         # (n, features)
        trend = X_seq[:, -1, :] - X_seq[:, 0, :]  # (n, features)
        return np.concatenate([last, mean, std, trend], axis=1)  # (n, 4*features)
    
    X_val_agg = aggregate_xgb_features(X_val_seq)
    logger.info(f"✓ Aggregated to shape {X_val_agg.shape} (4× temporal aggregates)")
    
    return X_val_agg, y_val


def calibrate_model_platt(
    ticker: str,
    X_val: np.ndarray,
    y_val: np.ndarray
) -> Tuple[Optional[LogisticRegression], float]:
    """
    Entrenar Platt Scaling calibrator para un modelo XGBoost.
    """
    try:
        # Cargar modelo
        model_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost.pkl")
        if not os.path.exists(model_path):
            logger.warning(f"❌ Modelo no encontrado: {model_path}")
            return None, 0.0
        
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        
        logger.info(f"✓ Loaded XGBoost model for {ticker}")
        
        # Obtener probabilidades
        y_proba_raw = model.predict_proba(X_val)
        y_pred = np.argmax(y_proba_raw, axis=1)
        y_conf_raw = np.max(y_proba_raw, axis=1).reshape(-1, 1)
        
        # Accuracy en validación
        accuracy = np.mean(y_pred == y_val)
        logger.info(f"  Validation accuracy: {accuracy:.3f}")
        
        # Labels para calibración: 1 si correcto, 0 si incorrecto
        y_labels = (y_pred == y_val).astype(int)
        
        # Entrenar calibrador
        calibrator = LogisticRegression(solver='lbfgs', max_iter=1000, random_state=42)
        calibrator.fit(y_conf_raw, y_labels)
        
        # Calcular ECE calibrado
        y_conf_cal = calibrator.predict_proba(y_conf_raw)[:, 1]
        y_conf_cal = np.clip(y_conf_cal, 0.01, 0.99)
        
        n_bins = 10
        ece = 0
        for i in range(n_bins):
            bin_lower = i / n_bins
            bin_upper = (i + 1) / n_bins
            in_bin = (y_conf_cal >= bin_lower) & (y_conf_cal < bin_upper)
            if in_bin.sum() > 0:
                bin_accuracy = y_labels[in_bin].mean()
                bin_confidence = y_conf_cal[in_bin].mean()
                ece += (in_bin.sum() / len(y_conf_cal)) * abs(bin_accuracy - bin_confidence)
        
        logger.info(f"✓ Platt Scaling calibrator trained (ECE: {ece:.4f})")
        return calibrator, ece
        
    except Exception as e:
        logger.error(f"❌ Error calibrating {ticker}: {e}")
        import traceback
        traceback.print_exc()
        return None, 0.0


def save_calibrator(ticker: str, calibrator: LogisticRegression) -> bool:
    """Guardar calibrador."""
    try:
        save_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_calibrator_platt.pkl")
        with open(save_path, 'wb') as f:
            pickle.dump(calibrator, f)
        logger.info(f"💾 Saved calibrator: {save_path}")
        return True
    except Exception as e:
        logger.error(f"❌ Error saving calibrator: {e}")
        return False


def load_calibrator(ticker: str) -> Optional[LogisticRegression]:
    """Cargar calibrador desde disco."""
    try:
        load_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_calibrator_platt.pkl")
        if not os.path.exists(load_path):
            return None
        
        with open(load_path, 'rb') as f:
            calibrator = pickle.load(f)
        return calibrator
    except Exception as e:
        logger.error(f"❌ Error loading calibrator: {e}")
        return None


def main():
    """Main loop."""
    all_tickers = TICKERS.get('stable', []) + TICKERS.get('volatile', [])
    
    print("\n" + "="*80)
    print("🔧 CALIBRACIÓN PLATT SCALING - XGBoost Models (v2)")
    print("="*80 + "\n")
    
    calibrated = []
    failed = []
    
    for ticker in all_tickers:
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"CALIBRATING: {ticker}")
            logger.info(f"{'='*60}")
            
            # Obtener datos
            X_val, y_val = get_flat_validation_data(ticker)
            
            # Calibrar
            calibrator, ece = calibrate_model_platt(ticker, X_val, y_val)
            
            if calibrator is not None:
                if save_calibrator(ticker, calibrator):
                    logger.info(f"✅ {ticker} calibrated successfully (ECE: {ece:.4f})")
                    calibrated.append(ticker)
                else:
                    logger.error(f"❌ Error saving calibrator for {ticker}")
                    failed.append(ticker)
            else:
                logger.warning(f"⚠️  Could not calibrate {ticker}")
                failed.append(ticker)
                
        except Exception as e:
            logger.error(f"❌ Error with {ticker}: {e}")
            failed.append(ticker)
    
    # Resumen
    print("\n" + "="*80)
    print("✅ CALIBRACIÓN COMPLETA")
    print("="*80)
    print(f"✓ Calibrated: {len(calibrated)}/15")
    print(f"  {', '.join(calibrated)}")
    if failed:
        print(f"✗ Failed: {len(failed)}")
        print(f"  {', '.join(failed)}")
    print()


if __name__ == "__main__":
    main()
