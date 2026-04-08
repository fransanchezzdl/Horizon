"""
OPTIMIZATION: Per-Type Threshold Calibration
==============================================

Objetivo: Usar targets de recall diferentes para STABLE vs VOLATILE.

Rationale:
- STABLE (3.42% mejor rendimiento): Ser más conservativo → target recall 48%
- VOLATILE (inconsistente, 3 tickers bajo 60%): Ser más agresivo → target recall 52%

Esto permite que cada segmento optimice según su característica natural,
sin reentrenamiento (solo recalibración de thresholds).

Tiempo estimado: 15 minutos
Esperado: +0.5-1% mejora en VOLATILE, +0.2-0.3% en STABLE
"""

import numpy as np
import pickle
import os
from typing import Dict, Tuple

from backend.models.config import (
    get_tickers_from_database,
    TICKERS,
    get_asset_type,
    SAVED_MODELS_DIR,
)
from backend.daos.activo_dao import ActivoDAO
from backend.models.data_pipeline import prepare_data_multi_window
from backend.models.config import get_config, ENSEMBLE_VARIATIONS, get_feature_cols
from sklearn.metrics import balanced_accuracy_score, confusion_matrix


def apply_per_type_calibration(
    ticker: str,
    X_val: np.ndarray,
    X_test: np.ndarray,
    y_val: np.ndarray,
    y_test: np.ndarray,
    model_path: str,
    asset_type: str = "stable"
) -> Dict:
    """
    Aplica calibración de thresholds específica por tipo de activo.
    
    STABLE: Target recall = 48% (más conservador)
    VOLATILE: Target recall = 52% (más agresivo)
    """
    
    # Target recall según tipo
    TARGET_RECALL_STABLE = 0.48
    TARGET_RECALL_VOLATILE = 0.52
    TOLERANCE = 0.10
    
    target_recall = TARGET_RECALL_VOLATILE if asset_type == "volatile" else TARGET_RECALL_STABLE
    
    # Cargar modelo
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    
    # Feature aggregation
    def build_xgb_features(X_tensor):
        X = X_tensor if isinstance(X_tensor, np.ndarray) else X_tensor.numpy()
        last = X[:, -1, :]
        mean = X.mean(axis=1)
        std = X.std(axis=1)
        trend = X[:, -1, :] - X[:, 0, :]
        return np.concatenate([last, mean, std, trend], axis=1)
    
    X_val_features = build_xgb_features(X_val)
    X_test_features = build_xgb_features(X_test)
    
    # Predicciones
    y_prob_val = model.predict_proba(X_val_features)
    y_prob_test = model.predict_proba(X_test_features)
    
    # Calibración v4 Recall-Target con target específico por tipo
    best_ba = -1
    best_down = np.percentile(y_prob_val, 25)
    best_up = np.percentile(y_prob_val, 75)
    best_recall = 0
    best_distance_to_target = float('inf')
    
    min_prob = np.percentile(y_prob_val, 5)
    max_prob = np.percentile(y_prob_val, 95)
    threshold_candidates = np.linspace(min_prob, max_prob, 60)
    
    for up_threshold in threshold_candidates:
        for down_threshold in np.linspace(min_prob, min_prob * 0.9, 15):
            if down_threshold >= up_threshold - 0.02:
                continue
            
            y_pred_candidate = np.ones(len(y_prob_val), dtype=int)
            y_pred_candidate[y_prob_val[:, 1] >= up_threshold] = 2      # ALCISTA
            y_pred_candidate[y_prob_val[:, 1] <= down_threshold] = 0    # BAJISTA
            
            ba_candidate = balanced_accuracy_score(y_val, y_pred_candidate)
            
            cm = confusion_matrix(y_val, y_pred_candidate, labels=[0, 1, 2])
            tp_candidate = cm[2, 2]
            fn_candidate = np.sum(cm[2, :]) - tp_candidate
            recall_candidate = tp_candidate / (tp_candidate + fn_candidate) if (tp_candidate + fn_candidate) > 0 else 0
            
            distance_to_target = abs(recall_candidate - target_recall)
            
            if distance_to_target <= TOLERANCE:
                if distance_to_target < best_distance_to_target or \
                   (distance_to_target == best_distance_to_target and ba_candidate > best_ba):
                    best_ba = ba_candidate
                    best_down = down_threshold
                    best_up = up_threshold
                    best_recall = recall_candidate
                    best_distance_to_target = distance_to_target
    
    # Predict on test con los thresholds calibrados
    y_pred_ternary = np.ones(len(y_test), dtype=int)
    y_pred_ternary[y_prob_test[:, 1] >= best_up] = 2
    y_pred_ternary[y_prob_test[:, 1] <= best_down] = 0
    
    ba_test = float(balanced_accuracy_score(y_test, y_pred_ternary))
    max_probs = np.max(y_prob_test, axis=1)
    confidence = float(np.mean(max_probs))
    
    return {
        "ba": ba_test,
        "confidence": confidence,
        "recall": float(best_recall),
        "target_recall": target_recall,
        "distance_to_target": float(best_distance_to_target),
        "thresholds": {
            "down": float(best_down),
            "up": float(best_up),
        }
    }


