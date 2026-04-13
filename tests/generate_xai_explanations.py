"""
Generate XAI Explanations for all trained models
================================================

Se ejecuta después de entrenar (o manually).

Genera explicaciones usando XAI Engine y las guarda en Supabase.

Uso:
    python generate_xai_explanations.py [--ticker AAPL] [--all]
"""

import os
import sys
import argparse
import logging
import pickle
import numpy as np
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.models.config import get_tickers_from_database, get_config, SAVED_MODELS_DIR, ENSEMBLE_VARIATIONS, get_asset_type
from backend.models.xai_explanation_engine import XAIEngine, load_xai_engine
from backend.models.data_pipeline import download_data, compute_features, get_feature_cols, prepare_data_multi_window
from backend.models.platt_scaling_calibration_v2 import load_calibrator
from backend.services.xai_update_service import XAIUpdateService
from backend.daos.activo_dao import ActivoDAO
from backend.daos.explicacion_xai_dao import ExplicacionXAIDAO


def generar_explicacion_para_ticker(
    ticker: str,
    version_modelo: str = "Phase3",
    seed_modelo: int = 42,
    save_to_db: bool = True
) -> bool:
    """
    Genera explicación XAI para un ticker.
    
    Steps:
    1. Cargar modelo XGBoost entrenado
    2. Obtener datos test
    3. Hacer predicción en última ventana
    4. Generar explicación XAI
    5. Guardar en BD
    
    Args:
        ticker: Ticker del activo
        version_modelo: Versión del modelo
        seed_modelo: Seed usado en entrenamiento
        save_to_db: Si guardar en BD
    
    Returns:
        True si exitoso
    """
    
    logger.info(f"\n{'='*80}")
    logger.info(f"GENERANDO EXPLICACIÓN XAI: {ticker}")
    logger.info(f"{'='*80}")
    
    try:
        # 1️⃣ Cargar configuración
        config = get_config(ticker)
        max_window_size = config.get("window_size", 30)
        
        # 2️⃣ Cargar modelo XGBoost
        xgb_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost.pkl")
        if not os.path.exists(xgb_path):
            logger.error(f"❌ Modelo no encontrado: {xgb_path}")
            return False
        
        with open(xgb_path, "rb") as f:
            xgb_model = pickle.load(f)
        logger.info(f"✓ XGBoost model cargado para {ticker}")
        
        # 3️⃣ Cargar feature names
        feature_names = []
        feature_names_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_feature_names.pkl")
        if os.path.exists(feature_names_path):
            with open(feature_names_path, "rb") as f:
                feature_names = pickle.load(f)
        logger.info(f"✓ {len(feature_names)} feature names cargados")
        
        # 4️⃣ Obtener datos recientes (usar misma configuración que training)
        logger.info(f"Descargando datos para {ticker}...")
        raw_df = download_data(ticker)
        asset_type = get_asset_type(ticker)
        include_market_context = (asset_type == "volatile")
        feat_df = compute_features(raw_df, include_market_context=include_market_context, ticker=ticker)
        feature_cols = get_feature_cols(ticker)
        
        if len(feat_df) < max_window_size:
            logger.error(f"❌ Datos insuficientes: {len(feat_df)} < {max_window_size}")
            return False
        
        logger.info(f"✓ Datos descargados: {len(feat_df)} filas")
        
        # 5️⃣ Preparar última ventana con agregación como training
        feature_cols = get_feature_cols(ticker)
        # Filtrar solo features que existen en feat_df (algunos no se crean si include_market_context=False)
        feature_cols = [c for c in feature_cols if c in feat_df.columns]
        logger.info(f"   Features disponibles: {len(feature_cols)} de {len(get_feature_cols(ticker))}")
        
        scaler_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_scaler.pkl")
        if not os.path.exists(scaler_path):
            logger.warning(f"⚠️ Scaler no encontrado para {ticker}")
            return False
        
        with open(scaler_path, "rb") as f:
            scaler = pickle.load(f)
        logger.info(f"✓ Scaler cargado")
        
        # Preparar ventana: últimos max_window_size rows
        last_window_raw = feat_df[feature_cols].values[-max_window_size:]  # Shape: (max_window_size, n_features)
        last_window_scaled = scaler.transform(last_window_raw)  # Shape: (max_window_size, n_features)
        
        # Aplicar la misma agregación que en training:
        # [last, mean, std, trend] = 4 * n_features
        n_features = last_window_scaled.shape[1]
        last_vals = last_window_scaled[-1, :]  # últimos valores (shape: n_features)
        mean_vals = np.mean(last_window_scaled, axis=0)  # promedio de la ventana
        std_vals = np.std(last_window_scaled, axis=0)  # desv estándar
        trend_vals = last_window_scaled[-1, :] - last_window_scaled[0, :]  # cambio total
        
        # Concatenar: shape (1, 4 * n_features)
        X_test = np.concatenate([last_vals, mean_vals, std_vals, trend_vals]).reshape(1, -1).astype(np.float32)
        logger.info(f"✓ Ventana preparada: shape {X_test.shape} (agregación: last+mean+std+trend)")
        
        # 6️⃣ Hacer predicción
        y_pred = xgb_model.predict(X_test)[0]  # 0=BAJISTA, 1=LATERAL, 2=ALCISTA
        y_proba = xgb_model.predict_proba(X_test)[0]
        
        # Convertir a tendencia
        senal_prediccion = {0: "BAJISTA", 1: "LATERAL", 2: "ALCISTA"}.get(y_pred, "LATERAL")
        
        # 🔧 APLICAR CALIBRACIÓN PLATT SCALING
        calibrator = load_calibrator(ticker)
        if calibrator is not None:
            logger.info(f"📊 Aplicando Platt Scaling para {ticker}")
            # Probabilidades máximas crudas
            y_conf_raw = np.max(y_proba).reshape(1, 1)
            # Aplicar calibrador
            y_conf_calibrated = calibrator.predict_proba(y_conf_raw)[0, 1]
            confianza_prediccion = float(y_conf_calibrated)
            logger.info(f"   Confianza raw: {float(np.max(y_proba)):.2%} → calibrada: {confianza_prediccion:.2%}")
        else:
            confianza_prediccion = float(np.max(y_proba))
            logger.warning(f"⚠️  No calibrator found, using raw confidence: {confianza_prediccion:.2%}")
        
        logger.info(f"✓ Predicción: {senal_prediccion} (confianza: {confianza_prediccion:.2%})")
        
        # 8️⃣ Crear XAI Engine
        xai_engine = XAIEngine(xgb_model=xgb_model, feature_names=feature_names)
        if not xai_engine.explainer_shap:
            logger.warning(f"⚠️ SHAP no disponible, usando explicaciones básicas")
        
        logger.info("✓ XAI Engine inicializado")
        
        # 9️⃣ Generar explicación
        explicacion = xai_engine.explain_prediction(
            X_instance=X_test[0],
            ticker=ticker,
            senal_prediccion=senal_prediccion,
            confianza=confianza_prediccion,
            X_test=X_test,
            feature_names=feature_names
        )
        
        logger.info(f"✓ Explicación generada")
        logger.info(f"   - SHAP values: {len(explicacion.get('shap_valores', []))} features")
        logger.info(f"   - Top 20 features: {len(explicacion.get('features_top20', []))} features")
        logger.info(f"   - Contribucion features: {len(explicacion.get('contribucion_features', {}))} features")
        
        # 🔟 Guardar en BD
        if save_to_db:
            success = ExplicacionXAIDAO.crear(
                ticker=ticker,
                shap_valores=explicacion.get("shap_valores", []),
                shap_grafico=explicacion.get("shap_grafico_base64", ""),
                features_top20=explicacion.get("features_top20", []),
                contribucion_features=explicacion.get("contribucion_features", {}),
                senal_prediccion=senal_prediccion,
                confianza_prediccion=confianza_prediccion,
                version_modelo=version_modelo,
                seed_modelo=seed_modelo,
                pesos_atencion=explicacion.get("pesos_atencion", [])
            )
            
            if success:
                logger.info(f"✅ EXPLICACIÓN GUARDADA EN BD PARA {ticker}")
            else:
                logger.error(f"❌ Error guardando explicación para {ticker}")
                return False
        else:
            logger.info(f"✓ Explicación generada (no guardada, --no-db)")
        
        # 1️⃣1️⃣ Mostrar resumen
        print(f"\n{'='*80}")
        print(f"RESUMEN: {ticker}")
        print(f"{'='*80}")
        print(f"Señal: {senal_prediccion}")
        print(f"Confianza: {confianza_prediccion:.2%}")
        print(f"\nTop 5 Features más importantes:")
        for feat in explicacion.get("features_top20", [])[:5]:
            print(f"  - {feat['feature_name']}: importancia={feat.get('importancia', 0):.4f}")
        print(f"{'='*80}\n")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Error en generar_explicacion_para_ticker({ticker}): {e}")
        import traceback
        traceback.print_exc()
        return False


