"""Test simple de imports y ejecución básica."""
import sys
sys.path.insert(0, ".")

print("Testing imports...")

try:
    from backend.models.model_evaluation import ModelEvaluator
    print("✓ model_evaluation.py")
except Exception as e:
    print(f"✗ model_evaluation.py: {e}")

try:
    from backend.models.xgboost_model import train_xgboost, predict_xgboost
    print("✓ xgboost_model.py")
except Exception as e:
    print(f"✗ xgboost_model.py: {e}")

try:
    from backend.models.validate_model_reliability import ModelReliabilityValidator
    print("✓ validate_model_reliability.py")
except Exception as e:
    print(f"✗ validate_model_reliability.py: {e}")

try:
    from backend.models.data_pipeline import prepare_data_multi_window
    print("✓ data_pipeline.py")
except Exception as e:
    print(f"✗ data_pipeline.py: {e}")

try:
    from backend.models.config import get_config, get_asset_type, get_feature_cols, ENSEMBLE_VARIATIONS
    print("✓ config.py")
except Exception as e:
    print(f"✗ config.py: {e}")

print("\nAll imports successful!")
