"""
Apply Platt Scaling calibration to XGBoost predictions and update Supabase BD
=========================================================================
This script:
1. Loads calibration parameters (a, b) for each ticker
2. Creates a platt_scale.pkl file with the parameters
3. Applies calibration to confidence scores (already computed from max proba)
4. Updates confianza_bygru in Supabase with calibrated values
"""

import os
import pickle
import numpy as np
import pandas as pd
from scipy.special import logit, expit  # logit = log(p/(1-p)), expit = sigmoid
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime
import logging

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv("backend/.env")

# Supabase config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Platt Scaling parameters (from calibration analysis)
PLATT_PARAMS = {
    "AAPL": {"a": 0.0614, "b": 1.7121},
    "AMZN": {"a": 3.4973, "b": 4.3757},
    "BABA": {"a": 0.4045, "b": 1.8344},
    "GOOGL": {"a": 0.0936, "b": 1.7232},
    "INTC": {"a": 0.2217, "b": 0.9073},
    "KO": {"a": 0.3142, "b": 1.9663},
    "META": {"a": 0.2997, "b": 2.2009},
    "MSFT": {"a": -0.5166, "b": 1.1386},
    "NFLX": {"a": 0.1967, "b": 2.8291},
    "NVDA": {"a": 0.2512, "b": 1.8784},
    "TSLA": {"a": 0.9481, "b": 2.1403},
    "VXX": {"a": 1.0060, "b": 1.4131},
}

def apply_platt_scaling(confidence, ticker):
    """
    Apply Platt Scaling: P_calib = sigmoid(a * logit(P_pred) + b)
    
    Args:
        confidence: confidence score (0-1, typically from max probability)
        ticker: ticker symbol to get correct parameters
    
    Returns:
        calibrated_confidence: calibrated score (0-1)
    """
    if ticker not in PLATT_PARAMS:
        logger.warning(f"Ticker {ticker} not in calibration params, returning original")
        return confidence
    
    # Clamp to avoid logit singularities
    confidence = np.clip(confidence, 1e-5, 1 - 1e-5)
    
    params = PLATT_PARAMS[ticker]
    a = params["a"]
    b = params["b"]
    
    # Apply Platt Scaling: sigmoid(a * logit(P) + b)
    log_odds = logit(confidence)
    calibrated_log_odds = a * log_odds + b
    calibrated_confidence = expit(calibrated_log_odds)
    
    return float(calibrated_confidence)


def save_calibration_params():
    """Save calibration parameters to pickle for easy loading"""
    save_path = "backend/models/platt_scaling_params.pkl"
    with open(save_path, "wb") as f:
        pickle.dump(PLATT_PARAMS, f)
    logger.info(f"✓ Calibration parameters saved to {save_path}")


def update_bd_with_calibration():
    """
    Update Supabase BD: fetch all activos, apply calibration, update confianza
    """
    logger.info("=" * 80)
    logger.info("APPLYING PLATT SCALING TO BD")
    logger.info("=" * 80)
    
    # Fetch all activos from BD
    response = supabase.table("activos").select("*").execute()
    activos = response.data
    
    logger.info(f"Fetched {len(activos)} registros from BD")
    
    updates_summary = {}
    total_updated = 0
    
    for activo in activos:
        ticker = activo["ticker"]
        old_confidence = float(activo.get("confianza_bygru", 0.5))
        
        # Apply calibration
        new_confidence = apply_platt_scaling(old_confidence, ticker)
        change = new_confidence - old_confidence
        
        # Only update if change is meaningful (>0.001)
        if abs(change) > 0.001:
            try:
                supabase.table("activos").update({
                    "confianza_bygru": new_confidence,
                    "updated_at": datetime.now().isoformat()
                }).eq("ticker", ticker).execute()
                
                total_updated += 1
                
                if ticker not in updates_summary:
                    updates_summary[ticker] = []
                
                updates_summary[ticker].append({
                    "before": old_confidence,
                    "after": new_confidence,
                    "change": change
                })
                
            except Exception as e:
                logger.error(f"Error updating activo {ticker}: {e}")
    
    logger.info(f"\n✓ Updated {total_updated} registros in BD")
    
    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("CALIBRATION UPDATE SUMMARY")
    logger.info("=" * 80)
    
    for ticker in sorted(updates_summary.keys()):
        updates = updates_summary[ticker]
        avg_before = np.mean([u["before"] for u in updates])
        avg_after = np.mean([u["after"] for u in updates])
        avg_change = np.mean([u["change"] for u in updates])
        
        logger.info(f"\n{ticker}:")
        logger.info(f"  Average: {avg_before:.2%} → {avg_after:.2%} ({avg_change:+.2%})")
        logger.info(f"  Updated {len(updates)} registros")
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ PLATT SCALING APPLIED TO PRODUCTION")
    logger.info("=" * 80)


if __name__ == "__main__":
    # Save calibration parameters
    save_calibration_params()
    
    # Update BD
    update_bd_with_calibration()
    
    logger.info("\n✅ ALL DONE: Platt Scaling applied to Supabase BD")
