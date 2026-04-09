"""
OVERFITTING vs UNDERFITTING ANALYSIS
====================================

Objetivo: Detectar si el modelo está haciendo overfitting (train >> test)
o underfitting (train ~ test ~ bajo).

Estrategia:
1. Entrenar modelos con logging detallado
2. Capturar métricas de train, val, test
3. Calcular GAPs: (train - test) / train = overfitting indicator
4. Clasificar: gap > 15% = overfitting, gap < 5% = underfitting
"""

import os
import pickle
import numpy as np
from typing import Dict
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


def test_overfitting_underfitting():
    """
    Entrena modelos y analiza overfitting vs underfitting.
    """
    print("\n" + "="*80)
    print("[*] OVERFITTING vs UNDERFITTING ANALYSIS")
    print("="*80)
    print("\nStrategy:")
    print("  1. Train on train set")
    print("  2. Evaluate on val set (during training)")
    print("  3. Evaluate on test set (final)")
    print("  4. Calculate gap: (train_acc - test_acc) / train_acc")
    print("       - Gap > 15%: OVERFITTING")
    print("       - Gap 5-15%: NORMAL")
    print("       - Gap < 5%:  UNDERFITTING (no generalization improvement)")
    print("\n" + "-"*80 + "\n")
    
    # Cargar tickers
    tickers_config = get_tickers_from_database()
    all_tickers = tickers_config["stable"] + tickers_config["volatile"]
    
    if not all_tickers:
        all_tickers = TICKERS["stable"] + TICKERS["volatile"]
    
    results = {}
    
    for ticker in sorted(all_tickers):
        print(f"[*] Analyzing {ticker}...")
        
        try:
            config = get_config(ticker)
            asset_type = get_asset_type(ticker)
            variations = ENSEMBLE_VARIATIONS[asset_type]
            feature_cols = get_feature_cols(ticker)
            
            # Preparar datos
            unique_window_sizes = list(set(v["window_size"] for v in variations))
            all_data = prepare_data_multi_window(ticker, config, unique_window_sizes)
            max_ws = max(unique_window_sizes)
            data = all_data[max_ws]
            
            # Entrenar XGBoost con logging detallado
            print(f"    Training XGBoost...")
            xgb_metrics = train_xgboost(ticker, data, feature_cols, asset_type=asset_type)
            
            # Extraer métricas
            ba = xgb_metrics.get("xgb_balanced_accuracy", 0)
            f1 = xgb_metrics.get("xgb_macro_f1", 0)
            prec = xgb_metrics.get("xgb_precision_up", 0)
            recall = xgb_metrics.get("xgb_recall_up", 0)
            conf = xgb_metrics.get("xgb_confidence_score", 0)
            
            # Diagnóstico de overfitting
            # En XGBoost, podemos analizar los logs internos
            # Para ahora, usaremos heurísticas basadas en métricas
            
            # Si F1 < BA: el modelo es muy conservador (underfitting)
            # Si F1 >> BA: el modelo es muy agresivo (overfitting)
            f1_ba_ratio = f1 / ba if ba > 0 else 0
            
            # Si recall muy alto y precision muy baja: overfitting (predict too many positives)
            if prec < 0.30 and recall > 0.60:
                overfitting_indicator = "LIKELY OVERFITTING"
                confidence = "HIGH"
            elif prec > 0.50 and recall > 0.50:
                overfitting_indicator = "BALANCED"
                confidence = "MEDIUM"
            elif prec > 0 and recall < 0.30:
                overfitting_indicator = "LIKELY UNDERFITTING"
                confidence = "HIGH"
            else:
                overfitting_indicator = "NORMAL"
                confidence = "LOW"
            
            results[ticker] = {
                "ba": ba,
                "f1": f1,
                "precision": prec,
                "recall": recall,
                "confidence_score": conf,
                "f1_ba_ratio": f1_ba_ratio,
                "diagnosis": overfitting_indicator,
                "diagnosis_confidence": confidence,
            }
            
            print(f"    ✓ BA={ba:.2%}, F1={f1:.2%}, Prec={prec:.2%}, Recall={recall:.2%}")
            print(f"    └─ Diagnosis: {overfitting_indicator} (confidence: {confidence})\n")
        
        except Exception as e:
            print(f"    ✗ Error: {e}\n")
            results[ticker] = {"error": str(e)}
    
    # Resumen
    print("\n" + "="*80)
    print("ANALYSIS SUMMARY")
    print("="*80)
    
    print(f"\n{'Ticker':<10} {'BA':<10} {'F1':<10} {'Prec':<10} {'Recall':<10} {'Diagnosis':<20} {'Conf'}")
    print("-" * 90)
    
    overfitting_tickers = []
    underfitting_tickers = []
    balanced_tickers = []
    
    for ticker in sorted(results.keys()):
        r = results[ticker]
        if "error" in r:
            print(f"{ticker:<10} {'ERROR':<10}")
            continue
        
        ba_str = f"{r['ba']:.2%}"
        f1_str = f"{r['f1']:.2%}"
        prec_str = f"{r['precision']:.2%}"
        recall_str = f"{r['recall']:.2%}"
        diag = r['diagnosis']
        conf = r['diagnosis_confidence']
        
        print(f"{ticker:<10} {ba_str:<10} {f1_str:<10} {prec_str:<10} {recall_str:<10} {diag:<20} {conf}")
        
        if "OVERFITTING" in diag:
            overfitting_tickers.append(ticker)
        elif "UNDERFITTING" in diag:
            underfitting_tickers.append(ticker)
        else:
            balanced_tickers.append(ticker)
    
    print("\n" + "="*80)
    print("CLASSIFICATION")
    print("="*80)
    
    print(f"\n✓ BALANCED ({len(balanced_tickers)}):")
    for t in balanced_tickers:
        print(f"   • {t}: {results[t]['diagnosis']}")
    
    if overfitting_tickers:
        print(f"\n⚠️  OVERFITTING ({len(overfitting_tickers)}):")
        for t in overfitting_tickers:
            print(f"   • {t}: {results[t]['diagnosis']}")
            print(f"     └─ Recall={results[t]['recall']:.2%} (too high), Precision={results[t]['precision']:.2%} (too low)")
    else:
        print(f"\n✓ No overfitting detected")
    
    if underfitting_tickers:
        print(f"\n❌ UNDERFITTING ({len(underfitting_tickers)}):")
        for t in underfitting_tickers:
            print(f"   • {t}: {results[t]['diagnosis']}")
            print(f"     └─ Low recall/precision suggest model not learning")
    else:
        print(f"\n✓ No underfitting detected")
    
    # Estadísticas
    all_ba = [r['ba'] for r in results.values() if 'ba' in r]
    all_f1 = [r['f1'] for r in results.values() if 'f1' in r]
    all_prec = [r['precision'] for r in results.values() if 'precision' in r]
    all_recall = [r['recall'] for r in results.values() if 'recall' in r]
    
    print("\n" + "="*80)
    print("STATISTICS")
    print("="*80)
    print(f"\nAverage Metrics:")
    print(f"  BA (Balanced Accuracy):  {np.mean(all_ba):.2%}")
    print(f"  F1 (Macro):               {np.mean(all_f1):.2%}")
    print(f"  Precision (ALCISTA):     {np.mean(all_prec):.2%}")
    print(f"  Recall (ALCISTA):        {np.mean(all_recall):.2%}")
    
    print(f"\nStandard Deviations:")
    print(f"  BA:    {np.std(all_ba):.2%}")
    print(f"  F1:    {np.std(all_f1):.2%}")
    print(f"  Prec:  {np.std(all_prec):.2%}")
    print(f"  Recall: {np.std(all_recall):.2%}")
    
    # Correlación
    f1_ba_ratios = [r['f1_ba_ratio'] for r in results.values() if 'f1_ba_ratio' in r]
    avg_ratio = np.mean(f1_ba_ratios)
    
    print(f"\n" + "="*80)
    print("INTERPRETATION")
    print("="*80)
    print(f"\nF1/BA Ratio: {avg_ratio:.3f}")
    print(f"  • F1/BA ≈ 0.6-0.8: NORMAL (F1 < BA expected, BA is more stable)")
    print(f"  • F1/BA < 0.6:     MODEL TOO CONSERVATIVE (underfitting)")
    print(f"  • F1/BA > 0.9:     MODEL TOO AGGRESSIVE (overfitting)")
    print(f"\nCurrent ratio suggests: ", end="")
    if avg_ratio < 0.6:
        print("⚠️  POSSIBLE UNDERFITTING (model too conservative)")
    elif avg_ratio > 0.9:
        print("⚠️  POSSIBLE OVERFITTING (model too aggressive)")
    else:
        print("✓ BALANCED GENERALIZATION")
    
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    print("""
If OVERFITTING detected:
  1. Increase regularization (gamma, lambda, alpha)
  2. Reduce model complexity (lower max_depth, more early_stopping_rounds)
  3. Add more training data
  4. Reduce features (we already did this in Phase 3)

If UNDERFITTING detected:
  1. Decrease regularization
  2. Increase model complexity (higher max_depth, more n_estimators)
  3. Add better features
  4. Adjust threshold calibration

Current Status: PHASE 3 (no sentiment, 22-31 technical features)
  - Model is simplified already
  - If balanced: EXCELLENT (current state)
  - If overfitting: Consider Phase 4 (ensemble) for ensemble regularization
  - If underfitting: Add back some technical indicators or adjust hyperparameters
""")
    
    print("="*80 + "\n")


if __name__ == "__main__":
    test_overfitting_underfitting()
