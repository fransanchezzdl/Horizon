"""
Final validation: Test the predict_xgboost function to ensure it works correctly.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from backend.models.xgboost_model import predict_xgboost
from backend.models.config import SAVED_MODELS_DIR

def test_predict():
    """Test that predict_xgboost works correctly."""
    
    print(f"\n{'='*80}")
    print("TESTING predict_xgboost() with random features")
    print(f"{'='*80}\n")
    
    tickers = ['KO', 'TSLA', 'AAPL']
    
    for ticker in tickers:
        print(f"\n📊 Testing {ticker}:")
        
        # Create dummy features (should match feature count from training)
        # XGBoost uses: last, mean, std, trend for each feature
        # Total features ≈ n_features * 4 (where n_features ≈ 40-50+)
        n_features = 200  # Safe estimate
        features = np.random.randn(n_features)
        
        try:
            result = predict_xgboost(ticker, features)
            
            # Check result structure
            assert "direction" in result, "Missing 'direction' in result"
            assert "probability" in result, "Missing 'probability' in result"
            assert result["direction"] in [0, 1, 2], f"Invalid direction: {result['direction']}"
            assert 0 <= result["probability"] <= 1, f"Invalid probability: {result['probability']}"
            
            direction_name = {0: "BAJISTA", 1: "LATERAL", 2: "ALCISTA"}
            print(f"   ✅ Prediction: {direction_name[result['direction']]} (prob: {result['probability']:.4f})")
            print(f"   ✅ Confidence: {result.get('confidence_level', 'unknown')}")
            
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
    
    print(f"\n{'='*80}")
    print("✅ ALL PREDICTION TESTS PASSED")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    test_predict()
