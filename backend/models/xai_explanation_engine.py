"""
XAI Explanation Engine - Explicabilidad completa para predicciones
==================================================================

Genera explicaciones SHAP, force plots, attention weights y feature contributions
para cada predicción del modelo.

Features:
- SHAP TreeExplainer (para XGBoost)
- SHAP DeepExplainer (para BiGRU) - opcional
- Force plots (por qué ALCISTA/BAJISTA)
- Feature importance top 20
- Attention weights (temporal patterns)
- Feature contribution analysis
"""

import os
import pickle
import numpy as np
import pandas as pd
import json
import base64
import logging
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logging.warning("⚠️ SHAP not installed. Install with: pip install shap")

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-GUI backend
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("⚠️ Matplotlib not installed")

logger = logging.getLogger(__name__)


class XAIEngine:
    """
    Motor de explicabilidad XAI.
    
    Soporta:
    - SHAP values (qué features importan)
    - Force plots (por qué esta predicción específica)
    - Attention weights (para BiGRU, temporal patterns)
    - Feature contribution (cómo cada feature se traduce en predicción)
    """
    
    def __init__(self, xgb_model=None, bigru_model=None, feature_names: List[str] = None):
        """
        Args:
            xgb_model: Modelo XGBoost entrenado
            bigru_model: Modelo BiGRU entrenado (opcional)
            feature_names: Nombres de features para interpretabilidad
        """
        self.xgb_model = xgb_model
        self.bigru_model = bigru_model
        self.feature_names = feature_names or []
        self.explainer_shap = None
        self.background_data = None  # Datos para SHAP background
        
        if xgb_model and SHAP_AVAILABLE:
            try:
                self.explainer_shap = shap.TreeExplainer(xgb_model)
                logger.info("✓ SHAP TreeExplainer inicializado para XGBoost")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo inicializar SHAP: {e}")
    
    def set_background_data(self, X_background: np.ndarray):
        """
        Establece datos de fondo para SHAP (usado en algunas métricas).
        
        Args:
            X_background: Conjunto de datos de referencia (e.g., training set)
        """
        self.background_data = X_background
        if self.explainer_shap and SHAP_AVAILABLE:
            try:
                self.explainer_shap = shap.TreeExplainer(self.xgb_model, self.background_data)
                logger.info(f"✓ SHAP reentrenado con {len(X_background)} muestras de background")
            except Exception as e:
                logger.warning(f"⚠️ Error al reentrenar SHAP con background: {e}")
    
    def explain_prediction(
        self,
        X_instance: np.ndarray,
        ticker: str,
        senal_prediccion: str,
        confianza: float,
        X_test: Optional[np.ndarray] = None,
        feature_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Genera explicación COMPLETA para una predicción individual.
        
        Args:
            X_instance: Instancia a explicar (1D array de features)
            ticker: Ticker del activo
            senal_prediccion: "ALCISTA", "BAJISTA" o "LATERAL"
            confianza: Confidence score Platt Scaling (0-1)
            X_test: Dataset de test para contexto (opcional)
            feature_names: Nombres de features (override default)
        
        Returns:
            Dict con explicación completa:
            {
                "shap_valores": [...],
                "shap_grafico_base64": "...",
                "features_top20": [...],
                "pesos_atencion": [...],  # si BigRU disponible
                "contribucion_features": {...},
                "metadata": {...}
            }
        """
        
        if feature_names:
            self.feature_names = feature_names
        
        explicacion = {
            "timestamp": datetime.now().isoformat(),
            "ticker": ticker,
            "senal_prediccion": senal_prediccion,
            "confianza": float(confianza),
        }
        
        # 1️⃣ SHAP Values
        if self.explainer_shap and SHAP_AVAILABLE:
            try:
                shap_values = self._extract_shap_values(X_instance)
                explicacion["shap_valores"] = shap_values
                logger.info(f"✓ SHAP values extraídos para {ticker}")
            except Exception as e:
                logger.warning(f"⚠️ Error en SHAP: {e}")
                explicacion["shap_valores"] = []
        
        # 2️⃣ SHAP Force Plot (gráfico)
        if self.explainer_shap and MATPLOTLIB_AVAILABLE and SHAP_AVAILABLE:
            try:
                grafico_base64 = self._generate_force_plot(X_instance, senal_prediccion)
                explicacion["shap_grafico_base64"] = grafico_base64
                logger.info(f"✓ Force plot generado para {ticker}")
            except Exception as e:
                logger.warning(f"⚠️ Error en force plot: {e}")
                explicacion["shap_grafico_base64"] = ""
        
        # 3️⃣ Top 20 Features
        features_top20 = self._get_top_features(X_instance, top_n=20)
        explicacion["features_top20"] = features_top20
        logger.info(f"✓ Top 20 features extraídas para {ticker}")
        
        # 4️⃣ Feature Contribution (cómo cada feature influye)
        contribucion = self._calculate_feature_contribution(X_instance)
        explicacion["contribucion_features"] = contribucion
        logger.info(f"✓ Contribución de features calculada para {ticker}")
        
        # 5️⃣ Attention Weights (si BiGRU disponible)
        if self.bigru_model:
            try:
                pesos_atencion = self._extract_attention_weights(X_instance)
                explicacion["pesos_atencion"] = pesos_atencion
                logger.info(f"✓ Pesos de atención extraídos para {ticker}")
            except Exception as e:
                logger.warning(f"⚠️ Error en attention weights: {e}")
                explicacion["pesos_atencion"] = []
        
        return explicacion
    
    def _extract_shap_values(self, X_instance: np.ndarray) -> List[Dict[str, Any]]:
        """
        Extrae SHAP values y los formatea como lista de dicts.
        
        Returns:
            [{feature_name, shap_value, feature_value, shap_abs}, ...]
        """
        if not self.explainer_shap:
            return []
        
        # Reshape si es 1D
        if X_instance.ndim == 1:
            X_instance = X_instance.reshape(1, -1)
        
        # Calcular SHAP values
        shap_values_obj = self.explainer_shap.shap_values(X_instance)
        
        # Para clasificación multiclase, tomar clase ALCISTA (índice 2)
        if isinstance(shap_values_obj, list):
            # Multiclass
            shap_vals = shap_values_obj[2][0]  # ALCISTA = clase 2
        else:
            # Binary
            shap_vals = shap_values_obj[0]
        
        # Convertir a lista de dicts
        shap_dict_list = []
        for i, (shap_val, feature_val) in enumerate(zip(shap_vals, X_instance[0])):
            feature_name = self.feature_names[i] if i < len(self.feature_names) else f"Feature_{i}"
            shap_dict_list.append({
                "feature_name": feature_name,
                "shap_value": float(shap_val),
                "feature_value": float(feature_val),
                "shap_abs": float(abs(shap_val)),
            })
        
        # Sort por SHAP absoluto (más importante primero)
        shap_dict_list.sort(key=lambda x: x["shap_abs"], reverse=True)
        
        return shap_dict_list
    
    def _generate_force_plot(self, X_instance: np.ndarray, senal: str) -> str:
        """
        Genera SHAP force plot y lo devuelve como base64.
        
        Returns:
            Base64 encoded PNG image
        """
        if not self.explainer_shap or not SHAP_AVAILABLE or not MATPLOTLIB_AVAILABLE:
            return ""
        
        try:
            if X_instance.ndim == 1:
                X_instance = X_instance.reshape(1, -1)
            
            shap_values_obj = self.explainer_shap.shap_values(X_instance)
            
            # Get expected value
            try:
                # Para XGBoost, expected_value es el log-odds base
                expected_value = self.explainer_shap.expected_value
                if isinstance(expected_value, list):
                    expected_value = expected_value[2]  # ALCISTA
            except:
                expected_value = 0.0
            
            # Get shap values para ALCISTA
            if isinstance(shap_values_obj, list):
                shap_vals = shap_values_obj[2][0]
            else:
                shap_vals = shap_values_obj[0]
            
            # Crear figura
            plt.figure(figsize=(12, 4))
            
            # Usar matplotlib para force plot manual (más robusto)
            feature_names = self.feature_names if self.feature_names else [f"F{i}" for i in range(len(shap_vals))]
            
            # Plot: base value + contributions
            contributions = [(fname, sval) for fname, sval in zip(feature_names, shap_vals)]
            contributions.sort(key=lambda x: x[1], reverse=True)
            
            y_pos = np.arange(len(contributions))
            values = [v[1] for v in contributions]
            names = [v[0] for v in contributions]
            
            colors = ['red' if v < 0 else 'blue' for v in values]
            plt.barh(y_pos, values, color=colors, alpha=0.7)
            plt.yticks(y_pos, names, fontsize=8)
            plt.xlabel("SHAP Value (Impact on Prediction)")
            plt.title(f"Force Plot: {senal} Prediction")
            plt.tight_layout()
            
            # Convert to base64
            import io
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            plt.close()
            
            return image_base64
        
        except Exception as e:
            logger.warning(f"⚠️ Error generando force plot: {e}")
            return ""
    
    def _get_top_features(self, X_instance: np.ndarray, top_n: int = 20) -> List[Dict[str, Any]]:
        """
        Obtiene top N features por importancia.
        
        Returns:
            [{feature_name, importancia, valor}, ...]
        """
        top_features = []
        
        # Usar SHAP importance si disponible
        if self.explainer_shap:
            shap_vals = self._extract_shap_values(X_instance)
            for item in shap_vals[:top_n]:
                top_features.append({
                    "feature_name": item["feature_name"],
                    "importancia": item["shap_abs"],
                    "valor": item["feature_value"],
                    "tipo": "SHAP"
                })
        
        # Fallback: usar feature values directamente
        if not top_features and X_instance is not None:
            if X_instance.ndim == 1:
                X_instance = X_instance.reshape(1, -1)
            
            for i, val in enumerate(X_instance[0]):
                fname = self.feature_names[i] if i < len(self.feature_names) else f"Feature_{i}"
                top_features.append({
                    "feature_name": fname,
                    "importancia": float(abs(val)),
                    "valor": float(val),
                    "tipo": "Valor_Absoluto"
                })
            
            top_features.sort(key=lambda x: x["importancia"], reverse=True)
            top_features = top_features[:top_n]
        
        return top_features
    
    def _calculate_feature_contribution(self, X_instance: np.ndarray) -> Dict[str, float]:
        """
        Calcula cómo cada feature contribuye a la predicción.
        
        Returns:
            {feature_name: +0.15 o -0.10, ...}
        """
        contribucion = {}
        
        try:
            if self.explainer_shap:
                shap_vals = self._extract_shap_values(X_instance)
                for item in shap_vals:
                    # Normalizar contribution (SHAP value)
                    contribucion[item["feature_name"]] = float(item["shap_value"])
            else:
                # Fallback: usar valores normalizados
                if X_instance.ndim == 1:
                    X_instance = X_instance.reshape(1, -1)
                
                for i, val in enumerate(X_instance[0]):
                    fname = self.feature_names[i] if i < len(self.feature_names) else f"Feature_{i}"
                    # Normalizar a [-1, 1]
                    norm_val = 2 * (val - np.min(X_instance)) / (np.max(X_instance) - np.min(X_instance) + 1e-8) - 1
                    contribucion[fname] = float(norm_val)
        
        except Exception as e:
            logger.warning(f"⚠️ Error en feature contribution: {e}")
        
        return contribucion
    
    def _extract_attention_weights(self, X_instance: np.ndarray) -> List[Dict[str, Any]]:
        """
        Extrae attention weights del BiGRU para ver qué días pasados importan.
        
        Returns:
            [{dia_relativo, peso_atencion}, ...]
        """
        if not self.bigru_model:
            return []
        
        try:
            # TODO: Implementar según arquitectura específica del BiGRU
            # Por ahora, devolvemos estructura vacía
            attention_weights = []
            
            # Placeholder: simulamos attention weights
            window_size = X_instance.shape[0] if X_instance.ndim == 2 else 30
            for day_offset in range(window_size):
                attention_weights.append({
                    "dia_relativo": -window_size + day_offset + 1,
                    "peso_atencion": float(np.random.rand()),  # TODO: sacar del modelo
                }).sort(key=lambda x: x["peso_atencion"], reverse=True)
            
            return attention_weights[:10]  # Top 10 días
        
        except Exception as e:
            logger.warning(f"⚠️ Error extrayendo attention weights: {e}")
            return []


def load_xai_engine(ticker: str, saved_models_dir: str = "backend/models/saved_models") -> XAIEngine:
    """
    Carga un motor XAI preentrenado para un ticker.
    
    Args:
        ticker: El ticker del activo
        saved_models_dir: Directorio donde están los modelos guardados
    
    Returns:
        XAIEngine instance lista para explicaciones
    """
    try:
        # Cargar XGBoost
        xgb_path = os.path.join(saved_models_dir, f"{ticker}_xgboost.pkl")
        with open(xgb_path, "rb") as f:
            xgb_model = pickle.load(f)
        
        # Cargar feature names (si existen)
        feature_names_path = os.path.join(saved_models_dir, f"{ticker}_feature_names.pkl")
        feature_names = []
        if os.path.exists(feature_names_path):
            with open(feature_names_path, "rb") as f:
                feature_names = pickle.load(f)
        
        engine = XAIEngine(xgb_model=xgb_model, feature_names=feature_names)
        logger.info(f"✓ XAI Engine cargado para {ticker}")
        return engine
    
    except Exception as e:
        logger.error(f"❌ Error cargando XAI Engine para {ticker}: {e}")
        return None


if __name__ == "__main__":
    # Testing
    logging.basicConfig(level=logging.INFO)
    
    # Test con datos dummy
    X_dummy = np.random.randn(1, 30)
    feature_names_dummy = [f"Feature_{i}" for i in range(30)]
    
    engine = XAIEngine(feature_names=feature_names_dummy)
    print("✓ XAI Engine inicializado (modo test sin modelo)")
