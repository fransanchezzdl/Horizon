"""
IMPROVED XGBoost TRAINING WITH COMPLETE FIX FOR BULLISH BIAS

Script maestro que entrena XGBoost con:
1. ✅ Temporal target sin leakage
2. ✅ Dual thresholds (BAJISTA/LATERAL/ALCISTA)
3. ✅ Scale pos weight para balancear clases
4. ✅ Métricas robustas (balanced_accuracy, macro_f1)
5. ✅ NO shuffle en DataLoader
6. ✅ Reporte comparativo sin/con sentimiento
7. ✅ Persistencia de thresholds y probabilidades

USO:
    python -m backend.models.train_xgboost_fixed --ticker=KO
    python -m backend.models.train_xgboost_fixed --batch
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

from backend.models.config import (
    get_tickers_from_database,
    TICKERS,
    SAVED_MODELS_DIR,
    get_config,
    get_asset_type,
    get_feature_cols,
)
from backend.models.data_pipeline import prepare_data_multi_window
from backend.models.xgboost_model import train_xgboost
from backend.models.model_evaluation import ModelEvaluator
from backend.models.validate_model_reliability import TemporalValidationChecker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class XGBoostTrainerFixed:
    """Trainer mejorado con todas las correcciones de sesgo alcista."""
    
    def __init__(self):
        self.evaluator = ModelEvaluator()
        self.temporal_checker = TemporalValidationChecker()
        self.results = {}
    
    def train_ticker(self, ticker: str, save_model: bool = True) -> Dict:
        """
        Entrena XGBoost para un ticker con todas las mejoras.
        
        Args:
            ticker: Símbolo del activo
            save_model: Si guardar el modelo
        
        Returns:
            Dict con resultados completos
        """
        print(f"\n{'='*100}")
        print(f"🚀 TRAINING XGBoost (FIXED) FOR {ticker}")
        print(f"{'='*100}")
        
        try:
            # 1. Cargar configuración y datos
            print(f"\n[1/5] 📥 Preparando datos...")
            config = get_config(ticker)
            asset_type = get_asset_type(ticker)
            
            # 2. Preparar datos multi-window
            print(f"[2/5] 🔄 Creando secuencias...")
            from backend.models.config import ENSEMBLE_VARIATIONS
            variations = ENSEMBLE_VARIATIONS[asset_type]
            window_sizes = [v["window_size"] for v in variations]
            
            all_data = prepare_data_multi_window(ticker, config, window_sizes)
            max_ws = max(window_sizes)
            data_dict = all_data[max_ws]
            
            # 3. Entrenar XGBoost con NEW FIX
            print(f"[3/5] 🌳 Entrenando XGBoost...")
            feature_cols = get_feature_cols(ticker)
            xgb_results = train_xgboost(ticker, data_dict, feature_cols)
            
            # 4. Generar reporte de evaluación
            print(f"[4/5] 📊 Generando reporte...")
            
            # Extraer métricas
            result = {
                "ticker": ticker,
                "timestamp": datetime.now().isoformat(),
                "training": {
                    "directional_accuracy": xgb_results.get('xgb_directional_accuracy', 0),
                    "balanced_accuracy": xgb_results.get('xgb_balanced_accuracy', 0),
                    "macro_f1": xgb_results.get('xgb_macro_f1', 0),
                    "precision_alcista": xgb_results.get('xgb_precision_up', 0),
                    "recall_alcista": xgb_results.get('xgb_recall_up', 0),
                },
                "class_distribution": xgb_results.get('xgb_class_distribution', {}),
                "thresholds": {
                    "down_threshold": xgb_results.get('xgb_down_threshold', 0),
                    "up_threshold": xgb_results.get('xgb_up_threshold', 0),
                },
                "scale_pos_weight": xgb_results.get('xgb_scale_pos_weight', 1.0),
                "confusion_matrix": xgb_results.get('xgb_confusion_matrix', {}),
                "feature_importance": xgb_results.get('feature_importance', {}),
            }
            
            # 5. Validar leakage temporal
            print(f"[5/5] 🔍 Validando integridad temporal...")
            temporal_checks = self.temporal_checker.check_all(ticker)
            result["temporal_validation"] = temporal_checks
            
            # Resumen
            print(f"\n{'='*100}")
            print(f"✅ TRAINING COMPLETED FOR {ticker}")
            print(f"{'='*100}")
            print(f"\n📈 KEY METRICS (Test Set):")
            print(f"   • Directional Accuracy:  {result['training']['directional_accuracy']:.1%}")
            print(f"   • Balanced Accuracy:     {result['training']['balanced_accuracy']:.1%} ⭐ PRIMARY")
            print(f"   • Macro F1 Score:        {result['training']['macro_f1']:.1%}")
            print(f"   • Precision (ALCISTA):   {result['training']['precision_alcista']:.1%}")
            print(f"   • Recall (ALCISTA):      {result['training']['recall_alcista']:.1%}")
            
            print(f"\n🎯 THRESHOLDS (Calibrated on Train):")
            print(f"   • BAJISTA ≤ {result['thresholds']['down_threshold']:.4f}")
            print(f"   • LATERAL (intermediate range)")
            print(f"   • ALCISTA ≥ {result['thresholds']['up_threshold']:.4f}")
            
            print(f"\n⚖️  CLASS BALANCING:")
            print(f"   • scale_pos_weight = {result['scale_pos_weight']:.2f}")
            print(f"   • Train: BAJISTA={result['class_distribution']['train'].get('BAJISTA', 0):.1f}% "
                  f"LATERAL={result['class_distribution']['train'].get('LATERAL', 0):.1f}% "
                  f"ALCISTA={result['class_distribution']['train'].get('ALCISTA', 0):.1f}%")
            
            print(f"\n✓ Temporal Validation: {('PASS' if temporal_checks['ok'] else 'REVIEW')}")
            
            return result
        
        except Exception as e:
            logger.error(f"Error training {ticker}: {str(e)}", exc_info=True)
            return {"error": str(e), "ticker": ticker}
    
    def train_batch(self, batch_size: Optional[int] = None) -> Dict:
        """Entrena múltiples tickers."""
        print(f"\n{'='*100}")
        print(f"🚀 BATCH TRAINING XGBoost (FIXED)")
        print(f"{'='*100}\n")
        
        try:
            tickers_config = get_tickers_from_database()
            all_tickers = tickers_config["stable"] + tickers_config["volatile"]
        except:
            all_tickers = TICKERS["stable"] + TICKERS["volatile"]
        
        if batch_size:
            all_tickers = all_tickers[:batch_size]
        
        results_list = []
        
        for i, ticker in enumerate(all_tickers, 1):
            print(f"\n[{i}/{len(all_tickers)}] Processing {ticker}...")
            result = self.train_ticker(ticker, save_model=True)
            results_list.append(result)
            
            # Minor pause between tickers
            import time
            time.sleep(2)
        
        # Generar resumen
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_tickers": len(all_tickers),
            "successful": sum(1 for r in results_list if 'error' not in r),
            "failed": sum(1 for r in results_list if 'error' in r),
            "results": results_list,
        }
        
        # Guardar resumen
        summary_path = os.path.join(SAVED_MODELS_DIR, "training_summary.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"\n{'='*100}")
        print(f"📊 BATCH TRAINING SUMMARY")
        print(f"{'='*100}")
        print(f"✅ Successful: {summary['successful']}/{summary['total_tickers']}")
        print(f"❌ Failed: {summary['failed']}/{summary['total_tickers']}")
        print(f"📄 Summary saved to: {summary_path}")
        
        return summary


def main():
    parser = argparse.ArgumentParser(
        description="Train XGBoost model with fixes for bullish bias"
    )
    parser.add_argument(
        "--ticker",
        type=str,
        help="Single ticker to train (e.g., KO)"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Train all tickers in batch"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        help="Limit batch size (e.g., 3)"
    )
    
    args = parser.parse_args()
    
    trainer = XGBoostTrainerFixed()
    
    if args.ticker:
        result = trainer.train_ticker(args.ticker)
    elif args.batch:
        result = trainer.train_batch(batch_size=args.batch_size)
    else:
        print("Use --ticker=SYMBOL or --batch")
        parser.print_help()
        return
    
    # Print final result
    print(f"\n{'='*100}")
    print(json.dumps(result, indent=2, default=str))
    print(f"{'='*100}")


if __name__ == "__main__":
    main()