def main():
    print("\n" + "="*80)
    print("OPTIMIZATION: Per-Type Threshold Calibration")
    print("="*80)
    print("\nStrategy:")
    print("  STABLE:   Target recall = 48% (conservative, low churn)")
    print("  VOLATILE: Target recall = 52% (aggressive, high churn)")
    print("  Benefit:  Customize risk appetite by asset type")
    print("\n" + "-"*80 + "\n")
    
    # Cargar config
    tickers_config = get_tickers_from_database()
    all_tickers = tickers_config["stable"] + tickers_config["volatile"]
    
    # Cargar fase 3 actual desde BD
    phase3_results = {}
    activos = ActivoDAO.obtener_todos()
    for activo in activos:
        if hasattr(activo, 'ticker') and hasattr(activo, 'confianza_bygru'):
            phase3_results[activo.ticker] = float(activo.confianza_bygru) if activo.confianza_bygru else 0
    
    # Recalibrar cada ticker
    optimized_results = {}
    
    print("RECALIBRATION BY ASSET TYPE")
    print("-" * 80)
    print(f"\n{'Ticker':<10} {'Type':<12} {'Phase 3':<12} {'Optimized':<12} {'Δ':<10} {'Status'}")
    print("-" * 70)
    
    for ticker in sorted(all_tickers):
        asset_type = get_asset_type(ticker)
        
        try:
            # Preparar datos
            config = get_config(ticker)
            variations = ENSEMBLE_VARIATIONS[asset_type]
            feature_cols = get_feature_cols(ticker)
            
            unique_window_sizes = list(set(v["window_size"] for v in variations))
            all_data = prepare_data_multi_window(ticker, config, unique_window_sizes)
            max_ws = max(unique_window_sizes)
            data = all_data[max_ws]
            
            X_val = data["X_val"].numpy()
            X_test = data["X_test"].numpy()
            y_val = data["y_val"].numpy()
            y_test = data["y_test"].numpy()
            
            # Ternary target
            y_train_continuous = data.get("y_train_returns", data["y_train"].numpy()).ravel()
            y_val_continuous = data.get("y_val_returns", data["y_val"].numpy()).ravel()
            y_test_continuous = data.get("y_test_returns", data["y_test"].numpy()).ravel()
            
            down_threshold = np.percentile(y_train_continuous, 33.33)
            up_threshold = np.percentile(y_train_continuous, 66.67)
            
            def returns_to_classes(returns, down_th, up_th):
                classes = np.ones(len(returns), dtype=int)
                classes[returns <= down_th] = 0
                classes[returns >= up_th] = 2
                return classes
            
            y_val_ternary = returns_to_classes(y_val_continuous, down_threshold, up_threshold)
            y_test_ternary = returns_to_classes(y_test_continuous, down_threshold, up_threshold)
            
            # Calibración per-type
            model_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost.pkl")
            
            result = apply_per_type_calibration(
                ticker,
                X_val,
                X_test,
                y_val_ternary,
                y_test_ternary,
                model_path,
                asset_type=asset_type
            )
            
            optimized_results[ticker] = result
            
            # Comparar con Phase 3
            phase3_conf = phase3_results.get(ticker, 0)
            optimized_conf = result["confidence"]
            delta = optimized_conf - phase3_conf
            
            status = "✅ IMPROVEMENT" if delta > 0.005 else "➡️  NEUTRAL" if delta > -0.005 else "❌ WORSE"
            
            print(f"{ticker:<10} {asset_type:<12} {phase3_conf:.2%}       {optimized_conf:.2%}       {delta:+.2%}      {status}")
            
        except Exception as e:
            print(f"{ticker:<10} {asset_type:<12} ERROR: {e}")
    
    # Análisis de resultados
    print("\n" + "="*80)
    print("ANALYSIS")
    print("="*80)
    
    improvements = []
    for ticker in sorted(all_tickers):
        if ticker in optimized_results and ticker in phase3_results:
            delta = optimized_results[ticker]["confidence"] - phase3_results[ticker]
            improvements.append(delta)
    
    if improvements:
        avg_improvement = np.mean(improvements)
        print(f"\nAverage Change: {avg_improvement:+.2%}")
        print(f"Positive Changes: {sum(1 for d in improvements if d > 0)}/{len(improvements)}")
        print(f"Range: {min(improvements):+.2%} to {max(improvements):+.2%}")
    
    # Decision
    print("\n" + "="*80)
    print("DECISION")
    print("="*80)
    
    if improvements and avg_improvement > 0.003:  # > 0.3pp
        print(f"\n✅ RECOMMENDED: {avg_improvement:+.2%} average improvement")
        print("\nOption A: Update all tickers in BD (if ALL improved)")
        print("Option B: Update only improved tickers (selective)")
        print("\nUser decision needed...")
    elif improvements and avg_improvement > -0.003:
        print(f"\n⚠️  NEUTRAL: {avg_improvement:+.2%} (within margin)")
        print("\nCould update selectively or keep Phase 3...")
    else:
        print(f"\n❌ NOT RECOMMENDED: {avg_improvement:+.2%} worse")
        print("\nKeep Phase 3 configuration")
    
    print("\n" + "="*80 + "\n")
    
    return optimized_results, improvements


if __name__ == "__main__":
    results, improvements = main()
