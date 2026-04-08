"""
PHASE 3: FEATURE IMPORTANCE FILTERING

Objetivo: Remover features menos importantes para reducir ruido y mejorar generalización.

Estrategia:
1. Cargar modelos XGBoost entrenados
2. Extraer feature importance de cada modelo
3. Identificar bottom 20% features (menos importantes)
4. Crear nueva configuración sin esos features
5. Reentrenar todos los modelos
6. Comparar resultados (esperado: +0.5-1% mejora en BA)

Tiempo estimado: ~10-15 minutos para todos los tickers
"""

import os
import pickle
import numpy as np
import pandas as pd
from typing import Dict, List
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


def analyze_feature_importance(ticker: str) -> Dict:
    """
    Carga el modelo XGBoost entrenado y extrae feature importance.
    
    Returns:
        Dict con:
            - feature_names: lista de feature names
            - importances: array de importancias
            - top_features: top 10 features
            - bottom_features: bottom 20% features
            - percentile_20: threshold para bottom 20%
    """
    try:
        model_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost.pkl")
        if not os.path.exists(model_path):
            print(f"   [SKIP] Modelo no encontrado para {ticker}")
            return None
        
        with open(model_path, "rb") as f:
            model = pickle.load(f)
        
        # Extraer importancias
        importances = model.feature_importances_
        feature_cols = get_feature_cols(ticker)
        
        # Tomar solo las del último timestep (primeras n_features)
        n_features = len(feature_cols)
        last_importances = importances[:n_features]
        
        # Calcular percentil 20 (threshold)
        percentile_20 = np.percentile(last_importances, 20)
        
        # Identificar features menos importantes
        bottom_indices = np.where(last_importances <= percentile_20)[0]
        bottom_features = [feature_cols[i] for i in bottom_indices]
        
        # Top features
        top_indices = np.argsort(last_importances)[::-1][:10]
        top_features = [(feature_cols[i], float(last_importances[i])) for i in top_indices]
        
        return {
            "ticker": ticker,
            "feature_names": feature_cols,
            "importances": last_importances,
            "top_features": top_features,
            "bottom_features": bottom_features,
            "percentile_20": float(percentile_20),
            "n_bottom": len(bottom_features),
            "n_total": len(feature_cols),
        }
    
    except Exception as e:
        print(f"   [ERROR] Error analizando {ticker}: {e}")
        return None


def retrain_without_bottom_features(ticker: str, feature_importance: Dict) -> Dict:
    """
    Reentrenea el modelo sin los features menos importantes.
    
    Returns:
        Dict con métricas del nuevo entrenamiento
    """
    try:
        # Filtrar features
        filtered_features = [
            f for f in feature_importance["feature_names"]
            if f not in feature_importance["bottom_features"]
        ]
        
        print(f"   [FILTER] Entrenando sin {feature_importance['n_bottom']} features menos importantes...")
        print(f"            Features eliminados: {feature_importance['bottom_features']}")
        
        config = get_config(ticker)
        asset_type = get_asset_type(ticker)
        variations = ENSEMBLE_VARIATIONS[asset_type]
        
        # Preparar datos
        unique_window_sizes = list(set(v["window_size"] for v in variations))
        all_data = prepare_data_multi_window(ticker, config, unique_window_sizes)
        max_ws = max(unique_window_sizes)
        data = all_data[max_ws]
        
        # Entrenar con features filtrados
        xgb_metrics = train_xgboost(ticker, data, filtered_features, asset_type=asset_type)
        
        # Extraer métricas
        return {
            "ticker": ticker,
            "original_features": feature_importance["n_total"],
            "filtered_features": len(filtered_features),
            "removed_count": feature_importance["n_bottom"],
            "xgb_balanced_accuracy": xgb_metrics.get("xgb_balanced_accuracy", 0),
            "xgb_confidence_score": xgb_metrics.get("xgb_confidence_score", 0),
            "xgb_precision_up": xgb_metrics.get("xgb_precision_up", 0),
            "xgb_recall_up": xgb_metrics.get("xgb_recall_up", 0),
            "status": "OK",
        }
    
    except Exception as e:
        print(f"   [ERROR] Error entrenando {ticker}: {e}")
        return {
            "ticker": ticker,
            "status": "ERROR",
            "error": str(e),
        }


