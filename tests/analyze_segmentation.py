"""
Análisis de Segmentación STABLE vs VOLATILE
============================================

Objetivo: Identificar oportunidades de optimización específicas por tipo de activo.

Basado en Phase 3 (22-31 features técnicas, sin sentimiento).
"""

import numpy as np
from backend.models.config import get_tickers_from_database, TICKERS
from backend.daos.activo_dao import ActivoDAO

def analyze_segmentation():
    """
    Analiza métricas Phase 3 segregadas por tipo de activo (STABLE vs VOLATILE).
    """
    
    print("\n" + "="*80)
    print("PHASE 3 ANALYSIS: STABLE vs VOLATILE SEGMENTATION")
    print("="*80)
    
    # Cargar configuración de tickers
    tickers_config = get_tickers_from_database()
    stable_tickers = tickers_config.get("stable", [])
    volatile_tickers = tickers_config.get("volatile", [])
    
    print(f"\n[SEGMENTATION]")
    print(f"  STABLE ({len(stable_tickers)}): {stable_tickers}")
    print(f"  VOLATILE ({len(volatile_tickers)}): {volatile_tickers}")
    
    # Cargar métricas Phase 3 desde BD
    activos = ActivoDAO.obtener_todos()
    
    stable_metrics = []
    volatile_metrics = []
    
    print("\n" + "-"*80)
    print("PHASE 3 RESULTS BY SEGMENTATION")
    print("-"*80)
    print(f"\n{'Ticker':<10} {'Type':<12} {'Confidence':<12} {'Status'}")
    print("-" * 50)
    
    for activo in activos:
        if hasattr(activo, 'ticker') and hasattr(activo, 'confianza_bygru'):
            ticker = activo.ticker
            confidence = float(activo.confianza_bygru) if activo.confianza_bygru else 0
            
            if ticker in stable_tickers:
                asset_type = "STABLE"
                stable_metrics.append({
                    'ticker': ticker,
                    'confidence': confidence,
                    'estabilidad': True
                })
            elif ticker in volatile_tickers:
                asset_type = "VOLATILE"
                volatile_metrics.append({
                    'ticker': ticker,
                    'confidence': confidence,
                    'estabilidad': False
                })
            else:
                continue
            
            status = "✓" if confidence > 0.6 else "⚠" if confidence > 0.5 else "❌"
            print(f"{ticker:<10} {asset_type:<12} {confidence:.2%}{'':8} {status}")
    
    # Análisis estadístico
    print("\n" + "="*80)
    print("STATISTICAL ANALYSIS")
    print("="*80)
    
    if stable_metrics:
        stable_confidences = [m['confidence'] for m in stable_metrics]
        stable_avg = np.mean(stable_confidences)
        stable_std = np.std(stable_confidences)
        stable_min = np.min(stable_confidences)
        stable_max = np.max(stable_confidences)
        
        print(f"\n[STABLE] ({len(stable_metrics)} tickers)")
        print(f"  Average Confidence: {stable_avg:.2%}")
        print(f"  Std Deviation:      {stable_std:.2%}")
        print(f"  Range:              {stable_min:.2%} - {stable_max:.2%}")
        print(f"  Above 60%:          {sum(1 for c in stable_confidences if c > 0.6)}/{len(stable_confidences)}")
    
    if volatile_metrics:
        volatile_confidences = [m['confidence'] for m in volatile_metrics]
        volatile_avg = np.mean(volatile_confidences)
        volatile_std = np.std(volatile_confidences)
        volatile_min = np.min(volatile_confidences)
        volatile_max = np.max(volatile_confidences)
        
        print(f"\n[VOLATILE] ({len(volatile_metrics)} tickers)")
        print(f"  Average Confidence: {volatile_avg:.2%}")
        print(f"  Std Deviation:      {volatile_std:.2%}")
        print(f"  Range:              {volatile_min:.2%} - {volatile_max:.2%}")
        print(f"  Above 60%:          {sum(1 for c in volatile_confidences if c > 0.6)}/{len(volatile_confidences)}")
    
    # Comparación
    print("\n" + "-"*80)
    print("COMPARISON")
    print("-"*80)
    
    if stable_metrics and volatile_metrics:
        diff = stable_avg - volatile_avg
        print(f"\nStable vs Volatile:")
        print(f"  Difference in Avg Confidence: {diff:+.2%}")
        print(f"  {'→ STABLE performs BETTER' if diff > 0 else '→ VOLATILE performs BETTER'}")
        print(f"  Insight: {abs(diff):.2%} {'advantage for STABLE' if diff > 0 else 'advantage for VOLATILE'}")
    
    # Recomendaciones
    print("\n" + "="*80)
    print("OPTIMIZATION OPPORTUNITIES")
    print("="*80)
    
    if stable_metrics:
        stable_below_60 = [m for m in stable_metrics if m['confidence'] < 0.60]
        if stable_below_60:
            print(f"\n[STABLE] Below 60% confidence:")
            for m in stable_below_60:
                print(f"  • {m['ticker']} ({m['confidence']:.2%}) ← Could benefit from tuning")
    
    if volatile_metrics:
        volatile_below_60 = [m for m in volatile_metrics if m['confidence'] < 0.60]
        if volatile_below_60:
            print(f"\n[VOLATILE] Below 60% confidence:")
            for m in volatile_below_60:
                print(f"  • {m['ticker']} ({m['confidence']:.2%}) ← Could benefit from tuning")
    
    print("\n" + "-"*80)
    print("POSSIBLE IMPROVEMENTS")
    print("-"*80)
    
    print("""
1. FEATURE ENGINEERING BY STABILITY:
   • STABLE: Current 22-31 features are adequate (low churn, predictable patterns)
   • VOLATILE: Consider additional volatility-specific indicators:
     - Realized volatility over different windows (5d, 10d, 20d)
     - Volatility cluster detection
     - Regime shift indicators (Bull/Bear market detection)
     - Jump risk measures
   
2. HYPERPARAMETER TUNING BY STABILITY:
   • STABLE: Already optimized but could explore:
     - Slight reduction in early_stopping_rounds (faster convergence)
     - Adjust max_depth (5 is good, test 4-6)
   • VOLATILE: Current config (750 estimators, 4 depth) working but:
     - Test increasing early_stopping_rounds (40→45) for patience
     - Test subsample variation (0.85→0.87) for better OOB estimate
   
3. THRESHOLD CALIBRATION:
   • Current v4 Recall-Target uses global thresholds
   • Could use per-type thresholds:
     - STABLE: Target recall 48% (more conservative)
     - VOLATILE: Target recall 52% (willing to take more risk)
   
4. CLASS WEIGHT ADJUSTMENT:
   • Current: scale_pos_weight adaptive per distribution
   • Could differentiate:
     - STABLE: scale_pos_weight = 1.8 (less adjustment needed)
     - VOLATILE: scale_pos_weight = 2.2 (more adjustment needed)
   
5. ENSEMBLE WEIGHTING:
   • BiGRU + XGBoost weights (currently: 0.6/0.4)
   • Could use per-type weights:
     - STABLE: 0.5/0.5 (equal weight, both models perform well)
     - VOLATILE: 0.7/0.3 (favor BiGRU, more robust with uncertainty)
    """)
    
    print("\n" + "="*80)
    print("RECOMMENDATION")
    print("="*80)
    
    print("""
✅ NEXT STEPS (Priority Order):

1. [QUICK WIN] Volatility Indicators (30 min)
   - Add 3-4 volatility measures specific to VOLATILE tickers
   - Re-train only VOLATILE models
   - Expected gain: +0.5-1% for VOLATILE

2. [MEDIUM] Per-Type Threshold Calibration (20 min)
   - Implement separate recall targets for STABLE vs VOLATILE
   - Rebalance risk appetite
   - Expected gain: +0.3-0.8% overall

3. [OPTIONAL] XGBoost Config Fine-tuning (40 min)
   - Test hyperparameter variations per type
   - Grid search: subsample (0.83-0.87), early_stopping (35-45)
   - Expected gain: +0.2-0.5% for VOLATILE

4. [FUTURE] Ensemble Weighting Optimization (60 min)
   - Grid search BigRU/XGBoost weights per type
   - Validate on test set
   - Expected cumulative gain: +1-2% overall
    """)
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    analyze_segmentation()
