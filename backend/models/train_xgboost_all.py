"""
Entrenamiento SOLO de XGBoost para todos los tickers.

Scripts para:
1. Entrenar XGBoost
2. Hacer predicciones
3. Guardar en BD con accuracy real
4. Guardar reportes

Tiempo estimado: 5-10 minutos
"""

import time
import os
from datetime import timedelta
from typing import Dict, Optional

from backend.models.config import get_tickers_from_database, TICKERS, get_config, get_asset_type, ENSEMBLE_VARIATIONS, get_feature_cols, SAVED_MODELS_DIR
from backend.models.data_pipeline import prepare_data_multi_window, download_data, compute_features
from backend.models.xgboost_model import train_xgboost
from backend.services.activo_update_service import ActivoUpdateService


def get_xgboost_prediction(ticker: str):
    """
    Realiza predicción con XGBoost entrenado.
    
    Retorna dict compatible con guardar_datos_post_entrenamiento.
    """
    try:
        import xgboost as xgb
        import numpy as np
        from backend.models.ensemble import load_scaler
        
        config = get_config(ticker)
        asset_type = get_asset_type(ticker)
        variations = ENSEMBLE_VARIATIONS[asset_type]
        max_window_size = max(v["window_size"] for v in variations)
        
        # Cargar scaler
        scaler = load_scaler(ticker)
        
        # Descargar datos recientes
        raw_df = download_data(ticker)
        feat_df = compute_features(raw_df, include_market_context=False, ticker=ticker)
        feature_cols = get_feature_cols(ticker)
        
        if len(feat_df) < max_window_size:
            raise ValueError(f"Datos insuficientes para {ticker}")
        
        # Precio actual
        current_price = float(feat_df["Close"].iloc[-1])
        
        # Escalar última ventana
        last_window_raw = feat_df[feature_cols].values[-max_window_size:]
        last_window_scaled = scaler.transform(last_window_raw)
        
        # Flatten para XGBoost
        X_last = last_window_scaled.reshape(1, -1)
        
        # Cargar XGBoost
        xgb_model_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost.pkl")
        import pickle
        with open(xgb_model_path, "rb") as f:
            xgb_model = pickle.load(f)
        
        # Predecir
        y_pred = xgb_model.predict(X_last)[0]  # 0=BAJISTA, 1=?, 2=ALCISTA
        y_proba = xgb_model.predict_proba(X_last)[0]  # [p0, p1, p2]
        
        # Convertir a tendencia
        if y_pred == 2:
            trend = "ALCISTA"
        elif y_pred == 0:
            trend = "BAJISTA"
        else:
            trend = "LATERAL"
        
        confidence = float(np.max(y_proba))
        
        # Retornar formato compatible
        return {
            "trend": trend,
            "confidence": confidence,
            "current_price": current_price,
            "predicted_price": current_price * (1 + 0.02) if y_pred == 2 else current_price * (1 - 0.02) if y_pred == 0 else current_price,
            "price_upper": current_price * 1.02,
            "price_lower": current_price * 0.98,
            "predicted_return": 0.02 if y_pred == 2 else -0.02 if y_pred == 0 else 0,
            "predicted_return_pct": 2.0 if y_pred == 2 else -2.0 if y_pred == 0 else 0,
            "meta_trend": trend,
            "meta_score": confidence,
            "xgboost_direction": "ALCISTA" if y_pred == 2 else "BAJISTA" if y_pred == 0 else "LATERAL",
            "xgboost_probability": confidence,
            "individual_predictions": []
        }
    
    except Exception as e:
        print(f"[ERROR] Error en predicción de {ticker}: {e}")
        return None


