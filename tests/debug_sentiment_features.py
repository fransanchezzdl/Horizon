"""
DEBUG: Verify if sentiment lag features are actually being used in training pipeline
"""
import sys
sys.path.insert(0, 'd:/Uni/TFG/Horizon')

from backend.models.config import get_feature_cols, SENTIMENT_FEATURE_COLS

print("=" * 80)
print("DEBUG: Feature Verification")
print("=" * 80)
print()

# Check 1: SENTIMENT_FEATURE_COLS registry
print("[1] SENTIMENT_FEATURE_COLS en config.py:")
print(f"    Total: {len(SENTIMENT_FEATURE_COLS)} features")
for feat in SENTIMENT_FEATURE_COLS:
    print(f"      • {feat}")

# Check 2: Features for each ticker
print(f"\n[2] Features per ticker:")
tickers = ['AAPL', 'NVDA', 'VXX']
for ticker in tickers:
    try:
        features = get_feature_cols(ticker)
        print(f"\n    {ticker}:")
        print(f"      Total: {len(features)} features")
        
        # Count sentiment features
        sentiment_in_cols = [f for f in features if 'sentiment' in f.lower()]
        print(f"      Sentiment-related: {len(sentiment_in_cols)} features")
        
        if sentiment_in_cols:
            print(f"      Detalles:")
            for feat in sentiment_in_cols:
                print(f"        • {feat}")
        else:
            print(f"      ⚠️  NO SENTIMENT FEATURES FOUND!")
            
    except Exception as e:
        print(f"      Error getting features: {e}")

# Check 3: Is data_pipeline importing sentiment_improved?
print(f"\n[3] Checking data_pipeline.py sentiment integration:")
try:
    from backend.models import data_pipeline
    
    # Check if sentiment_improved is imported
    import inspect
    source = inspect.getsource(data_pipeline.compute_features)
    
    if 'sentiment_improved' in source or 'ImprovedSentimentAnalyzer' in source:
        print("    ✓ sentiment_improved.py is referenced in compute_features")
    else:
        print("    ✗ sentiment_improved.py is NOT referenced - features won't be created!")
        
except Exception as e:
    print(f"    Error: {e}")

print("\n" + "=" * 80)
