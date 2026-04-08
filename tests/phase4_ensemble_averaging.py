"""
PHASE 4: ENSEMBLE AVERAGING WITH MULTIPLE RANDOM SEEDS (FIXED)
==============================================================

Objetivo: Entrenar 3 modelos XGBoost con DIFERENTES random seeds y hacer
ensemble de sus predicciones para reducir varianza y mejorar generalización.

Estrategia:
1. Entrenar 3 modelos por ticker con SEEDS DIFERENTES (42, 123, 456)
2. Promediar probabilidades de los 3 modelos
3. Aplicar v4 Recall-Target calibration con ensemble probs
4. Comparar resultados contra Phase 3 (single model seed=42)
5. Guardar nuevas confianzas en BD SOLO si hay mejora

Tiempo estimado: ~120-180 minutos (3× más lento que single model)
Esperado: +0.5-1.5% mejora en BA, +validación de robustez
"""

import os
import pickle
import numpy as np
from typing import Dict, List
import time

from backend.models.config import (
    get_tickers_from_database,
    TICKERS,
    get_config,
    get_asset_type,
    ENSEMBLE_VARIATIONS,
    get_feature_cols,
    SAVED_MODELS_DIR,
)
from backend.models.data_pipeline import prepare_data_multi_window
from backend.models.xgboost_model import train_xgboost
from backend.daos.activo_dao import ActivoDAO
from sklearn.metrics import balanced_accuracy_score, confusion_matrix


def get_ensemble_predictions(ticker: str, X_test: np.ndarray, seeds: List[int]) -> np.ndarray:
    """
    Obtiene predicciones de todos los modelos en el ensemble y las promedia.
    
    Returns: Array de probabilidades promediadas [n_samples, 2]
    """
    all_proba = []
    
    for seed in seeds:
        model_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost_seed{seed}.pkl")
        if os.path.exists(model_path):
            with open(model_path, "rb") as f:
                model = pickle.load(f)
            
            # Predicción de este modelo
            proba = model.predict_proba(X_test)  # shape: (n_samples, 2)
            all_proba.append(proba)
    
    if not all_proba:
        return None
    
    # Promediar probabilidades
    ensemble_proba = np.mean(all_proba, axis=0)  # shape: (n_samples, 2)
    return ensemble_proba


def apply_v4_threshold_calibration(y_prob: np.ndarray, y_val: np.ndarray, y_test: np.ndarray) -> Dict:
    """
    Aplica v4 Recall-Target con probabilidades del ensemble.
    """
    TARGET_RECALL = 0.50
    TOLERANCE = 0.10
    
    best_ba = -1
    best_down = np.percentile(y_prob, 25)
    best_up = np.percentile(y_prob, 75)
    best_recall_up = 0
    best_distance_to_target = float('inf')
    
    min_prob = np.percentile(y_prob, 5)
    max_prob = np.percentile(y_prob, 95)
    threshold_candidates = np.linspace(min_prob, max_prob, 60)
    
    for up_threshold in threshold_candidates:
        for down_threshold in np.linspace(min_prob, min_prob * 0.9, 15):
            if down_threshold >= up_threshold - 0.02:
                continue
            
            y_pred_candidate = np.ones(len(y_prob), dtype=int)
            y_pred_candidate[y_prob[:, 1] >= up_threshold] = 2      # ALCISTA
            y_pred_candidate[y_prob[:, 1] <= down_threshold] = 0    # BAJISTA
            
            ba_candidate = balanced_accuracy_score(y_val, y_pred_candidate)
            
            cm = confusion_matrix(y_val, y_pred_candidate, labels=[0, 1, 2])
            tp_candidate = cm[2, 2]
            fp_candidate = np.sum(cm[:, 2]) - tp_candidate
            fn_candidate = np.sum(cm[2, :]) - tp_candidate
            recall_candidate = tp_candidate / (tp_candidate + fn_candidate) if (tp_candidate + fn_candidate) > 0 else 0
            
            distance_to_target = abs(recall_candidate - TARGET_RECALL)
            
            if distance_to_target <= TOLERANCE:
                if distance_to_target < best_distance_to_target or \
                   (distance_to_target == best_distance_to_target and ba_candidate > best_ba):
                    best_ba = ba_candidate
                    best_down = down_threshold
                    best_up = up_threshold
                    best_recall_up = recall_candidate
                    best_distance_to_target = distance_to_target
    
    return {
        "down_threshold": float(best_down),
        "up_threshold": float(best_up),
        "ba": float(best_ba),
        "recall": float(best_recall_up),
    }


