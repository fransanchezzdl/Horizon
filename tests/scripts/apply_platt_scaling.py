"""
Apply Platt Scaling calibration to XGBoost predictions and update Supabase BD
=========================================================================
This script:
1. Loads calibrators (LogisticRegression models) for each ticker
2. Applies calibration to confidence scores (raw BiGRU/XGBoost predictions)
3. Updates confianza_bygru in Supabase with calibrated values
"""

import os
import pickle
import numpy as np
import pandas as pd
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

# Calibrators directory
CALIBRATORS_DIR = "backend/models/saved_models"

def load_calibrator(ticker):
    """
    Load pre-trained Platt Scaling calibrator (LogisticRegression)
    
    Args:
        ticker: ticker symbol
    
    Returns:
        calibrator: fitted LogisticRegression model or None
    """
    calibrator_path = os.path.join(CALIBRATORS_DIR, f"{ticker}_calibrator_platt.pkl")
    
    if not os.path.exists(calibrator_path):
        logger.warning(f"[{ticker}] Calibrator not found at {calibrator_path}")
        return None
    
    try:
        with open(calibrator_path, "rb") as f:
            calibrator = pickle.load(f)
        logger.debug(f"[{ticker}] Calibrator loaded successfully")
        return calibrator
    except Exception as e:
        logger.error(f"[{ticker}] Error loading calibrator: {e}")
        return None

def apply_platt_scaling(confidence, ticker, calibrator=None):
    """
    Apply Platt Scaling calibration using pre-trained LogisticRegression
    
    Args:
        confidence: confidence score (0-1, raw probability)
        ticker: ticker symbol (for loading calibrator if not provided)
        calibrator: pre-loaded calibrator (optional)
    
    Returns:
        calibrated_confidence: calibrated score (0-1)
    """
    # Load calibrator if not provided
    if calibrator is None:
        calibrator = load_calibrator(ticker)
    
    if calibrator is None:
        logger.debug(f"[{ticker}] No calibrator, returning original confidence: {confidence:.4f}")
        return confidence
    
    try:
        # Clamp to avoid edge cases
        confidence = np.clip(confidence, 1e-5, 1 - 1e-5)
        
        # Reshape for sklearn: expected (n_samples, 1)
        confidence_reshaped = np.array([[confidence]])
        
        # Apply calibrator: predict_proba returns [[prob_class_0, prob_class_1]]
        calibrated_confidence = calibrator.predict_proba(confidence_reshaped)[0, 1]
        
        return float(calibrated_confidence)
    
    except Exception as e:
        logger.error(f"[{ticker}] Error applying calibration: {e}")
        return confidence


def update_bd_with_calibration():
    """
    Update Supabase BD: fetch all activos, apply calibration, update confianza
    """
    logger.info("=" * 80)
    logger.info("APPLYING PLATT SCALING TO BD")
    logger.info("=" * 80)
    
    # Pre-load all calibrators for efficiency
    logger.info("Loading calibrators...")
    calibrators_cache = {}
    
    for file in os.listdir(CALIBRATORS_DIR):
        if file.endswith("_calibrator_platt.pkl"):
            ticker = file.replace("_calibrator_platt.pkl", "")
            calibrator = load_calibrator(ticker)
            if calibrator is not None:
                calibrators_cache[ticker] = calibrator
    
    logger.info(f"✓ Loaded {len(calibrators_cache)} calibrators")
    
    # Fetch all activos from BD
    response = supabase.table("activos").select("*").execute()
    activos = response.data
    
    logger.info(f"✓ Fetched {len(activos)} registros from BD")
    
    updates_summary = {}
    total_updated = 0
    
    for activo in activos:
        ticker = activo.get("ticker")
        if not ticker:
            continue
        
        old_confidence = float(activo.get("confianza_bygru", 0.5))
        
        # Get calibrator (from cache or None)
        calibrator = calibrators_cache.get(ticker)
        
        # Apply calibration
        new_confidence = apply_platt_scaling(old_confidence, ticker, calibrator)
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
                
                logger.debug(f"[{ticker}] {old_confidence:.4f} → {new_confidence:.4f} ({change:+.4f})")
                
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
    logger.info("[START] Aplicando Platt Scaling a confianza_bygru en BD...")
    
    # Update BD with new calibrators
    update_bd_with_calibration()
    
    logger.info("[SUCCESS] Calibracion completada!")
    
    logger.info("\n✅ ALL DONE: Platt Scaling applied to Supabase BD")
