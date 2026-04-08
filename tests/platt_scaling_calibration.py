"""
PROBABILITY CALIBRATION: Platt Scaling
========================================

Objetivo: Hacer que los scores de confianza sean HONESTOS.

Problema: Un modelo bien entrenado pero mal calibrado puede predecir 70%
cuando la probabilidad real es 55%, causando falsas confianzas.

Solución: Platt Scaling
- Entrenar sigmoid: P_calib = sigmoid(a * P_pred + b)
- Maximiza likelihood de verdaderas etiquetas
- NO cambia AUC-ROC, SOLO honestidad de probabilidades

Métricas:
- ECE (Expected Calibration Error): cuán honesto es el modelo
- Brier Score: error cuadrático medio de probabilidades
- Calibration Plots: gráficos de confiabilidad

Tiempo: 15-20 minutos
Beneficio: +honestidad en confianza (mejor decisiones downstream)
"""

import os
import pickle
import numpy as np
from typing import Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

from backend.models.config import (
    get_tickers_from_database,
    TICKERS,
    get_config,
    ENSEMBLE_VARIATIONS,
    get_feature_cols,
    SAVED_MODELS_DIR,
)
from backend.models.data_pipeline import prepare_data_multi_window
from backend.daos.activo_dao import ActivoDAO
from sklearn.metrics import brier_score_loss, roc_auc_score
from scipy.optimize import minimize