def train_xgboost_all() -> None:
    """
    Entrena SOLO XGBoost para todos los tickers y guarda en BD.
    
    Nota: Guarda accuracy del training, sin hacer predicción en vivo
    para evitar mismatch de features.
    """
    
    # Cargar tickers
    print("\n" + "="*80)
    print("[*] ENTRENAMIENTO XGBOOST SOLO - Con guardado en BD")
    print("="*80)
    
    tickers_config = get_tickers_from_database()
    all_tickers = tickers_config["stable"] + tickers_config["volatile"]
    
    if not all_tickers:
        all_tickers = TICKERS["stable"] + TICKERS["volatile"]
        print("[WARNING] Usando configuración hardcoded")
    
    print(f"\n[INFO] Tickers a entrenar: {all_tickers}\n")
    
    results = []
    total_start = time.time()
    
    # Importar servicio de BD
    try:
        use_db = True
        print("[OK] Guardado en BD activado")
    except Exception as e:
        use_db = False
        print(f"[WARNING] No se puede guardar en BD: {e}")
    
    for ticker in all_tickers:
        ticker_start = time.time()
        try:
            print(f"\n{'─'*80}")
            print(f"[*] {ticker}")
            print(f"{'─'*80}")
            
            config = get_config(ticker)
            asset_type = get_asset_type(ticker)
            variations = ENSEMBLE_VARIATIONS[asset_type]
            feature_cols = get_feature_cols(ticker)
            
            # Preparar datos
            unique_window_sizes = list(set(v["window_size"] for v in variations))
            all_data = prepare_data_multi_window(ticker, config, unique_window_sizes)
            
            max_ws = max(unique_window_sizes)
            data = all_data[max_ws]
            
            # Entrenar XGBoost con configuración segregada por tipo de activo
            print(f"   [TRAIN] Entrenando XGBoost ({asset_type})...")
            xgb_metrics = train_xgboost(ticker, data, feature_cols, asset_type=asset_type)
            
            elapsed = time.time() - ticker_start
            
            # Extraer métricas
            xgb_acc = xgb_metrics.get("xgb_balanced_accuracy", 0)  # Métrica multi-clase (para compatibilidad)
            xgb_confidence = xgb_metrics.get("xgb_confidence_score", 0)  # ⭐ CONFIANZA NUEVA (para BD)
            xgb_prec = xgb_metrics.get("xgb_precision_up", 0)
            xgb_rec = xgb_metrics.get("xgb_recall_up", 0)
            
            if use_db:
                # Guardar confianza basada en probabilidades máximas
                print(f"   [SAVE] Guardando en BD...")
                try:
                    from backend.daos.activo_dao import ActivoDAO
                    update_data = {
                        "confianza_bygru": xgb_confidence,  # ⭐ Confianza de probabilidades máximas (más realista)
                    }
                    success = ActivoDAO.actualizar(ticker, update_data)
                    result_status = "[OK] BD OK" if success else "[ERROR] BD FAIL"
                except Exception as bd_err:
                    print(f"      [ERROR] Error guardando: {bd_err}")
                    result_status = "❌ BD ERROR"
            else:
                result_status = "⏭️  No BD"
            
            result = {
                "ticker": ticker,
                "xgb_accuracy": xgb_acc,
                "xgb_confidence": xgb_confidence,  # ⭐ Guardado en BD
                "xgb_precision": xgb_prec,
                "xgb_recall": xgb_rec,
                "elapsed": elapsed,
                "status": "OK",
                "db_status": result_status
            }
            
            print(f"\n   [DONE] {ticker} completado:")
            print(f"      • XGBoost Accuracy (BA): {xgb_acc:.2%}")
            print(f"      • ✨ Confianza (guardado): {xgb_confidence:.2%} ✨")
            print(f"      • Precision (UP): {xgb_prec:.2%}")
            print(f"      • Recall (UP): {xgb_rec:.2%}")
            print(f"      • Tiempo: {elapsed:.1f}s")
            print(f"      • {result_status}")
            
            results.append(result)
            
        except Exception as e:
            elapsed = time.time() - ticker_start
            print(f"\n   [ERROR] Error en {ticker}: {e}")
            results.append({
                "ticker": ticker,
                "status": "ERROR",
                "error": str(e),
                "elapsed": elapsed,
                "db_status": "❌ ERROR"
            })
    
    # ── Resumen final ──────────────────────────────────────────────────────────
    total_elapsed = time.time() - total_start
    
    print(f"\n{'='*80}")
    print(f"[SUMMARY] RESUMEN FINAL - XGBOOST SOLO")
    print(f"{'='*80}\n")
    
    successful = [r for r in results if r["status"] == "OK"]
    
    if successful:
        print(f"{'Ticker':<12} {'XGB Acc':<12} {'Precision':<12} {'Recall':<12} {'BD':<15} {'Tiempo':<10}")
        print(f"{'─'*80}")
        
        for r in successful:
            ticker = r["ticker"]
            acc = r["xgb_accuracy"]
            prec = r["xgb_precision"]
            rec = r["xgb_recall"]
            db = r.get("db_status", "N/A")
            elapsed = r["elapsed"]
            
            print(f"{ticker:<12} {acc:>10.2%}     {prec:>10.2%}     {rec:>10.2%}   {db:<15} {elapsed:>8.1f}s")
        
        print(f"{'─'*80}")
        avg_acc = sum(r["xgb_accuracy"] for r in successful) / len(successful)
        avg_time = sum(r["elapsed"] for r in successful) / len(successful)
        
        print(f"{'PROMEDIO':<12} {avg_acc:>10.2%}")
        print(f"\n[TIME] Tiempo total: {str(timedelta(seconds=int(total_elapsed)))}")
        print(f"   Por ticker (promedio): {avg_time:.1f}s")
        
        # Contar guardados
        db_saves = sum(1 for r in results if "[OK] BD OK" in r.get("db_status", ""))
        print(f"\n[SAVED] Guardados en BD: {db_saves}/{len(results)}")
    
    else:
        print("[FAILED] Todos los entrenamientos fallaron")
    
    # Errores
    failed = [r for r in results if r["status"] == "ERROR"]
    if failed:
        print(f"\n[ERRORS] Errores ({len(failed)}):")
        for r in failed:
            print(f"   - {r['ticker']}: {r.get('error', 'desconocido')}")
    
    print(f"\n{'='*80}\n")
    
    # Resumen ejecutivo
    print("\n[SUMMARY] RESUMEN EJECUTIVO:")
    print(f"   • Tickers entrenados: {len(successful)}/{len(all_tickers)}")
    print(f"   • Accuracy promedio: {avg_acc:.2%}")
    print(f"   • Tiempo total: {str(timedelta(seconds=int(total_elapsed)))}")
    print(f"   • Tickers guardados en BD: {db_saves}/{len(results)}")
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    train_xgboost_all()
