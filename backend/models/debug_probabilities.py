"""
Debug script to check prediction probabilities distribution
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pickle
import numpy as np
from backend.models.config import SAVED_MODELS_DIR, get_config, get_asset_type, get_feature_cols, ENSEMBLE_VARIATIONS
from backend.models.data_pipeline import prepare_data_multi_window

def check_probs(ticker='KO'):
    """Check probability distribution for ALCISTA after training."""
    
    print(f"\n{'='*80}")
    print(f"DEBUG: Probability distribution for {ticker}")
    print(f"{'='*80}")
    
    # 1. Load model
    model_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost.pkl")
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    print(f"✅ Model loaded from {model_path}")
    
    # 2. Prepare data
    config = get_config(ticker)
    asset_type = get_asset_type(ticker)
    variations = ENSEMBLE_VARIATIONS.get(asset_type, [{"window_size": 30}])
    window_sizes = [v.get("window_size", 30) for v in variations]
    all_data = prepare_data_multi_window(ticker, config, window_sizes)
    max_ws = max(window_sizes)
    data_dict = all_data.get(max_ws)
    
    # 3. Build features
    def build_xgb_features(X_tensor):
        X = X_tensor.numpy()
        last  = X[:, -1, :]
        mean  = X.mean(axis=1)
        std   = X.std(axis=1)
        trend = X[:, -1, :] - X[:, 0, :]
        return np.concatenate([last, mean, std, trend], axis=1)
    
    X_test = build_xgb_features(data_dict["X_test"])
    
    # 4. Get probabilities
    y_prob = model.predict_proba(X_test)[:, 1]
    y_test = data_dict["y_test"].numpy().ravel()
    
    print(f"\n📊 Probabilities for ALCISTA class (0=positiveLOW, 1=HIGH):")
    print(f"   Min:  {y_prob.min():.4f}")
    print(f"   Max:  {y_prob.max():.4f}")
    print(f"   Mean: {y_prob.mean():.4f}")
    print(f"   Std:  {y_prob.std():.4f}")
    print(f"   Median: {np.median(y_prob):.4f}")
    
    print(f"\n📊 Percentiles:")
    for p in [10, 25, 50, 75, 90, 95, 99]:
        print(f"   {p}%:  {np.percentile(y_prob, p):.4f}")
    
    print(f"\n📊 Count by range:")
    for min_p, max_p in [(0, 0.2), (0.2, 0.35), (0.35, 0.5), (0.5, 0.65), (0.65, 0.8), (0.8, 1.0)]:
        count = np.sum((y_prob >= min_p) & (y_prob < max_p))
        pct = count / len(y_prob) * 100
        print(f"   {min_p:.2f}-{max_p:.2f}: {count:4d} ({pct:5.1f}%)")
    
    print(f"\n📊 Predictions with prob >= 0.65: {np.sum(y_prob >= 0.65)}")
    print(f"   Predictions with prob >= 0.55: {np.sum(y_prob >= 0.55)}")
    print(f"   Predictions with prob >= 0.50: {np.sum(y_prob >= 0.50)}")
    print(f"   Predictions with prob >= 0.45: {np.sum(y_prob >= 0.45)}")
    
    # Check test set ground truth
    print(f"\n📊 Test set ground truth:")
    print(f"   ALCISTA samples in test (class 2): {np.sum(y_test == 2)}")
    print(f"   LATERAL samples in test (class 1): {np.sum(y_test == 1)}")
    print(f"   BAJISTA samples in test (class 0): {np.sum(y_test == 0)}")
    
    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    check_probs('KO')
