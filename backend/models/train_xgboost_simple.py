"""
IMPROVED XGBoost TRAINING - SIMPLIFIED VERSION
Script simplificado que priorita robustez sobre features extras.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import argparse
import json
from datetime import datetime
from typing import Dict, Optional

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def train_single_ticker(ticker: str) -> Dict:
    """Entrena un único ticker con el pipeline mejorado."""
    
    print(f"\n{'='*100}")
    print(f"🚀 TRAINING XGBoost (FIXED) FOR {ticker}")
    print(f"{'='*100}")
    
    try:
        # 1. Imports locales para mejor error handling
        from backend.models.config import get_config, get_asset_type, get_feature_cols, ENSEMBLE_VARIATIONS, SAVED_MODELS_DIR
        from backend.models.data_pipeline import prepare_data_multi_window
        from backend.models.xgboost_model import train_xgboost
        
        print(f"\n[1/4] 📥 Preparando datos...")
        config = get_config(ticker)
        asset_type = get_asset_type(ticker)
        
        # 2. Preparar multi-window
        print(f"[2/4] 🔄 Creando secuencias...")
        variations = ENSEMBLE_VARIATIONS.get(asset_type, [{"window_size": 30}])
        window_sizes = [v.get("window_size", 30) for v in variations]
        
        all_data = prepare_data_multi_window(ticker, config, window_sizes)
        max_ws = max(window_sizes)
        data_dict = all_data.get(max_ws)
        
        if data_dict is None:
            logger.error(f"No data for {ticker}")
            return {"error": f"No data for window size {max_ws}", "ticker": ticker}
        
        # 3. Entrenar
        print(f"[3/4] 🌳 Entrenando XGBoost...")
        feature_cols = get_feature_cols(ticker)
        xgb_results = train_xgboost(ticker, data_dict, feature_cols)
        
        # 4. Resumen
        print(f"[4/4] 📊 Generando reporte...")
        
        result = {
            "ticker": ticker,
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "metrics": {
                "balanced_accuracy": xgb_results.get('xgb_balanced_accuracy', 0),
                "macro_f1": xgb_results.get('xgb_macro_f1', 0),
                "directional_accuracy": xgb_results.get('xgb_directional_accuracy', 0),
            },
            "thresholds": {
                "down": xgb_results.get('xgb_down_threshold', 0),
                "up": xgb_results.get('xgb_up_threshold', 0),
            },
        }
        
        print(f"\n{'='*100}")
        print(f"✅ TRAINING COMPLETED FOR {ticker}")
        print(f"{'='*100}")
        print(f"\n📈 METRICS:")
        print(f"   • Balanced Accuracy: {result['metrics']['balanced_accuracy']:.1%} ⭐")
        print(f"   • Macro F1 Score:    {result['metrics']['macro_f1']:.1%}")
        print(f"   • Directional Acc:   {result['metrics']['directional_accuracy']:.1%}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error training {ticker}: {str(e)}", exc_info=True)
        return {
            "ticker": ticker,
            "status": "error",
            "error": str(e)
        }


def main():
    parser = argparse.ArgumentParser(description="Train XGBoost model (simplified)")
    parser.add_argument("--ticker", type=str, help="Single ticker to train (e.g., KO)")
    parser.add_argument("--batch", action="store_true", help="Train batch")
    parser.add_argument("--batch-size", type=int, help="Limit batch size")
    
    args = parser.parse_args()
    
    if args.ticker:
        result = train_single_ticker(args.ticker)
        print(f"\n{json.dumps(result, indent=2, default=str)}")
    elif args.batch:
        print("Batch mode not yet implemented in simplified version")
    else:
        print("Use --ticker=SYMBOL")
        parser.print_help()


if __name__ == "__main__":
    main()
