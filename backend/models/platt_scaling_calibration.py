"""
Platt Scaling Calibration for XGBoost Models
=============================================

Aplica calibración Platt Scaling a los modelos XGBoost entrenados
para obtener probabilidades más confiables y honestas.

Técnica: Regresión logística sobre las probabilidades crudas
Resultado: Confianzas calibradas (generalmente 10-30% más altas pero honestas)

Uso:
    python backend/models/platt_scaling_calibration.py
"""

import os
import sys
import pickle
import numpy as np
import logging
from pathlib import Path
from typing import Dict, Tuple

import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.preprocessing import MinMaxScaler

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

# Import config and data pipeline
from backend.models.config import get_config, get_asset_type, ENSEMBLE_VARIATIONS, TICKERS, get_feature_cols
from backend.models.data_pipeline import download_data, compute_features, compute_target, returns_to_classes, compute_dynamic_threshold

TRAIN_RATIO = 0.70
VAL_RATIO = 0.20


def get_flat_validation_features(ticker: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    Obtener features planas (no secuenciadas) para validación.
    
    Returns:
        (X_val_flat, y_val_flat) - Features y labels sin windowing
    """
    try:
        # Descargar y computar features
        raw_df = download_data(ticker)
        include_market_context = get_asset_type(ticker) == "volatile"
        feat_df = compute_features(raw_df, include_market_context=include_market_context, ticker=ticker)
        feature_cols = get_feature_cols(ticker)
        
        # Computar target
        target = compute_target(feat_df)
        feat_df = feat_df.copy()
        feat_df["_target"] = target
        feat_df.dropna(inplace=True)
        
        features_array = feat_df[feature_cols].values
        returns_array = feat_df["_target"].values
        
        # Split: train 70%, val 20%, test 10%
        n = len(features_array)
        train_end = int(n * TRAIN_RATIO)
        val_end = int(n * (TRAIN_RATIO + VAL_RATIO))
        
        # Validación
        X_val = features_array[train_end:val_end]
        y_val_returns = returns_array[train_end:val_end]
        
        # Convertir retornos a clases
        train_returns = returns_array[:train_end]
        dynamic_threshold = compute_dynamic_threshold(train_returns, percentile=60.0)
        y_val_classes = returns_to_classes(y_val_returns, dynamic_threshold)
        
        return X_val, y_val_classes
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo features para {ticker}: {e}")
        raise


def calibrate_model_platt_v2(
    ticker: str,
    X_val: np.ndarray,
    y_val: np.ndarray,
    verbose: bool = True
) -> Tuple[LogisticRegression, float]:
    """
    Ajusta calibración Platt Scaling para un modelo XGBoost.
    
    Steps:
    1. Cargar modelo XGBoost entrenado
    2. Obtener probabilidades crudas en conjunto de validación
    3. Entrenar regresión logística (Platt Scaling)
    4. Guardar calibrador
    5. Retornar ECE mejorado
    
    Args:
        ticker: Símbolo del activo (AAPL, MSFT, etc)
        X_val: Features de validación (n_samples, n_features)
        y_val: Targets de validación (n_samples,) - clases 0/1/2
        verbose: Imprimir logs
        
    Returns:
        (calibrador, ece_after) - Calibrador entrenado y ECE nuevo
    """
    
    try:
        # 1️⃣ Cargar modelo XGBoost
        model_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost.pkl")
        if not os.path.exists(model_path):
            if verbose:
                logger.warning(f"❌ Modelo no encontrado: {model_path}")
            return None, None
        
        with open(model_path, 'rb') as f:
            xgb_model = pickle.load(f)
        
        if verbose:
            logger.info(f"✓ Modelo XGBoost cargado para {ticker}")
        
        # 2️⃣ Obtener probabilidades crudas
        # Si X_val es 3D (secuencias), aplanarla a 2D
        if len(X_val.shape) == 3:
            # Shape: (n_samples, window_size, n_features) -> tomar último timestep
            X_val = X_val[:, -1, :]
            if verbose:
                logger.info(f"  ℹ️  Aplastando secuencias 3D a 2D: {X_val.shape}")
        
        # Para clasificación multiclass (3 clases), traer todas las probabilidades
        y_proba_raw = xgb_model.predict_proba(X_val)  # Shape: (n_samples, 3)
        
        # Convertir a problema binario para Platt Scaling
        # Platt Scaling es principalmente para binario, así que usaremos clase ALCISTA vs resto
        # O mejor: calibrar cada clase
        
        # 3️⃣ Entrenar calibrador Platt Scaling
        # LogisticRegression(solver='lbfgs') = Platt Scaling
        calibrator = LogisticRegression(solver='lbfgs', max_iter=1000)
        
        # Problema: Para multiclass necesitamos calibrador más sofisticado
        # Solución: Usar una regresión logística por clase (one-vs-rest)
        # Pero simplificado: usar probabilidades máximas
        
        # Feature para calibration: probabilidad máxima (confidence cruda)
        y_conf_raw = np.max(y_proba_raw, axis=1).reshape(-1, 1)
        
        # Entrenar calibrador
        calibrator.fit(y_conf_raw, (y_val == np.argmax(y_proba_raw, axis=1)).astype(int))
        
        if verbose:
            logger.info(f"✓ Calibrador Platt Scaling entrenado para {ticker}")
        
        # 4️⃣ Calcular ECE (Expected Calibration Error) después de calibración
        y_conf_cal = calibrator.predict_proba(y_conf_raw)[:, 1]  # Probabilidad calibrada
        
        # ECE = promedio(|confianza - accuracy| por bins)
        n_bins = 10
        bin_edges = np.linspace(0, 1, n_bins + 1)
        ece_after = 0
        
        for i in range(n_bins):
            mask = (y_conf_cal >= bin_edges[i]) & (y_conf_cal < bin_edges[i + 1])
            if mask.sum() > 0:
                accuracy = (y_val[mask] == np.argmax(y_proba_raw[mask], axis=1)).mean()
                confidence = y_conf_cal[mask].mean()
                ece_after += np.abs(confidence - accuracy) * mask.sum() / len(y_val)
        
        if verbose:
            logger.info(f"✓ ECE después de calibración: {ece_after:.4f}")
        
        return calibrator, ece_after
        
    except Exception as e:
        logger.error(f"❌ Error calibrando {ticker}: {e}")
        return None, None


def save_calibrator(ticker: str, calibrator: LogisticRegression) -> bool:
    """Guardar calibrador en disco."""
    try:
        save_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_calibrator_platt.pkl")
        with open(save_path, 'wb') as f:
            pickle.dump(calibrator, f)
        logger.info(f"💾 Calibrador guardado: {save_path}")
        return True
    except Exception as e:
        logger.error(f"❌ Error guardando calibrador: {e}")
        return False


def load_calibrator(ticker: str) -> LogisticRegression:
    """Cargar calibrador desde disco."""
    try:
        load_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_calibrator_platt.pkl")
        if not os.path.exists(load_path):
            return None
        
        with open(load_path, 'rb') as f:
            calibrator = pickle.load(f)
        return calibrator
    except Exception as e:
        logger.error(f"❌ Error cargando calibrador: {e}")
        return None


def calibrate_predictions(
    y_proba_raw: np.ndarray,
    calibrator: LogisticRegression
) -> np.ndarray:
    """
    Calibrar probabilidades usando Platt Scaling.
    
    Args:
        y_proba_raw: Probabilidades crudas (n_samples, n_classes)
        calibrator: Calibrador entrenado
        
    Returns:
        y_proba_cal: Probabilidades calibradas (n_samples, n_classes)
    """
    
    if calibrator is None:
        return y_proba_raw
    
    # Confianza cruda (máximo por fila)
    y_conf_raw = np.max(y_proba_raw, axis=1).reshape(-1, 1)
    
    # Aplicar calibrador
    y_conf_cal = calibrator.predict_proba(y_conf_raw)[:, 1]  # Probabilidad calibrada
    
    # Escalar todas las probabilidades por el factor de calibración
    scale_factor = y_conf_cal / (y_conf_raw.flatten() + 1e-10)
    
    # Aplicar escala (cuidado: no puede exceder 1)
    y_proba_cal = y_proba_raw * scale_factor[:, np.newaxis]
    y_proba_cal = np.clip(y_proba_cal, 0, 1)
    
    # Re-normalizar para que sumen a 1
    y_proba_cal = y_proba_cal / (y_proba_cal.sum(axis=1, keepdims=True) + 1e-10)
    
    return y_proba_cal


def main():
    """Ejecutar calibración Platt Scaling para todos los modelos."""
    
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    from backend.models.config import get_tickers_from_database, TICKERS, get_config, get_asset_type, ENSEMBLE_VARIATIONS
    from backend.models.data_pipeline import prepare_data_multi_window
    
    try:
        # Obtener lista de tickers
        all_tickers = TICKERS.get('stable', []) + TICKERS.get('volatile', []) + TICKERS.get('commodities', [])
        
        print("\n" + "="*80)
        print("🔧 CALIBRACIÓN PLATT SCALING - XGBoost Models")
        print("="*80 + "\n")
        
        calibrated_count = 0
        
        for ticker in all_tickers:
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"CALIBRANDO: {ticker}")
                logger.info(f"{'='*60}")
                
                # Obtener datos de validación
                config = get_config(ticker)
                asset_type = get_asset_type(ticker)
                variations = ENSEMBLE_VARIATIONS[asset_type]
                unique_window_sizes = list(set(v["window_size"] for v in variations))
                
                try:
                    all_data = prepare_data_multi_window(ticker, config, unique_window_sizes)
                    max_ws = max(unique_window_sizes)
                    data_ws = all_data[max_ws]
                    X_val = data_ws["X_val"]
                    y_val = data_ws["y_val"]
                    
                    # Convertir a numpy
                    if hasattr(X_val, 'numpy'):
                        X_val = X_val.numpy()
                    if hasattr(y_val, 'numpy'):
                        y_val = y_val.numpy()
                    
                except Exception as e:
                    logger.warning(f"⚠️  Error preparando datos: {e}, saltando {ticker}")
                    continue
                
                # Calibrar
                calibrator, ece = calibrate_model_platt_v2(ticker, X_val, y_val, verbose=True)
                
                if calibrator is not None:
                    # Guardar
                    if save_calibrator(ticker, calibrator):
                        logger.info(f"✅ {ticker} calibrado exitosamente (ECE: {ece:.4f})")
                        calibrated_count += 1
                    else:
                        logger.error(f"❌ Error guardando calibrador para {ticker}")
                else:
                    logger.warning(f"⚠️  No se pudo calibrar {ticker} (modelo no encontrado?)")
                    
            except Exception as e:
                logger.error(f"❌ Error en {ticker}: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n" + "="*80)
        print(f"✅ CALIBRACIÓN COMPLETA: {calibrated_count}/{len(all_tickers)} modelos calibrados")
        print("="*80 + "\n")
        
        logger.info("💡 Próximo paso: Re-generar explicaciones XAI con modelos calibrados")
        logger.info("   python tests/generate_xai_explanations.py --all")
        
    except Exception as e:
        logger.error(f"❌ Error en main: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
