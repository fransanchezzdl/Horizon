"""
Entrenamiento de meta-model de Ensemble Stacking.

Función para ser llamada DESPUÉS de train_ensemble().
Genera predicciones de validación y entrena meta-model LightGBM.
"""

import os
import torch
import numpy as np
import pickle
import json
from typing import Tuple
from datetime import datetime, timezone

from .ensemble import load_ensemble, load_scaler
from .data_pipeline import prepare_data_multi_window, get_feature_cols
from .ensemble_stacking import EnsembleStackingMetaModel
from .config import SAVED_MODELS_DIR, get_config, get_asset_type, ENSEMBLE_VARIATIONS


def train_stacking_metalearner(ticker: str, verbose: bool = True) -> dict:
    """
    Entrena meta-model de Ensemble Stacking para combinar BiGRU + XGBoost.
    
    Esta función debe ejecutarse DESPUÉS de train_ensemble(ticker).
    
    Flujo:
    1. Carga modelos BiGRU entrenados
    2. Carga XGBoost entrenado
    3. Genera predicciones en validation set usando ambos
    4. Entrena meta-model LightGBM
    5. Guarda meta-model para inferencia
    
    Args:
        ticker: Símbolo del activo
        verbose: Si mostrar logs
        
    Returns:
        Dict con métricas del meta-model
    """
    if verbose:
        print(f"\n{'='*60}")
        print(f"🔗 Entrenando Meta-Model de Stacking para {ticker}")
        print(f"{'='*60}")
    
    # Configuración
    config = get_config(ticker)
    asset_type = get_asset_type(ticker)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    variations = ENSEMBLE_VARIATIONS[asset_type]
    
    # Verificar que los modelos existen
    for model_idx in range(len(variations)):
        model_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_model_{model_idx}.pth")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Modelo BiGRU {model_idx} no encontrado: {model_path}")
    
    xgboost_model_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost.pkl")
    if not os.path.exists(xgboost_model_path):
        raise FileNotFoundError(f"Modelo XGBoost no encontrado: {xgboost_model_path}")
    
    # ── Preparar datos de validación ────────────────────────────────────────
    if verbose:
        print(f"\n📊 Preparando datos de validación...")
    
    unique_window_sizes = list(set(v["window_size"] for v in variations))
    all_data = prepare_data_multi_window(ticker, config, unique_window_sizes)
    
    # Usar window_size mayor para tener más contexto (igual que XGBoost)
    max_ws = max(unique_window_sizes)
    val_data = all_data[max_ws]
    
    X_val = val_data["X_val"]  # Tensor (n_val, seq_len, features)
    y_val = val_data["y_val"]  # Tensor (n_val,) clases
    X_test = val_data["X_test"]  # Tensor (n_test, seq_len, features)
    y_test = val_data["y_test"]  # Tensor (n_test,) clases
    
    # ── Generar predicciones de BiGRU ────────────────────────────────────────
    if verbose:
        print(f"🧠 Generando predicciones de BiGRU...")
    
    models = load_ensemble(ticker)  # Carga todos los modelos
    
    # Predicciones en validation set
    bigru_proba_val_list = []
    for model in models:
        proba = _get_bigru_proba(model, X_val, device)
        bigru_proba_val_list.append(proba)  # (n_val, 3)
    
    # Promedio de predicciones
    bigru_proba_val = np.mean(bigru_proba_val_list, axis=0)  # (n_val, 3)
    
    # Predicciones en test set
    bigru_proba_test_list = []
    for model in models:
        proba = _get_bigru_proba(model, X_test, device)
        bigru_proba_test_list.append(proba)
    
    bigru_proba_test = np.mean(bigru_proba_test_list, axis=0)
    
    # ── Generar predicciones de XGBoost ──────────────────────────────────────
    if verbose:
        print(f"🌳 Generando predicciones de XGBoost...")
    
    import xgboost as xgb
    xgb_model = xgb.Booster(model_file=xgboost_model_path)
    
    # Convertir datos a DMatrix
    feature_cols = get_feature_cols(ticker)
    
    # X_val es tensor (n, seq_len, features) → necesita flatten
    X_val_np = X_val.cpu().numpy() if isinstance(X_val, torch.Tensor) else X_val
    X_test_np = X_test.cpu().numpy() if isinstance(X_test, torch.Tensor) else X_test
    y_val_np = y_val.cpu().numpy() if isinstance(y_val, torch.Tensor) else y_val
    y_test_np = y_test.cpu().numpy() if isinstance(y_test, torch.Tensor) else y_test
    
    # Flatten secuencias
    n_val_seq, seq_len, n_feat = X_val_np.shape
    X_val_flat = X_val_np.reshape(n_val_seq, -1)
    X_test_flat = X_test_np.reshape(len(X_test_np), -1)
    
    dval = xgb.DMatrix(X_val_flat)
    dtest = xgb.DMatrix(X_test_flat)
    
    # Predicciones (retorna probabilidades para 3 clases)
    xgb_proba_val = xgb_model.predict(dval)  # (n_val, 3)
    xgb_proba_test = xgb_model.predict(dtest)  # (n_test, 3)
    
    xgb_pred_val = np.argmax(xgb_proba_val, axis=1)  # (n_val,)
    xgb_pred_test = np.argmax(xgb_proba_test, axis=1)  # (n_test,)
    
    # ── Entrenar Meta-Model ──────────────────────────────────────────────────
    if verbose:
        print(f"\n🔗 Entrenando Meta-Model...")
    
    meta_model = EnsembleStackingMetaModel(verbose=verbose)
    
    # Crear features de stacking
    X_val_stacking = meta_model.create_stacking_features(
        bigru_proba_val, xgb_pred_val, xgb_proba_val
    )
    X_test_stacking = meta_model.create_stacking_features(
        bigru_proba_test, xgb_pred_test, xgb_proba_test
    )
    
    # Entrenar
    metrics, y_pred_proba_test = meta_model.train_meta_model(
        X_val_stacking, y_val_np,
        X_test_stacking, y_test_np
    )
    
    # ── Guardar Meta-Model ───────────────────────────────────────────────────
    meta_model_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_stacking_metalearner.pkl")
    with open(meta_model_path, "wb") as f:
        pickle.dump(meta_model.meta_model, f)
    
    if verbose:
        print(f"💾 Meta-model guardado en {meta_model_path}")
    
    # ── Log Feature Importance ───────────────────────────────────────────────
    if verbose:
        importance = meta_model.get_feature_importance()
        print(f"\n📊 Feature Importance del Meta-Model:")
        for feat, imp in sorted(importance.items(), key=lambda x: x[1], reverse=True):
            print(f"   {feat:20s}: {imp:.4f}")
    
    # ── Guardar informe ──────────────────────────────────────────────────────
    report = {
        "ticker": ticker,
        "stacking_metalearner": "LightGBM",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "meta_model_metrics": {
            "test_accuracy": float(metrics["accuracy"]),
            "test_f1_weighted": float(metrics["f1_weighted"]),
            "n_estimators": metrics["n_estimators"],
        },
        "feature_importance": meta_model.get_feature_importance(),
    }
    
    report_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_stacking_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    
    if verbose:
        print(f"📄 Reporte guardado en {report_path}\n")
    
    return metrics


def _get_bigru_proba(model, X_tensor: torch.Tensor, device) -> np.ndarray:
    """Helper para obtener probabilidades de BiGRU"""
    model.eval()
    with torch.no_grad():
        X_tensor = X_tensor.to(device)
        logits = model(X_tensor)
        proba = torch.softmax(logits, dim=1)
    return proba.cpu().numpy()


if __name__ == "__main__":
    # Test: entrenar stacking para GC=F (después de train_ensemble)
    print("Testing stacking metalearner training...")
    try:
        metrics = train_stacking_metalearner("GC=F", verbose=True)
        print(f"\n✅ Stacking metalearner entrenado exitosamente!")
        print(f"   Accuracy: {metrics['accuracy']:.2%}")
        print(f"   F1: {metrics['f1_weighted']:.4f}")
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("   Ejecuta train_ensemble('GC=F') primero")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
