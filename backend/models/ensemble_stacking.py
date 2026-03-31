"""
Ensemble Stacking: Meta-model LightGBM que combina BiGRU + XGBoost.

Arquitectura:
1. BiGRU predice: probabilidades de 3 clases
2. XGBoost predice: directional (0/1/2) + confidence
3. Meta-model (LightGBM) aprende en validation set a combinar ambas
4. Test: Meta-model predice clase final integrando ambos modelos

Ventajas:
- BiGRU: captura tendencias a largo plazo
- XGBoost: captura patrones cortos y features macro
- Meta-model: aprende pesos óptimos automáticamente
"""

import numpy as np
import torch
import lightgbm as lgb
import pickle
from typing import Tuple, Dict, Optional
import warnings

warnings.filterwarnings('ignore')


class EnsembleStackingMetaModel:
    """
    Meta-model que stacks predicciones de BiGRU y XGBoost usando LightGBM.
    """
    
    def __init__(self, verbose: bool = False):
        """
        Inicializa meta-model.
        
        Args:
            verbose: Si mostrar logs
        """
        self.verbose = verbose
        self.meta_model = None
        self.trained = False
        self.feature_names = ['bigru_prob_bajista', 'bigru_prob_lateral', 'bigru_prob_alcista',
                             'xgb_pred', 'xgb_pred_proba']
        
    def predict_bigru_proba(self, model, X_tensor: torch.Tensor, device) -> np.ndarray:
        """
        Obtiene probabilidades de BiGRU.
        
        Args:
            model: BiGRU model
            X_tensor: Input tensor (batch, seq_len, features)
            device: Dispositivo
            
        Returns:
            Array de probabilidades (batch, 3) — cada fila suma a 1
        """
        model.eval()
        with torch.no_grad():
            X_tensor = X_tensor.to(device)
            logits = model(X_tensor)  # (batch, 3)
            proba = torch.softmax(logits, dim=1)  # (batch, 3)
        return proba.cpu().numpy()
    
    def create_stacking_features(
        self,
        bigru_proba: np.ndarray,
        xgb_predictions: np.ndarray,
        xgb_predict_proba: np.ndarray
    ) -> np.ndarray:
        """
        Crea features para el meta-model.
        
        Args:
            bigru_proba: (n_samples, 3) — probabilidades BiGRU
            xgb_predictions: (n_samples,) — predicción XGBoost (0, 1, 2)
            xgb_predict_proba: (n_samples, 3) — probabilidades XGBoost (si disponible)
            
        Returns:
            (n_samples, 5) features para LightGBM
        """
        n_samples = bigru_proba.shape[0]
        
        # Convertir predicción XGBoost a one-hot para confidence
        xgb_confidence = np.zeros(n_samples)
        if xgb_predict_proba is not None:
            # Confidence = max probability de XGBoost
            xgb_confidence = np.max(xgb_predict_proba, axis=1)
        else:
            xgb_confidence = np.ones(n_samples) * 0.8  # Default confidence
        
        # Stack features: [bigru_p0, bigru_p1, bigru_p2, xgb_pred, xgb_conf]
        features = np.column_stack([
            bigru_proba[:, 0],  # P(BAJISTA) from BiGRU
            bigru_proba[:, 1],  # P(LATERAL) from BiGRU
            bigru_proba[:, 2],  # P(ALCISTA) from BiGRU
            xgb_predictions.astype(float),  # XGBoost prediction (0, 1, 2)
            xgb_confidence,  # XGBoost confidence
        ])
        
        return features
    
    def train_meta_model(
        self,
        X_val_stacking: np.ndarray,
        y_val: np.ndarray,
        X_test_stacking: np.ndarray,
        y_test: np.ndarray,
    ) -> Dict:
        """
        Entrena meta-model LightGBM en validation set.
        
        Args:
            X_val_stacking: (n_val, 5) features de stacking en validation
            y_val: (n_val,) targets en validation
            X_test_stacking: (n_test, 5) features de stacking en test
            y_test: (n_test,) targets en test
            
        Returns:
            Dict con métricas y modelo
        """
        # Crear datasets LightGBM
        train_data = lgb.Dataset(X_val_stacking, label=y_val)
        test_data = lgb.Dataset(X_test_stacking, label=y_test, reference=train_data)
        
        # Parámetros
        params = {
            'objective': 'multiclass',
            'num_class': 3,
            'metric': 'multi_logloss',
            'num_leaves': 31,
            'learning_rate': 0.1,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1 if not self.verbose else 100
        }
        
        if self.verbose:
            print(f"   📚 Entrenando meta-model LightGBM ({X_val_stacking.shape[0]} validation samples)...")
        
        # Entrenar
        self.meta_model = lgb.train(
            params,
            train_data,
            num_boost_round=200,
            valid_sets=[test_data],
            callbacks=[
                lgb.early_stopping(30),
                lgb.log_evaluation(period=0) if not self.verbose else lgb.log_evaluation(period=50)
            ]
        )
        
        self.trained = True
        
        # Evaluar en test
        y_pred = self.meta_model.predict(X_test_stacking)  # (n_test, 3) probabilidades
        y_pred_class = np.argmax(y_pred, axis=1)  # (n_test,) clases predichas
        
        # Calcular accuracy
        accuracy = np.mean(y_pred_class == y_test)
        
        # Calcular F1
        from sklearn.metrics import f1_score
        f1 = f1_score(y_test, y_pred_class, average='weighted', zero_division=0)
        
        metrics = {
            'accuracy': accuracy,
            'f1_weighted': f1,
            'n_estimators': len(self.meta_model.feature_importance()),
        }
        
        if self.verbose:
            print(f"      ✅ Meta-model trained: {accuracy:.2%} accuracy, {f1:.4f} F1")
        
        return metrics, y_pred
    
    def predict_ensemble(
        self,
        bigru_proba: np.ndarray,
        xgb_predictions: np.ndarray,
        xgb_predict_proba: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predice usando ensemble stacking.
        
        Args:
            bigru_proba: (n_samples, 3) probabilidades BiGRU
            xgb_predictions: (n_samples,) predicción XGBoost
            xgb_predict_proba: (n_samples, 3) probabilidades XGBoost
            
        Returns:
            (y_pred, y_proba) clases y probabilidades del ensemble
        """
        if not self.trained:
            raise ValueError("Meta-model not trained yet!")
        
        # Crear features
        X_stacking = self.create_stacking_features(bigru_proba, xgb_predictions, xgb_predict_proba)
        
        # Predecir con meta-model
        y_proba = self.meta_model.predict(X_stacking)  # (n_samples, 3)
        y_pred = np.argmax(y_proba, axis=1)  # (n_samples,)
        
        return y_pred, y_proba
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Devuelve importancia de features del meta-model"""
        if not self.trained:
            return {}
        
        importance_dict = dict(zip(
            self.feature_names,
            self.meta_model.feature_importance(importance_type='gain')
        ))
        
        return importance_dict


def load_stacking_metalearner(ticker: str, verbose: bool = False) -> Optional['EnsembleStackingMetaModel']:
    """
    Carga meta-model de stacking guardado para un ticker.
    
    Args:
        ticker: Símbolo del activo
        verbose: Si mostrar logs
        
    Returns:
        EnsembleStackingMetaModel con meta-model cargado, o None si no existe
    """
    import os
    from .config import SAVED_MODELS_DIR
    
    meta_model_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_stacking_metalearner.pkl")
    
    if not os.path.exists(meta_model_path):
        return None  # No hay meta-model entrenado
    
    # Cargar
    with open(meta_model_path, "rb") as f:
        loaded_lgb_model = pickle.load(f)
    
    # Recrear wrapper
    meta = EnsembleStackingMetaModel(verbose=verbose)
    meta.meta_model = loaded_lgb_model
    meta.trained = True
    
    if verbose:
        print(f"🔗 Meta-model de stacking cargado para {ticker}")
    
    return meta


def demonstrate_stacking():
    """Demostración de ensemble stacking con datos ficticios"""
    
    print("="*80)
    print("ENSEMBLE STACKING DEMONSTRATION")
    print("="*80)
    
    # Simular predicciones de BiGRU y XGBoost (datasets pequeños)
    n_val = 100
    n_test = 50
    
    # BiGRU: probabilidades aleatorias (simuladas)
    bigru_proba_val = np.random.dirichlet([1, 1, 1], n_val)  # (100, 3) suman a 1
    xgb_pred_val = np.random.randint(0, 3, n_val)  # (100,) predicciones 0,1,2
    xgb_proba_val = np.random.dirichlet([1, 1, 1], n_val)
    
    bigru_proba_test = np.random.dirichlet([1, 1, 1], n_test)
    xgb_pred_test = np.random.randint(0, 3, n_test)
    xgb_proba_test = np.random.dirichlet([1, 1, 1], n_test)
    
    # Targets ficticios
    y_val = np.random.randint(0, 3, n_val)
    y_test = np.random.randint(0, 3, n_test)
    
    # Crear meta-model
    meta = EnsembleStackingMetaModel(verbose=False)  # verbose=False para menos logs
    
    # Entrenar
    metrics, y_pred_proba = meta.train_meta_model(
        meta.create_stacking_features(bigru_proba_val, xgb_pred_val, xgb_proba_val),
        y_val,
        meta.create_stacking_features(bigru_proba_test, xgb_pred_test, xgb_proba_test),
        y_test
    )
    
    print(f"\n✅ Meta-Model Entrenado (LightGBM):")
    print(f"  - Accuracy: {metrics['accuracy']:.2%}")
    print(f"  - F1 Weighted: {metrics['f1_weighted']:.4f}")
    
    # Feature importance
    importance = meta.get_feature_importance()
    print(f"\n📊 Feature Importance:")
    for feat, imp in sorted(importance.items(), key=lambda x: x[1], reverse=True):
        print(f"   {feat:20s}: {imp:.4f}")
    
    # Predecir
    y_pred, y_proba = meta.predict_ensemble(bigru_proba_test, xgb_pred_test, xgb_proba_test)
    
    print(f"\n📈 Ejemplos de predicciones (primeras 5):")
    class_names = ['BAJISTA', 'LATERAL', 'ALCISTA']
    for i in range(5):
        pred_class = class_names[y_pred[i]]
        confidence = y_proba[i].max()
        print(f"   {i}: {pred_class:8s} (confidence: {confidence:.2%})")


if __name__ == "__main__":
    demonstrate_stacking()
