"""
Script para analizar las features calculadas y detectar problemas.
"""

import pandas as pd
import numpy as np
from backend.models.data_pipeline import download_data, compute_features
from backend.models.config import get_asset_type

def analyze_features(ticker: str):
    """Analiza las features calculadas para un ticker."""
    
    print("=" * 60)
    print(f"ANÁLISIS DE FEATURES PARA {ticker}")
    print("=" * 60)
    
    # Descargar y calcular features
    raw_df = download_data(ticker)
    include_market_context = get_asset_type(ticker) == "volatile"
    feat_df = compute_features(raw_df, include_market_context=include_market_context, ticker=ticker)
    
    print(f"\n📊 Total de features: {len(feat_df.columns)}")
    print(f"📊 Total de filas: {len(feat_df)}")
    
    # Estadísticas por feature
    print(f"\n{'Feature':<20} {'Min':<12} {'Max':<12} {'Mean':<12} {'Std':<12} {'NaN%':<8}")
    print("-" * 80)
    
    for col in feat_df.columns:
        nan_pct = feat_df[col].isna().sum() / len(feat_df) * 100
        if nan_pct == 0:
            stats = feat_df[col].describe()
            print(f"{col:<20} {stats['min']:<12.4f} {stats['max']:<12.4f} {stats['mean']:<12.4f} {stats['std']:<12.4f} {nan_pct:<8.2f}")
        else:
            print(f"{col:<20} {'N/A':<12} {'N/A':<12} {'N/A':<12} {'N/A':<12} {nan_pct:<8.2f}")
    
    # Detectar features con valores extremos o constantes
    print(f"\n⚠️  FEATURES CON POSIBLES PROBLEMAS:")
    problems_found = False
    
    for col in feat_df.columns:
        # Feature constante
        if feat_df[col].std() < 1e-6:
            print(f"  • {col}: Casi constante (std={feat_df[col].std():.2e})")
            problems_found = True
        
        # Feature con valores extremos
        q99 = feat_df[col].quantile(0.99)
        q01 = feat_df[col].quantile(0.01)
        if abs(q99) > 1e6 or abs(q01) > 1e6:
            print(f"  • {col}: Valores extremos (Q01={q01:.2e}, Q99={q99:.2e})")
            problems_found = True
        
        # Feature con muchos NaN
        nan_pct = feat_df[col].isna().sum() / len(feat_df) * 100
        if nan_pct > 5:
            print(f"  • {col}: Muchos NaN ({nan_pct:.1f}%)")
            problems_found = True
    
    if not problems_found:
        print("  ✅ No se detectaron problemas obvios")
    
    # Correlación con el target
    from backend.models.data_pipeline import compute_target
    target = compute_target(feat_df)
    feat_df_with_target = feat_df.copy()
    feat_df_with_target["_target"] = target
    feat_df_with_target.dropna(inplace=True)
    
    correlations = feat_df_with_target.corr()["_target"].drop("_target").abs().sort_values(ascending=False)
    
    print(f"\n📈 TOP 10 FEATURES MÁS CORRELACIONADAS CON TARGET:")
    for i, (feat, corr) in enumerate(correlations.head(10).items(), 1):
        print(f"  {i:2d}. {feat:<20} {corr:.4f}")
    
    print(f"\n📉 BOTTOM 5 FEATURES MENOS CORRELACIONADAS:")
    for i, (feat, corr) in enumerate(correlations.tail(5).items(), 1):
        print(f"  {i:2d}. {feat:<20} {corr:.4f}")

if __name__ == "__main__":
    analyze_features("KO")