def main():
    print("\n" + "="*80)
    print("[*] PHASE 3: FEATURE IMPORTANCE FILTERING")
    print("="*80)
    
    # Cargar tickers
    tickers_config = get_tickers_from_database()
    all_tickers = tickers_config["stable"] + tickers_config["volatile"]
    
    if not all_tickers:
        all_tickers = TICKERS["stable"] + TICKERS["volatile"]
    
    print(f"\n[INFO] Analizando {len(all_tickers)} tickers...\n")
    
    # STEP 1: Analizar feature importance
    print("STEP 1: ANALIZANDO FEATURE IMPORTANCE")
    print("-" * 80)
    
    importance_analysis = {}
    for ticker in all_tickers:
        print(f"  {ticker}...", end=" ")
        analysis = analyze_feature_importance(ticker)
        if analysis:
            importance_analysis[ticker] = analysis
            print(f"✓ ({analysis['n_total']} features, remover {analysis['n_bottom']})")
        else:
            print("✗")
    
    if not importance_analysis:
        print("[ERROR] No se encontraron modelos entrenados")
        return
    
    print(f"\n[OK] Análisis completado para {len(importance_analysis)} tickers")
    
    # STEP 2: Mostrar análisis por ticker
    print("\n\nSTEP 2: ANÁLISIS DETALLADO")
    print("-" * 80)
    
    for ticker, analysis in importance_analysis.items():
        print(f"\n{ticker}:")
        print(f"  • Total features: {analysis['n_total']}")
        print(f"  • Bottom 20% (a remover): {analysis['n_bottom']} features")
        print(f"  • Threshold: {analysis['percentile_20']:.6f}")
        print(f"  • Features a remover: {analysis['bottom_features']}")
        print(f"  • Top 5 features importantes:")
        for i, (fname, imp) in enumerate(analysis['top_features'][:5], 1):
            print(f"    {i}. {fname}: {imp:.6f}")
    
    # STEP 3: Reentrenar sin features menos importantes
    print("\n\nSTEP 3: REENTRENANDO SIN FEATURES MENOS IMPORTANTES")
    print("-" * 80)
    
    retrain_results = {}
    total_start = time.time()
    
    for ticker in all_tickers:
        ticker_start = time.time()
        print(f"\n{ticker}:")
        
        if ticker not in importance_analysis:
            print("   [SKIP] No hay análisis disponible")
            continue
        
        result = retrain_without_bottom_features(ticker, importance_analysis[ticker])
        retrain_results[ticker] = result
        
        elapsed = time.time() - ticker_start
        
        if result.get("status") == "OK":
            print(f"   [OK] Reentrenamiento completado en {elapsed:.1f}s")
            print(f"        Features: {result['original_features']} → {result['filtered_features']}")
            print(f"        BA: {result['xgb_balanced_accuracy']:.2%}")
            print(f"        Confianza: {result['xgb_confidence_score']:.2%}")
        else:
            print(f"   [ERROR] {result.get('error', 'Unknown error')}")
    
    total_elapsed = time.time() - total_start
    
    # STEP 4: Resumen y comparación
    print("\n\n" + "="*80)
    print("STEP 4: RESUMEN Y COMPARACIÓN")
    print("="*80)
    
    print("\nResultados por ticker (Phase 3 vs Current):\n")
    print(f"{'Ticker':<10} {'Features':<12} {'BA Phase3':<12} {'Confianza':<12} {'Status'}")
    print("-" * 60)
    
    for ticker in all_tickers:
        if ticker in retrain_results:
            result = retrain_results[ticker]
            if result.get("status") == "OK":
                feat_str = f"{result['original_features']}→{result['filtered_features']}"
                ba_str = f"{result['xgb_balanced_accuracy']:.2%}"
                conf_str = f"{result['xgb_confidence_score']:.2%}"
                print(f"{ticker:<10} {feat_str:<12} {ba_str:<12} {conf_str:<12} ✓")
            else:
                print(f"{ticker:<10} {'ERROR':<12} {'-':<12} {'-':<12} ✗")
    
    # Calcular promedios
    successful_results = [r for r in retrain_results.values() if r.get("status") == "OK"]
    if successful_results:
        avg_ba = np.mean([r["xgb_balanced_accuracy"] for r in successful_results])
        avg_confidence = np.mean([r["xgb_confidence_score"] for r in successful_results])
        avg_removed = np.mean([r["removed_count"] for r in successful_results])
        
        print("-" * 60)
        print(f"{'PROMEDIO':<10} {f'~{avg_removed:.0f} features':<12} {avg_ba:.2%}{'':6} {avg_confidence:.2%}")
    
    print(f"\n[OK] Phase 3 completada en {total_elapsed/60:.1f} minutos")
    print("\n✅ PRÓXIMOS PASOS:")
    print("   1. Comparar resultados con Phase 1 (original 41.22% confianza promedio)")
    print("   2. Si mejora > 0.5%: USAR phase 3 como nueva configuración base")
    print("   3. Si no hay mejora: MANTENER phase 1 (sin remover features)")
    print("   4. (Opcional) Phase 4: Ensemble averaging (3x más lento, +0.5-1.5%)")


if __name__ == "__main__":
    main()
