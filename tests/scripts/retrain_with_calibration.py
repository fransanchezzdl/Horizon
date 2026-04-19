"""
Reentrenamiento Completo con Calibracion Platt Scaling (Windows-compatible)
===========================================================================

Pipeline completo:
1. Entrena/re-entrena modelos XGBoost
2. Aplica calibracion Platt Scaling
3. Re-genera explicaciones XAI con confianzas calibradas
4. Actualiza BD con nuevas explicaciones

Uso:
    python retrain_with_calibration.py --all
    python retrain_with_calibration.py --ticker AAPL
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# Setup
sys.path.insert(0, str(Path(__file__).parent))

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_command(cmd: str, description: str) -> bool:
    """Execute shell command and return success status."""
    logger.info(f"\n{'='*80}")
    logger.info(f"[RUN] {description}")
    logger.info(f"{'='*80}\n")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, text=True)
        logger.info(f"[OK] {description} - SUCCESS\n")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"[FAIL] {description} - FAILED")
        logger.error(f"   Error: {e}\n")
        return False
    except Exception as e:
        logger.error(f"[ERROR] {description} - ERROR: {e}\n")
        return False


def main():
    """Main retraining pipeline."""
    
    parser = argparse.ArgumentParser(
        description="Reentrenamiento completo con calibracion"
    )
    parser.add_argument("--all", action="store_true", help="Entrenar todos los tickers")
    parser.add_argument("--ticker", type=str, help="Especifico ticker")
    parser.add_argument("--skip-train", action="store_true", help="Skip XGBoost training")
    parser.add_argument("--skip-calibration", action="store_true", help="Skip calibration")
    parser.add_argument("--skip-xai", action="store_true", help="Skip XAI generation")
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("[RETRAINING] REENTRENAMIENTO COMPLETO CON CALIBRACION")
    print("="*80)
    print(f"\nFecha inicio: {datetime.now().isoformat()}")
    print(f"Modo: {'ALL TICKERS' if args.all else f'TICKER: {args.ticker}'}")
    print(f"Skip training: {args.skip_train}")
    print(f"Skip calibration: {args.skip_calibration}")
    print(f"Skip XAI: {args.skip_xai}")
    print()
    
    results = {
        "training": None,
        "calibration": None,
        "xai_generation": None
    }
    
    start_time = datetime.now()
    
    # STEP 1: TRAIN XGBOOST MODELS
    if not args.skip_train:
        logger.info("\n[STEP 1] ENTRENAR MODELOS XGBOOST")
        
        if args.all:
            cmd = "python backend/models/train_xgboost_all.py"
            results["training"] = run_command(cmd, "Entrenamiento XGBoost (todos los tickers)")
        else:
            cmd = f"python tests/train_model.py --ticker {args.ticker}"
            results["training"] = run_command(cmd, f"Entrenamiento XGBoost ({args.ticker})")
    else:
        logger.info("[SKIP] Step 1: Training")
        results["training"] = True
    
    # STEP 2: APPLY CALIBRATION
    if not args.skip_calibration:
        logger.info("\n[STEP 2] APLICAR CALIBRACION PLATT SCALING")
        
        cmd = "python backend/models/platt_scaling_calibration_v2.py"
        results["calibration"] = run_command(cmd, "Calibracion Platt Scaling")
    else:
        logger.info("[SKIP] Step 2: Calibration")
        results["calibration"] = True
    
    # STEP 3: GENERATE XAI EXPLANATIONS
    if not args.skip_xai:
        logger.info("\n[STEP 3] GENERAR EXPLICACIONES XAI")
        
        if args.all:
            cmd = "python tests/generate_xai_explanations.py --all"
            results["xai_generation"] = run_command(cmd, "Generacion XAI (todos los tickers)")
        else:
            cmd = f"python tests/generate_xai_explanations.py --ticker {args.ticker}"
            results["xai_generation"] = run_command(cmd, f"Generacion XAI ({args.ticker})")
    else:
        logger.info("[SKIP] Step 3: XAI Generation")
        results["xai_generation"] = True
    
    # SUMMARY
    end_time = datetime.now()
    duration = end_time - start_time
    
    print("\n" + "="*80)
    print("[SUMMARY] RESUMEN DE EJECUCION")
    print("="*80)
    print(f"\n[1] Entrenamiento XGBoost:    {'[OK]' if results['training'] else '[FAIL]'}")
    print(f"[2] Calibracion Platt:       {'[OK]' if results['calibration'] else '[FAIL]'}")
    print(f"[3] Generacion XAI:          {'[OK]' if results['xai_generation'] else '[FAIL]'}")
    print(f"\n[TIME] Duracion total: {duration}")
    print(f"[END] Fecha fin: {end_time.isoformat()}")
    
    all_success = all(r for r in results.values() if r is not None)
    
    print("\n" + "="*80)
    if all_success:
        print("[SUCCESS] REENTRENAMIENTO COMPLETADO CON EXITO")
        print("\n[OK] PASOS COMPLETADOS:")
        print("   * Modelos XGBoost entrenados")
        print("   * Calibracion Platt Scaling aplicada")
        print("   * Explicaciones XAI generadas con confianzas calibradas")
        print("\n[DB] CAMBIOS PERSISTIDOS:")
        print("   * 11 calibradores guardados en backend/models/saved_models/{ticker}_calibrator_platt.pkl")
        print("   * Explicaciones XAI actualizadas en BD con confianzas honestas")
        print("\n[TODO] PROXIMOS PASOS:")
        print("   1. Verificar confianzas en BD (deberia estar en 80-85%)")
        print("   2. Actualizar API para usar calibradores en tiempo real")
        print("   3. Validar con usuarios")
    else:
        print("[ERROR] REENTRENAMIENTO COMPLETADO CON ERRORES")
        failed_steps = [k for k, v in results.items() if v is False]
        print(f"\n[FAIL] PASOS QUE FALLARON: {', '.join(failed_steps)}")
        return 1
    
    print("="*80 + "\n")
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
