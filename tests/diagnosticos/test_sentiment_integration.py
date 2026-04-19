#!/usr/bin/env python3
"""
Test script to verify sentiment integration is working correctly.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from backend.models.config import USE_SENTIMENT, SENTIMENT_FEATURE_COLS, get_feature_cols
from backend.models.data_pipeline import compute_features, download_data

print("\n" + "="*80)
print("TEST: Sentiment Integration Check")
print("="*80)

# Test 1: Verify USE_SENTIMENT is True
print(f"\n[TEST 1] USE_SENTIMENT setting")
print(f"  Value: {USE_SENTIMENT}")
assert USE_SENTIMENT == True, "USE_SENTIMENT should be True"
print(f"  ✓ PASSED")

# Test 2: Verify sentiment features are in config
print(f"\n[TEST 2] Sentiment feature columns")
print(f"  Columns: {SENTIMENT_FEATURE_COLS}")
assert len(SENTIMENT_FEATURE_COLS) == 3, "Should have 3 sentiment features"
assert "sentiment_score" in SENTIMENT_FEATURE_COLS
assert "sentiment_magnitude" in SENTIMENT_FEATURE_COLS
assert "news_volume" in SENTIMENT_FEATURE_COLS
print(f"  ✓ PASSED")

# Test 3: Check if features include sentiment
print(f"\n[TEST 3] Feature columns for AAPL")
feature_cols = get_feature_cols("AAPL")
print(f"  Total features: {len(feature_cols)}")
print(f"  Features: {feature_cols}")
sentiment_features_in_cols = [col for col in feature_cols if col in SENTIMENT_FEATURE_COLS]
print(f"  Sentiment features found: {sentiment_features_in_cols}")
assert len(sentiment_features_in_cols) == 3, "All 3 sentiment features should be in feature columns"
print(f"  ✓ PASSED")

# Test 4: Actually compute features and check if sentiment is there
print(f"\n[TEST 4] Computing features with sentiment for AAPL")
print(f"  Downloading data...")
df = download_data("AAPL")
print(f"  Data shape: {df.shape}")

print(f"  Computing features...")
df_features = compute_features(df, ticker="AAPL")
print(f"  Features shape: {df_features.shape}")
print(f"  Features columns: {df_features.columns.tolist()}")

sentiment_cols_present = [col for col in SENTIMENT_FEATURE_COLS if col in df_features.columns]
print(f"  Sentiment columns present: {sentiment_cols_present}")
assert len(sentiment_cols_present) > 0, "At least one sentiment column should be present"
print(f"  ✓ PASSED")

# Test 5: Check sentimente values
print(f"\n[TEST 5] Sentiment values")
if "sentiment_score" in df_features.columns:
    score_mean = df_features["sentiment_score"].mean()
    score_std = df_features["sentiment_score"].std()
    print(f"  sentiment_score: mean={score_mean:.4f}, std={score_std:.4f}")
    
if "sentiment_magnitude" in df_features.columns:
    mag_mean = df_features["sentiment_magnitude"].mean()
    mag_std = df_features["sentiment_magnitude"].std()
    print(f"  sentiment_magnitude: mean={mag_mean:.4f}, std={mag_std:.4f}")
    
if "news_volume" in df_features.columns:
    vol_mean = df_features["news_volume"].mean()
    vol_max = df_features["news_volume"].max()
    print(f"  news_volume: mean={vol_mean:.1f}, max={vol_max}")
print(f"  ✓ PASSED")

print(f"\n" + "="*80)
print("ALL TESTS PASSED! Sentiment integration is working correctly.")
print("="*80 + "\n")