def generar_explicaciones_todos():
    """Genera explicaciones para todos los tickers."""
    
    logger.info("\n" + "="*80)
    logger.info("GENERANDO EXPLICACIONES XAI PARA TODOS LOS TICKERS")
    logger.info("="*80 + "\n")
    
    # Cargar tickers desde BD
    tickers_dict = get_tickers_from_database()
    all_tickers = tickers_dict.get("stable", []) + tickers_dict.get("volatile", [])
    
    logger.info(f"Total tickers: {len(all_tickers)}")
    
    resultados = {"exitosas": 0, "fallidas": 0, "tickers": []}
    
    for ticker in all_tickers:
        try:
            success = generar_explicacion_para_ticker(ticker)
            if success:
                resultados["exitosas"] += 1
                resultados["tickers"].append({"ticker": ticker, "status": "✅"})
            else:
                resultados["fallidas"] += 1
                resultados["tickers"].append({"ticker": ticker, "status": "❌"})
        
        except Exception as e:
            logger.error(f"❌ Error inesperado en {ticker}: {e}")
            resultados["fallidas"] += 1
            resultados["tickers"].append({"ticker": ticker, "status": "❌ Exception"})
    
    # Resumen final
    logger.info("\n" + "="*80)
    logger.info("RESUMEN FINAL")
    logger.info("="*80)
    logger.info(f"✅ Explicaciones exitosas: {resultados['exitosas']}")
    logger.info(f"❌ Explicaciones fallidas: {resultados['fallidas']}")
    logger.info(f"Total: {resultados['exitosas'] + resultados['fallidas']}")
    
    for item in resultados["tickers"]:
        logger.info(f"  {item['status']} {item['ticker']}")
    
    logger.info("="*80 + "\n")
    
    return resultados["exitosas"] == len(all_tickers)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate XAI explanations for trained models"
    )
    parser.add_argument("--ticker", type=str, help="Generate for specific ticker (e.g., AAPL)")
    parser.add_argument("--all", action="store_true", help="Generate for all tickers")
    parser.add_argument("--no-db", action="store_true", help="Don't save to database")
    
    args = parser.parse_args()
    
    # Determinar qué hacer
    if args.ticker:
        # Specific ticker
        success = generar_explicacion_para_ticker(
            args.ticker,
            save_to_db=not args.no_db
        )
        sys.exit(0 if success else 1)
    
    elif args.all:
        # All tickers
        success = generar_explicaciones_todos()
        sys.exit(0 if success else 1)
    
    else:
        # Mostrar ayuda
        parser.print_help()
        sys.exit(1)