def main():
    print("\n" + "="*80)
    print("[*] PHASE 4: ENSEMBLE AVERAGING WITH MULTIPLE RANDOM SEEDS")
    print("="*80)
    print("\nStrategy:")
    print("  1. Train 3 models per ticker with DIFFERENT SEEDS (42, 123, 456)")
    print("  2. Average predictions from 3 models ← Reduce variance")
    print("  3. Apply v4 Recall-Target calibration with ensemble")
    print("  4. Compare BA/Confidence against Phase 3 (single seed=42)")
    print("  5. Update BD ONLY for tickers with improvement +0.5pp")
    print("  6. Expected: +0.5-1.5% BA, more robust predictions")
    print("\n" + "-"*80 + "\n")
    
    tickers_config = get_tickers_from_database()
    all_tickers = tickers_config["stable"] + tickers_config["volatile"]
    
    if not all_tickers:
        all_tickers = TICKERS["stable"] + TICKERS["volatile"]
    
    SEEDS = [42, 123, 456]
    results_phase4 = {}
    total_start = time.time()
    
    # STEP 1: Train ensemble models
    print("STEP 1: TRAINING 3 MODELS PER TICKER (DIFFERENT RANDOM SEEDS)")
    print("-" * 80)
    
    for ticker in sorted(all_tickers):
        print(f"\n{ticker}:")
        ticker_start = time.time()
        
        try:
            config = get_config(ticker)
            asset_type = get_asset_type(ticker)
            variations = ENSEMBLE_VARIATIONS[asset_type]
            feature_cols = get_feature_cols(ticker)
            
            # Preparar datos una sola vez
            unique_window_sizes = list(set(v["window_size"] for v in variations))
            all_data = prepare_data_multi_window(ticker, config, unique_window_sizes)
            max_ws = max(unique_window_sizes)
            data = all_data[max_ws]
            
            # Entrenar 3 modelos con DIFERENTES SEEDS
            print(f"   Train 3 models with seeds: {SEEDS}")
            for i, seed in enumerate(SEEDS, 1):
                print(f"     [{i}/3] seed={seed}...", end=" ", flush=True)
                
                # Train with specific seed
                xgb_metrics = train_xgboost(ticker, data, feature_cols, asset_type=asset_type, seed=seed)
                
                # Save model with seed in name
                model_path_seed = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost_seed{seed}.pkl")
                model_path_default = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost.pkl")
                
                if os.path.exists(model_path_default):
                    with open(model_path_default, "rb") as f:
                        model = pickle.load(f)
                    with open(model_path_seed, "wb") as f:
                        pickle.dump(model, f)
                
                print("✓")
            
            elapsed = time.time() - ticker_start
            print(f"   ✓ Completed in {elapsed:.1f}s")
            
        except Exception as e:
            print(f"   ✗ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n✓ Step 1 completed")
    
    # STEP 2: Evaluate ensemble predictions
    print("\n\nSTEP 2: ENSEMBLE PREDICTION & v4 CALIBRATION")
    print("-" * 80)
    
    for ticker in sorted(all_tickers):
        print(f"\n{ticker}:")
        
        try:
            config = get_config(ticker)
            asset_type = get_asset_type(ticker)
            variations = ENSEMBLE_VARIATIONS[asset_type]
            feature_cols = get_feature_cols(ticker)
            
            # Prepare data
            unique_window_sizes = list(set(v["window_size"] for v in variations))
            all_data = prepare_data_multi_window(ticker, config, unique_window_sizes)
            max_ws = max(unique_window_sizes)
            data = all_data[max_ws]
            
            X_val = data["X_val"].numpy()
            X_test = data["X_test"].numpy()
            y_val = data["y_val"].numpy()
            y_test = data["y_test"].numpy()
            
            # Feature aggregation (same as train_xgboost)
            def build_xgb_features(X_tensor):
                X = X_tensor if isinstance(X_tensor, np.ndarray) else X_tensor.numpy()
                last = X[:, -1, :]
                mean = X.mean(axis=1)
                std = X.std(axis=1)
                trend = X[:, -1, :] - X[:, 0, :]
                return np.concatenate([last, mean, std, trend], axis=1)
            
            X_val_features = build_xgb_features(X_val)
            X_test_features = build_xgb_features(X_test)
            
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
            
            # Get ensemble predictions
            y_prob_val = get_ensemble_predictions(ticker, X_val_features, SEEDS)
            y_prob_test = get_ensemble_predictions(ticker, X_test_features, SEEDS)
            
            if y_prob_val is None or y_prob_test is None:
                print(f"   ✗ Could not generate ensemble predictions")
                continue
            
            # Apply v4 calibration
            calib_result = apply_v4_threshold_calibration(
                y_prob_val, y_val_ternary, y_test_ternary
            )
            
            # Predict with calibrated thresholds
            y_pred_ternary = np.ones(len(y_test_ternary), dtype=int)
            y_pred_ternary[y_prob_test[:, 1] >= calib_result["up_threshold"]] = 2
            y_pred_ternary[y_prob_test[:, 1] <= calib_result["down_threshold"]] = 0
            
            # Calculate metrics
            ba_ensemble = float(balanced_accuracy_score(y_test_ternary, y_pred_ternary))
            max_probs = np.max(y_prob_test, axis=1)
            confidence_ensemble = float(np.mean(max_probs))
            
            results_phase4[ticker] = {
                "ba": ba_ensemble,
                "confidence": confidence_ensemble,
                "thresholds": calib_result,
            }
            
            print(f"   ✓ Ensemble BA: {ba_ensemble:.2%}")
            print(f"   ✓ Ensemble Confidence: {confidence_ensemble:.2%}")
            
        except Exception as e:
            print(f"   ✗ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n✓ Step 2 completed")
    
    # STEP 3: Compare with Phase 3
    print("\n\n" + "="*80)
    print("COMPARISON: PHASE 3 (seed=42) vs PHASE 4 (ensemble)")
    print("="*80)
    
    # Get Phase 3 values from BD
    phase3_results = {}
    activos = ActivoDAO.obtener_todos()
    for activo in activos:
        if hasattr(activo, 'ticker') and hasattr(activo, 'confianza_bygru'):
            phase3_results[activo.ticker] = float(activo.confianza_bygru) if activo.confianza_bygru else 0
    
    print(f"\n{'Ticker':<10} {'Phase 3':<12} {'Phase 4':<12} {'Diff':<12} {'Decision':<15}")
    print("-" * 65)
    
    improvements = []
    update_count = 0
    for ticker in sorted(all_tickers):
        if ticker in results_phase4 and ticker in phase3_results:
            phase3 = phase3_results[ticker]
            phase4 = results_phase4[ticker]["confidence"]
            diff = phase4 - phase3
            
            # Threshold: +0.5pp (0.005) for significant improvement
            if diff > 0.005:
                decision = "✅ UPDATE"
                update_count += 1
            elif diff > -0.005:
                decision = "➡️  KEEP P3"
            else:
                decision = "❌ P3 BETTER"
            
            print(f"{ticker:<10} {phase3:.2%}     {phase4:.2%}     {diff:+.2%}     {decision:<15}")
            improvements.append(diff)
    
    if improvements:
        avg_improvement = np.mean(improvements)
        print("-" * 65)
        print(f"{'AVERAGE':<10} {'':12} {'':12} {avg_improvement:+.2%}{'':5} (OVERALL VERDICT)")
    
    print("\n" + "="*80)
    print("FINAL DECISION & ACTION")
    print("="*80)
    
    if improvements and avg_improvement > 0.005:  # > 0.5pp average
        print(f"\n✅ PHASE 4 RECOMMENDED: +{avg_improvement:.2%} average improvement")
        print(f"\nAction: Update {update_count}/{len(results_phase4)} tickers in BD")
        print("        (only those with >+0.5pp improvement)")
        
        # Update BD - ONLY for tickers with improvement
        for ticker, result in results_phase4.items():
            if ticker in phase3_results:
               if result["confidence"] > phase3_results[ticker] + 0.005:
                    try:
                        update_data = {"confianza_bygru": result["confidence"]}
                        ActivoDAO.actualizar(ticker, update_data)
                        diff = result["confidence"] - phase3_results[ticker]
                        print(f"  ✓ {ticker}: {phase3_results[ticker]:.2%} → {result['confidence']:.2%} ({diff:+.2%})")
                    except Exception as e:
                        print(f"  ✗ {ticker}: Failed - {e}")
    
    elif improvements and avg_improvement > -0.005:  # Within margin
        print(f"\n⚠️  PHASE 4 NEUTRAL: {avg_improvement:+.2%} (within ±0.5pp)")
        print("\nRecommendation: Keep Phase 3")
        print("  Rationale: Ensemble adds complexity without clear benefit")
        print("  Action: No changes to BD, continue with Phase 3 config")
    
    else:
        print(f"\n❌ PHASE 4 NOT RECOMMENDED: {avg_improvement:+.2%} worse")
        print("\nRecommendation: Keep Phase 3")
        print("  Rationale: Ensemble averaging decreases performance")
        print("  Action: No changes to BD, continue with Phase 3 config")
    
    total_elapsed = time.time() - total_start
    print(f"\n[✓] Phase 4 execution completed in {total_elapsed/60:.1f} minutes")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
