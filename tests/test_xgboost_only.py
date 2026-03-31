"""
Script de prueba: Entrena SOLO XGBoost para comparar con BiGRU

Muestra:
- Accuracy de XGBoost directa (sin BiGRU)
- Comparación BiGRU vs XGBoost
- Para ayudarte decidir si conviene cambiar de arquitectura
"""

import time
from datetime import timedelta
from typing import Dict

from backend.models.config import get_tickers_from_database, TICKERS
from backend.models.ensemble import train_ensemble
from backend.models.data_pipeline import prepare_data_multi_window
from backend.models.xgboost_model import train_xgboost
from backend.models.config import get_config, get_asset_type, ENSEMBLE_VARIATIONS, get_feature_cols


def test_xgboost_only():
    """
    Entrena SOLO XGBoost para todos los tickers y muestra accuracy.
    """
    
    # Cargar tickers
    print("\n" + "="*80)
    print("🌳 TEST XGBOOST SOLO — Sin BiGRU")
    print("="*80)
    
    tickers_config = get_tickers_from_database()
    all_tickers = tickers_config["stable"] + tickers_config["volatile"]
    
    if not all_tickers:
        all_tickers = TICKERS["stable"] + TICKERS["volatile"]
    
    print(f"\n📍 Tickers a evaluar: {all_tickers}\n")
    
    results = []
    total_start = time.time()
    
    for ticker in all_tickers:
        ticker_start = time.time()
        try:
            print(f"\n{'─'*80}")
            print(f"🔄 Procesando {ticker}...")
            print(f"{'─'*80}")
            
            config = get_config(ticker)
            asset_type = get_asset_type(ticker)
            variations = ENSEMBLE_VARIATIONS[asset_type]
            
            # Preparar datos
            unique_window_sizes = list(set(v["window_size"] for v in variations))
            all_data = prepare_data_multi_window(ticker, config, unique_window_sizes)
            
            # Usar window_size mayor
            max_ws = max(unique_window_sizes)
            data = all_data[max_ws]
            
            feature_cols = get_feature_cols(ticker)
            
            # Entrenar XGBoost
            print(f"   📚 Entrenando XGBoost...")
            xgb_metrics = train_xgboost(ticker, data, feature_cols)
            
            elapsed = time.time() - ticker_start
            
            # Extraer accuracy
            xgb_acc = xgb_metrics.get("xgb_directional_accuracy", 0)
            xgb_prec = xgb_metrics.get("xgb_precision_up", 0)
            xgb_rec = xgb_metrics.get("xgb_recall_up", 0)
            
            result = {
                "ticker": ticker,
                "xgb_accuracy": xgb_acc,
                "xgb_precision": xgb_prec,
                "xgb_recall": xgb_rec,
                "elapsed": elapsed,
                "status": "OK"
            }
            
            print(f"\n   ✅ {ticker} completado:")
            print(f"      • XGBoost Accuracy: {xgb_acc:.2%}")
            print(f"      • Precision (UP): {xgb_prec:.2%}")
            print(f"      • Recall (UP): {xgb_rec:.2%}")
            print(f"      • Tiempo: {elapsed:.1f}s")
            
            results.append(result)
            
        except Exception as e:
            elapsed = time.time() - ticker_start
            print(f"\n   ❌ Error en {ticker}: {e}")
            results.append({
                "ticker": ticker,
                "status": "ERROR",
                "error": str(e),
                "elapsed": elapsed
            })
    
    # ── Resumen final ──────────────────────────────────────────────────────────
    total_elapsed = time.time() - total_start
    
    print(f"\n{'='*80}")
    print(f"📊 RESUMEN XGBOOST SOLO")
    print(f"{'='*80}\n")
    
    successful = [r for r in results if r["status"] == "OK"]
    
    if successful:
        print(f"{'Ticker':<12} {'XGB Acc':<12} {'Precision':<12} {'Recall':<12} {'Tiempo':<10}")
        print(f"{'─'*60}")
        
        for r in successful:
            ticker = r["ticker"]
            acc = r["xgb_accuracy"]
            prec = r["xgb_precision"]
            rec = r["xgb_recall"]
            elapsed = r["elapsed"]
            
            print(f"{ticker:<12} {acc:>10.2%}     {prec:>10.2%}     {rec:>10.2%}   {elapsed:>8.1f}s")
        
        print(f"{'─'*60}")
        avg_acc = sum(r["xgb_accuracy"] for r in successful) / len(successful)
        avg_time = sum(r["elapsed"] for r in successful)
        
        print(f"{'PROMEDIO':<12} {avg_acc:>10.2%}")
        print(f"\n⏱️  Tiempo total: {str(timedelta(seconds=int(total_elapsed)))}")
        print(f"   Por ticker: {avg_time/len(successful):.1f}s promedio")
        
        print(f"\n💾 Tiempo vs BiGRU:")
        print(f"   • XGBoost SOLO: ~{len(all_tickers) * 30}s = {len(all_tickers) * 30 / 60:.1f} min")
        print(f"   • BiGRU+XGB+STACKING: ~{len(all_tickers) * 300}s = {len(all_tickers) * 300 / 60:.1f} min")
        
    else:
        print("❌ Todos los entrenamientos fallaron")
    
    # Errores
    failed = [r for r in results if r["status"] == "ERROR"]
    if failed:
        print(f"\n⚠️  Errores ({len(failed)}):")
        for r in failed:
            print(f"   • {r['ticker']}: {r.get('error', 'desconocido')}")
    
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    test_xgboost_only()
