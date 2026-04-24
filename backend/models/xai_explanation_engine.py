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
import base64
import logging
from typing import Dict, List, Any, Optional
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
            # Lista de arrays por clase: [n_samples, n_features] × n_classes
            shap_vals = shap_values_obj[2][0]
        elif isinstance(shap_values_obj, np.ndarray) and shap_values_obj.ndim == 3:
            # ndarray shape (n_samples, n_features, n_classes)
            shap_vals = shap_values_obj[0, :, 2]
        else:
            # Binary: (n_samples, n_features)
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
    
    # Mapa de nombres técnicos → etiquetas legibles para el usuario
    _FEATURE_LABELS = {
        "Close":            "Precio de cierre",
        "Volume":           "Volumen",
        "RSI":              "RSI (sobrecompra/venta)",
        "MACD":             "MACD (momentum)",
        "EMA":              "Media móvil exponencial",
        "Bollinger_PctB":   "Posición en Bandas Bollinger",
        "ATR":              "Volatilidad diaria (ATR)",
        "Log_Return":       "Retorno logarítmico",
        "Volume_Ratio":     "Ratio de volumen",
        "SMA200_Dist":      "Distancia a SMA200",
        "SMA50_Slope":      "Pendiente SMA50",
        "Realized_Vol":     "Volatilidad realizada",
        "SMA200_Regime":    "Régimen de mercado",
        "VIX_Close":        "Índice de miedo (VIX)",
        "NASDAQ_Return":    "Retorno NASDAQ",
        "CMF":              "Flujo de dinero (CMF)",
        "OBV":              "Volumen en balance (OBV)",
        "Aroon_Up":         "Aroon alcista",
        "Aroon_Down":       "Aroon bajista",
        "DX":               "Índice direccional (DX)",
        "CCI":              "Canal de materias (CCI)",
        "TSI":              "Índice fuerza real (TSI)",
        "KST":              "Know Sure Thing (KST)",
        "CMO":              "Oscilador Chande (CMO)",
        "Ultimate_Osc":     "Oscilador Ultimate",
        "momentum_5d":      "Momentum 5 días",
        "rsi_14":           "RSI 14 períodos",
        "macd_signal":      "MACD vs señal",
        "bbands_pct":       "% Bandas Bollinger",
        "atr_14":           "ATR 14 períodos",
        "obv_momentum":     "Momentum OBV",
        "volume_sma_ratio": "Volumen / SMA ratio",
        "high_low_ratio":   "Rango Alto-Bajo",
        "close_range_pct":  "Posición en rango diario",
        "roc_10":           "Tasa de cambio 10d",
        "volatility_std":   "Volatilidad STD 20d",
        "price_acceleration":"Aceleración del precio",
    }

    _SUFFIX_LABELS = {
        "_last":  "actual",
        "_mean":  "promedio ventana",
        "_std":   "variabilidad ventana",
        "_trend": "tendencia ventana",
    }

    @classmethod
    def _humanize_feature(cls, raw_name: str) -> str:
        """Convierte 'RSI_last' → 'RSI (sobrecompra/venta) — actual'."""
        for suffix, suffix_label in cls._SUFFIX_LABELS.items():
            if raw_name.endswith(suffix):
                base = raw_name[: -len(suffix)]
                base_label = cls._FEATURE_LABELS.get(base, base)
                return f"{base_label} — {suffix_label}"
        return cls._FEATURE_LABELS.get(raw_name, raw_name)

    def _generate_force_plot(self, X_instance: np.ndarray, senal: str) -> str:
        """
        Genera SHAP Waterfall plot (Top 10 features) como PNG base64.

        Muestra las 5 features que más empujan hacia la predicción y las 5
        que más la frenan, con nombres legibles para el usuario final.
        El color rojo indica impacto negativo (baja probabilidad de ALCISTA),
        el azul indica impacto positivo.

        Returns:
            Base64 encoded PNG image, o "" si falla.
        """
        if not self.explainer_shap or not SHAP_AVAILABLE or not MATPLOTLIB_AVAILABLE:
            return ""

        try:
            import io
            import matplotlib.patches as mpatches

            if X_instance.ndim == 1:
                X_instance = X_instance.reshape(1, -1)

            shap_values_obj = self.explainer_shap.shap_values(X_instance)

            # Seleccionar clase según señal (0=BAJISTA, 1=LATERAL, 2=ALCISTA)
            cls_map = {"BAJISTA": 0, "LATERAL": 1, "ALCISTA": 2}
            cls_idx = cls_map.get(senal, 2)

            if isinstance(shap_values_obj, np.ndarray) and shap_values_obj.ndim == 3:
                # shape (n_samples, n_features, n_classes)
                shap_vals = shap_values_obj[0, :, cls_idx]
            elif isinstance(shap_values_obj, list):
                shap_vals = shap_values_obj[cls_idx][0]
            else:
                shap_vals = shap_values_obj[0]

            feat_names = self.feature_names if self.feature_names else [f"F{i}" for i in range(len(shap_vals))]

            # Humanizar nombres
            readable = [self._humanize_feature(f) for f in feat_names]

            # Seleccionar Top 5 positivos y Top 5 negativos por valor absoluto
            pairs = list(zip(readable, shap_vals))
            positivos = sorted([(n, v) for n, v in pairs if v > 0], key=lambda x: x[1], reverse=True)[:5]
            negativos = sorted([(n, v) for n, v in pairs if v < 0], key=lambda x: x[1])[:5]
            top_items = negativos + positivos  # negativos abajo, positivos arriba

            if not top_items:
                return ""

            names  = [x[0] for x in top_items]
            values = [x[1] for x in top_items]
            colors = ["#E74C3C" if v < 0 else "#2980B9" for v in values]

            # ── Layout ─────────────────────────────────────────────────────────
            fig, ax = plt.subplots(figsize=(10, 5))
            fig.patch.set_facecolor("#F8F9FA")
            ax.set_facecolor("#F8F9FA")

            y_pos = np.arange(len(names))
            bars = ax.barh(y_pos, values, color=colors, alpha=0.88,
                           height=0.6, edgecolor="white", linewidth=0.5)

            # Valor numérico al lado de cada barra
            for bar, val in zip(bars, values):
                sign = "+" if val > 0 else ""
                ax.text(
                    val + (0.0003 if val >= 0 else -0.0003),
                    bar.get_y() + bar.get_height() / 2,
                    f"{sign}{val:.4f}",
                    va="center",
                    ha="left" if val >= 0 else "right",
                    fontsize=8.5,
                    color="#2C3E50",
                )

            ax.set_yticks(y_pos)
            ax.set_yticklabels(names, fontsize=9.5, color="#2C3E50")
            ax.axvline(0, color="#7F8C8D", linewidth=0.9, linestyle="--")
            ax.set_xlabel("Impacto en la predicción (valor SHAP)", fontsize=10, color="#555")

            senal_color = {"ALCISTA": "#27AE60", "BAJISTA": "#E74C3C", "LATERAL": "#F39C12"}.get(senal, "#555")
            ax.set_title(
                f"¿Por qué el modelo predice {senal}?  —  Top factores",
                fontsize=12, fontweight="bold", color=senal_color, pad=12,
            )

            # Leyenda
            patch_pos = mpatches.Patch(color="#2980B9", alpha=0.88, label="Empuja hacia esta predicción")
            patch_neg = mpatches.Patch(color="#E74C3C", alpha=0.88, label="Frena esta predicción")
            ax.legend(handles=[patch_pos, patch_neg], fontsize=8.5,
                      loc="lower right", framealpha=0.7)

            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_visible(False)
            ax.tick_params(left=False)
            plt.tight_layout(pad=1.5)

            buffer = io.BytesIO()
            plt.savefig(buffer, format="png", dpi=130, bbox_inches="tight",
                        facecolor=fig.get_facecolor())
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            plt.close(fig)

            return image_base64

        except Exception as e:
            logger.warning(f"⚠️ Error generando waterfall plot: {e}")
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