def expected_calibration_error(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    """
    Calcula Expected Calibration Error (ECE).
    ECE = promedio de |confianza - accuracy| en bins de probabilidad.
    
    ECE cercano a 0 = modelo bien calibrado
    """
    bins = np.linspace(0, 1, n_bins + 1)
    bin_centers = (bins[:-1] + bins[1:]) / 2
    bin_sums = np.zeros(n_bins)
    bin_true = np.zeros(n_bins)
    bin_total = np.zeros(n_bins)
    
    for i in range(len(y_prob)):
        bin_idx = np.digitize(y_prob[i], bins) - 1
        if 0 <= bin_idx < n_bins:
            bin_sums[bin_idx] += y_prob[i]
            bin_true[bin_idx] += y_true[i]
            bin_total[bin_idx] += 1
    
    ece = 0
    for i in range(n_bins):
        if bin_total[i] > 0:
            bin_accuracy = bin_true[i] / bin_total[i]
            bin_confidence = bin_sums[i] / bin_total[i]
            ece += (bin_total[i] / len(y_prob)) * abs(bin_confidence - bin_accuracy)
    
    return ece


def sigmoid(x: np.ndarray) -> np.ndarray:
    """Función sigmoid."""
    return 1 / (1 + np.exp(-x))


def calibration_function(p_pred: np.ndarray, params: Tuple[float, float]) -> np.ndarray:
    """Función de calibración: P_calib = sigmoid(a * P_pred + b)."""
    a, b = params
    # Clip probabilities para evitar overflow
    p_pred_clipped = np.clip(p_pred, 1e-6, 1 - 1e-6)
    logit_p = np.log(p_pred_clipped / (1 - p_pred_clipped))
    return sigmoid(a * logit_p + b)


def platt_scaling_loss(params: Tuple[float, float], y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """Negative log-likelihood para minimizar."""
    p_calib = calibration_function(y_prob, params)
    p_calib = np.clip(p_calib, 1e-6, 1 - 1e-6)
    return -np.mean(y_true * np.log(p_calib) + (1 - y_true) * np.log(1 - p_calib))


def fit_platt_scaling(y_true: np.ndarray, y_prob: np.ndarray) -> Tuple[float, float]:
    """
    Entrena parámetros a, b de Platt Scaling.
    Minimiza negative log-likelihood.
    """
    # Initial guess
    x0 = np.array([1.0, 0.0])
    
    # Minimize
    result = minimize(
        platt_scaling_loss,
        x0,
        args=(y_true, y_prob),
        method='BFGS'
    )
    
    return result.x[0], result.x[1]


def calibrate_predictions(ticker: str) -> Dict:
    """
    Aplica Platt Scaling a un ticker específico.
    """
    
    try:
        # Preparar datos
        from backend.models.config import get_asset_type
        
        config = get_config(ticker)
        asset_type = get_asset_type(ticker)
        variations = ENSEMBLE_VARIATIONS[asset_type]
        feature_cols = get_feature_cols(ticker)
        
        print(f"   Processing {ticker} ({asset_type})...", flush=True)
        
        unique_window_sizes = list(set(v["window_size"] for v in variations))
        all_data = prepare_data_multi_window(ticker, config, unique_window_sizes)
        max_ws = max(unique_window_sizes)
        data = all_data[max_ws]
        
        X_val = data["X_val"].numpy()
        X_test = data["X_test"].numpy()
        y_val = data["y_val"].numpy()
        y_test = data["y_test"].numpy()
        
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
        
        # Cargar modelo
        model_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost.pkl")
        with open(model_path, "rb") as f:
            model = pickle.load(f)
        
        # Predicciones (binary: prob de clase 1)
        y_prob_val = model.predict_proba(X_val_features)[:, 1]
        y_prob_test = model.predict_proba(X_test_features)[:, 1]
        y_test_binary = (y_test >= 1).astype(int)  # 0=BAJISTA, 1=LATERAL+ALCISTA
        
        # ANTES: Métricas sin calibración
        ece_before = expected_calibration_error(y_test_binary, y_prob_test)
        brier_before = brier_score_loss(y_test_binary, y_prob_test)
        
        # Entrenar Platt Scaling en validation set
        y_val_binary = (y_val >= 1).astype(int)
        a, b = fit_platt_scaling(y_val_binary, y_prob_val)
        
        # Aplicar calibración a test set
        y_prob_test_calib = calibration_function(y_prob_test, (a, b))
        
        # DESPUÉS: Métricas con calibración
        ece_after = expected_calibration_error(y_test_binary, y_prob_test_calib)
        brier_after = brier_score_loss(y_test_binary, y_prob_test_calib)
        
        # Confianza promedio
        max_probs_before = np.maximum(y_prob_test, 1 - y_prob_test)
        max_probs_after = np.maximum(y_prob_test_calib, 1 - y_prob_test_calib)
        
        confidence_before = float(np.mean(max_probs_before))
        confidence_after = float(np.mean(max_probs_after))
        
        return {
            "ticker": ticker,
            "a": float(a),
            "b": float(b),
            "ece_before": float(ece_before),
            "ece_after": float(ece_after),
            "brier_before": float(brier_before),
            "brier_after": float(brier_after),
            "confidence_before": confidence_before,
            "confidence_after": confidence_after,
        }
    
    except Exception as e:
        print(f"[ERROR] {ticker}: {e}")
        return None


def main():
    print("\n" + "="*80)
    print("PROBABILITY CALIBRATION: Platt Scaling")
    print("="*80)
    print("\nObjective: Make confidence scores HONEST")
    print("  • ECE (Expected Calibration Error) → 0 = perfect calibration")
    print("  • Brier Score → lower = better probability estimates")
    print("  • NO changes to ROC-AUC (only honesty)")
    print("\n" + "-"*80 + "\n")
    
    # Cargar tickers
    tickers_config = get_tickers_from_database()
    all_tickers = tickers_config["stable"] + tickers_config["volatile"]
    
    print(f"[DEBUG] Processing {len(all_tickers)} tickers: {all_tickers[:3]}... (truncated)\n", flush=True)
    
    # Calibrar cada ticker
    results = {}
    
    print("CALIBRATION RESULTS")
    print("-" * 80)
    print(f"\n{'Ticker':<10} {'ECE Before':<12} {'ECE After':<12} {'Improvement':<12} {'Status'}")
    print("-" * 70)
    
    for ticker in sorted(all_tickers):
        result = calibrate_predictions(ticker)
        
        if result:
            results[ticker] = result
            
            ece_before = result["ece_before"]
            ece_after = result["ece_after"]
            improvement = ece_before - ece_after  # negative is worse
            
            status = "✓ Better calibrated" if improvement > 0.001 else "≈ No change" if improvement > -0.001 else "✗ Worse"
            
            print(f"{ticker:<10} {ece_before:.4f}       {ece_after:.4f}       {improvement:+.4f}       {status}")
    
    # Análisis detallado
    print("\n" + "="*80)
    print("DETAILED ANALYSIS")
    print("="*80)
    
    if results:
        # Verificar calibración
        ece_improvements = [r["ece_before"] - r["ece_after"] for r in results.values()]
        brier_improvements = [r["brier_before"] - r["brier_after"] for r in results.values()]
        
        print(f"\n[ECE - Expected Calibration Error]")
        print(f"  Average improvement: {np.mean(ece_improvements):+.4f}")
        print(f"  Tickers improved:    {sum(1 for x in ece_improvements if x > 0)}/{len(ece_improvements)}")
        print(f"  Range:               {min(ece_improvements):+.4f} to {max(ece_improvements):+.4f}")
        
        print(f"\n[Brier Score - Probability MSE]")
        print(f"  Average improvement: {np.mean(brier_improvements):+.4f}")
        print(f"  Tickers improved:    {sum(1 for x in brier_improvements if x > 0)}/{len(brier_improvements)}")
        print(f"  Range:               {min(brier_improvements):+.4f} to {max(brier_improvements):+.4f}")
        
        print(f"\n[Confidence Scores]")
        conf_before = np.mean([r["confidence_before"] for r in results.values()])
        conf_after = np.mean([r["confidence_after"] for r in results.values()])
        print(f"  Average BEFORE: {conf_before:.2%}")
        print(f"  Average AFTER:  {conf_after:.2%}")
        print(f"  Change:         {conf_after - conf_before:+.2%}")
    
    # Decision
    print("\n" + "="*80)
    print("DECISION")
    print("="*80)
    
    if np.mean(ece_improvements) > 0.001:
        print(f"\n✅ CALIBRATION IMPROVES HONESTY")
        print(f"   Average ECE improvement: {np.mean(ece_improvements):+.4f}")
        print("\n   Option A: Apply calibration to all tickers (update BD)")
        print("   Option B: Keep current (already well-calibrated)")
        print("\n   Recommendation: Apply if ECE improvement > 0.005 per ticker")
        
        # Count tickers with significant improvement
        sig_improved = sum(1 for r in results.values() if r["ece_before"] - r["ece_after"] > 0.005)
        print(f"   Tickers with sig. improvement (>0.005): {sig_improved}/{len(results)}")
        
    elif np.mean(ece_improvements) > -0.001:
        print(f"\n➡️  CALIBRATION NEUTRAL")
        print(f"    Average ECE change: {np.mean(ece_improvements):+.4f}")
        print("\n    Current model is already well-calibrated!")
        print("    Recommendation: Keep as-is")
        
    else:
        print(f"\n⚠️  CALIBRATION MAKES WORSE")
        print(f"    Average ECE change: {np.mean(ece_improvements):+.4f}")
        print("\n    Recommendation: Skip calibration, keep current")
    
    print("\n" + "="*80)
    print("\nCalibration Parameters (if applying):")
    print("-" * 80)
    print(f"\n{'Ticker':<10} {'a (slope)':<12} {'b (intercept)':<12} {'Notes'}")
    print("-" * 50)
    
    for ticker in sorted(results.keys()):
        result = results[ticker]
        a = result["a"]
        b = result["b"]
        # a≈1, b≈0 means no calibration needed
        # a<1 means overcondident, a>1 means underconfident
        
        if abs(a - 1.0) < 0.1 and abs(b) < 0.1:
            note = "✓ Well-calibrated"
        elif a < 1:
            note = "⚠ Overconfident"
        else:
            note = "⚠ Underconfident"
        
        print(f"{ticker:<10} {a:+.4f}     {b:+.4f}       {note}")
    
    print("\n" + "="*80 + "\n")
    
    return results


if __name__ == "__main__":
    results = main()
