"""
TEST: Verify ImprovedSentimentAnalyzer lag features work with synthetic data
Purpose: Validate the sentiment lag feature creation logic before full training
"""
import sys
sys.path.insert(0, 'd:/Uni/TFG/Horizon')

import pandas as pd
import numpy as np
from backend.models.sentiment_improved import ImprovedSentimentAnalyzer

print("=" * 70)
print("TEST: ImprovedSentimentAnalyzer Lag Features (Synthetic Data)")
print("=" * 70)

# Create synthetic data
print("\n[1/3] Creating synthetic test data...")
dates = pd.date_range(start='2023-01-01', periods=365, freq='D')
np.random.seed(42)

# Simulate sentiment score (between -1 and 1)
sentiment_score = np.random.uniform(-0.5, 0.8, 365)
volatility_std = np.random.uniform(0.01, 0.05, 365)

df_test = pd.DataFrame({
    'Date': dates,
    'sentiment_score': sentiment_score,
    'volatility_std': volatility_std,
})
df_test.set_index('Date', inplace=True)

print(f"✓ Synthetic data created: {len(df_test)} rows")
print(f"  Columns: {list(df_test.columns)}")

# Test 2: Apply ImprovedSentimentAnalyzer
print("\n[2/3] Applying ImprovedSentimentAnalyzer...")
try:
    analyzer = ImprovedSentimentAnalyzer(window_size=30)
    df_with_features = analyzer.create_sentiment_features_with_lag(
        df_test.copy(),
        'sentiment_score',
        'volatility_std'
    )
    print(f"✓ Features created successfully")
except Exception as e:
    print(f"✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Verify features
print("\n[3/3] Verifying feature creation...")
expected_features = analyzer.get_feature_names()
print(f"\nExpected {len(expected_features)} features:")

found = 0
for i, feat in enumerate(expected_features, 1):
    if feat in df_with_features.columns:
        non_null = df_with_features[feat].notna().sum()
        col_values = df_with_features[feat].dropna()
        has_variance = col_values.std() > 0
        status = "✓" if non_null > 0 else "✗"
        print(f"  [{i:2d}] {status} {feat:40s} | {non_null:5d} non-null | var={has_variance}")
        found += 1
    else:
        print(f"  [{i:2d}] ✗ {feat:40s} | MISSING!")

# Summary
print("\n" + "=" * 70)
success = found == len(expected_features)
print("TEST RESULT: " + ("✓ PASS" if success else f"✗ FAIL (found {found}/{len(expected_features)})"))
print("=" * 70)

if success:
    print("\n✓ ImprovedSentimentAnalyzer is working correctly!")
    print("✓ Ready to proceed with full training using real data")
sys.exit(0 if success else 1)
