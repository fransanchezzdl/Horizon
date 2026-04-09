"""
TEST: Verify ImprovedSentimentAnalyzer lag features are created correctly
Purpose: Quick validation before full training with all 12 tickers
"""
import sys
sys.path.insert(0, 'd:/Uni/TFG/Horizon')

from backend.models.data_pipeline import download_data, compute_features
from backend.models.sentiment_improved import ImprovedSentimentAnalyzer
from backend.models.config import get_asset_type

print("=" * 70)
print("TEST: ImprovedSentimentAnalyzer Lag Features Creation")
print("=" * 70)

# Test 1: Load data for AAPL with new sentiment features
print("\n[1/3] Loading AAPL data with sentiment lag features...")
ticker = "AAPL"
try:
    raw_df = download_data(ticker)
    include_market_context = get_asset_type(ticker) == "volatile"
    df = compute_features(raw_df, include_market_context=include_market_context, ticker=ticker)
    print(f"✓ Data loaded: {len(df)} rows, {len(df.columns)} columns")
except Exception as e:
    print(f"✗ ERROR loading data: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Verify sentiment lag features exist
print("\n[2/3] Verifying sentiment lag features...")
analyzer = ImprovedSentimentAnalyzer(window_size=30)
expected_features = analyzer.get_feature_names()
print(f"Expected features ({len(expected_features)}):")

found_count = 0
for i, feat in enumerate(expected_features, 1):
    if feat in df.columns:
        non_null = df[feat].notna().sum()
        non_zero = (df[feat] != 0).sum()
        print(f"  [{i:2d}] ✓ {feat:40s} | {non_null:5d} non-null | {non_zero:5d} non-zero")
        found_count += 1
    else:
        print(f"  [{i:2d}] ✗ {feat:40s} | MISSING!")

# Test 3: Quick statistics
print("\n[3/3] Feature statistics:")
has_all = found_count == len(expected_features)
if has_all:
    sentiment_cols = [c for c in df.columns if 'sentiment' in c]
    print(f"✓ All {len(expected_features)} lag features found!")
    print(f"✓ Total sentiment-related columns: {len(sentiment_cols)}")
    print(f"  Columns: {', '.join(sentiment_cols[:5])}...")
    
    # Check variance
    print(f"\n  Lag feature variance (should NOT be all zeros):")
    for feat in expected_features[:5]:
        if feat in df.columns:
            var = df[feat].var()
            print(f"    {feat:40s}: var={var:.6f}")
else:
    print(f"✗ MISSING {len(expected_features) - found_count} features!")
    missing = [f for f in expected_features if f not in df.columns]
    print(f"  Missing: {missing}")

print("\n" + "=" * 70)
print("TEST COMPLETE" + (" ✓ PASS - Ready for training" if has_all else " ✗ FAIL - Check data pipeline"))
print("=" * 70)
