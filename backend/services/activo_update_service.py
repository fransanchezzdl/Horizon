"""
Servicio para actualizar los activos con datos del modelo de predicción.

Responsabilidades:
- Procesar resultados del modelo (accuracy, predicciones)
- Extraer el último precio disponible
- Generar señal IA basada en la tendencia
- Actualizar la tabla `activos` con estos datos
"""

from typing import Optional, Dict, List
import numpy as np
from ..daos import activo_dao, historico_dao


class ActivoUpdateService:
    """Servicio para actualizar activos con datos de modelos y predicciones."""
    
    @staticmethod
    def actualizar_activo_con_prediccion(
        ticker: str,
        accuracy: float,
        predicciones: List[float],
        precio_actual: float
    ) -> bool:
        """
        Actualiza un activo con los resultados completos de una predicción.
        
        Args:
            ticker: Símbolo del ticker (ej: AAPL, BTC-USD)
            accuracy: Accuracy del modelo (0-1)
            predicciones: Lista de predicciones futuras
            precio_actual: Precio actual del activo
        
        Returns:
            bool: True si la actualización fue exitosa
        """
        try:
            # Calcular tendencia basada en predicciones
            senal_ia = ActivoUpdateService._determinar_senal(predicciones)
            
            # Preparar datos para actualizar
            update_data = {
                "confianza_bygru": float(accuracy),
                "precio": float(precio_actual),
                "senal_ia": senal_ia
            }
            
            # Actualizar activo
            return activo_dao.actualizar(ticker, update_data)
        
        except Exception as e:
            print(f"Error actualizando activo {ticker}: {e}")
            return False
    
    @staticmethod
    def actualizar_activo_minimalista(
        ticker: str,
        accuracy: float,
        precio_actual: float,
        senal: str
    ) -> bool:
        """
        Actualiza un activo con datos mínimos (sin necesidad de predicciones detalladas).
        
        Args:
            ticker: Símbolo del ticker
            accuracy: Accuracy del modelo (0-1)
            precio_actual: Precio actual
            senal: ALCISTA, BAJISTA o LATERAL
        
        Returns:
            bool: True si exitoso
        """
        try:
            if senal not in ["ALCISTA", "BAJISTA", "LATERAL"]:
                print(f"Señal inválida: {senal}")
                return False
            
            return activo_dao.actualizar_senal_ia(ticker, senal, accuracy) and \
                   activo_dao.actualizar_precio(ticker, precio_actual)
        
        except Exception as e:
            print(f"Error actualizando activo {ticker}: {e}")
            return False
    
    @staticmethod
    def _determinar_senal(predicciones: List[float]) -> str:
        """
        Determina la señal IA basada en predicciones futuras.
        
        Lógica:
        - ALCISTA: Si la mayoría de predicciones van al alza
        - BAJISTA: Si la mayoría de predicciones van a la baja
        - LATERAL: Si hay cambios mixtos
        """
        try:
            if not predicciones or len(predicciones) < 2:
                return "LATERAL"
            
            predicciones = np.array(predicciones)
            cambios = np.diff(predicciones)
            
            alcistas = np.sum(cambios > 0)
            bajistas = np.sum(cambios < 0)
            total = len(cambios)
            
            pct_alcista = alcistas / total if total > 0 else 0
            pct_bajista = bajistas / total if total > 0 else 0
            
            THRESHOLD = 0.6  # 60% en misma dirección
            
            if pct_alcista > THRESHOLD:
                return "ALCISTA"
            elif pct_bajista > THRESHOLD:
                return "BAJISTA"
            else:
                return "LATERAL"
        
        except Exception as e:
            print(f"Error determinando señal: {e}")
            return "LATERAL"
    
    @staticmethod
    def extraer_ultimo_precio(ticker: str, dias: int = 30) -> Optional[float]:
        """
        Extrae el último precio disponible del histórico.
        """
        try:
            historicos = historico_dao.obtener_ultimos_dias(ticker, dias)
            
            if historicos and len(historicos) > 0:
                return float(historicos[0].precio_cierre)
            
            return None
        
        except Exception as e:
            print(f"Error extrayendo último precio de {ticker}: {e}")
            return None
    
    @staticmethod
    def extraer_precision_del_modelo(
        predictions: List[float],
        actual_values: List[float]
    ) -> float:
        """
        Calcula el accuracy del modelo (MAPE convertido a 0-1).
        """
        try:
            if not predictions or not actual_values or len(predictions) != len(actual_values):
                return 0.0
            
            predictions = np.array(predictions)
            actual_values = np.array(actual_values)
            
            if np.any(actual_values == 0):
                mae = np.mean(np.abs(predictions - actual_values))
                accuracy = max(0, 1 - (mae / np.mean(np.abs(actual_values))))
            else:
                mape = np.mean(np.abs((actual_values - predictions) / actual_values))
                accuracy = max(0, 1 - mape)
            
            return float(np.clip(accuracy, 0, 1))
        
        except Exception as e:
            print(f"Error calculando precisión: {e}")
            return 0.0
    
    @staticmethod
    def actualizar_multiples_activos(activos_data: List[Dict]) -> Dict[str, bool]:
        """
        Actualiza múltiples activos en una sola operación.
        
        Args:
            activos_data: Lista de dicts con:
                {
                    "ticker": str,
                    "confianza_bygru": float (0-1),
                    "precio": float,
                    "senal_ia": str (ALCISTA/BAJISTA/LATERAL)
                }
        """
        resultados = {}
        
        try:
            for activo_data in activos_data:
                ticker = activo_data.get("ticker")
                
                if not ticker:
                    print("⚠️  Activo sin ticker, saltando...")
                    continue
                
                exito = activo_dao.actualizar(ticker, activo_data)
                resultados[ticker] = exito
                
                if exito:
                    print(f"{ticker} actualizado")
                else:
                    print(f"{ticker} no se pudo actualizar")
            
            return resultados
        
        except Exception as e:
            print(f"Error actualizando múltiples activos: {e}")
            return resultados
    
    @staticmethod
    def guardar_datos_post_entrenamiento(
        ticker: str,
        ensemble_prediction: Dict,
        training_metrics: Optional[Dict] = None
    ) -> bool:
        """
        Guarda los datos relevantes en la tabla activos después del entrenamiento del modelo.
        
        Se llama después de entrenar con sentiment_flag=false para guardar:
        - precio: Precio actual descargado de Yahoo Finance
        - senal_ia: Señal del modelo (ALCISTA/BAJISTA/LATERAL)
        - confianza_bygru: Confianza del ensemble (proporción de modelos que acuerdan)
        - grafico_prediccion: JSON con métricas adicionales (cajon desastre)
        
        Args:
            ticker: Símbolo del ticker (ej: AAPL, BTC-USD)
            ensemble_prediction: Dict retornado por predict_ensemble() con:
                - trend: ALCISTA/BAJISTA/LATERAL
                - confidence: confianza 0-1
                - current_price: precio actual
                - predicted_price: precio predicho
                - price_upper/price_lower: bandas de incertidumbre
                - predicted_return: retorno logarítmico predicho
                - meta_trend: tendencia del meta-ensemble
                - meta_score: score del meta-ensemble
                - xgboost_direction/probability: resultados XGBoost
            training_metrics: Dict opcional con métricas del entrenamiento:
                - avg_val_loss: pérdida de validación media
                - avg_directional_accuracy: accuracy direccional media
                - avg_mae, avg_rmse: errores del model
                - dynamic_threshold: threshold dinámico
                - xgb_directional_accuracy: accuracy XGBoost
        
        Returns:
            bool: True si la actualización fue exitosa
        """
        try:
            # Extraer datos del ensemble_prediction
            precio_actual = float(ensemble_prediction.get("current_price", 0))
            senal_ia = ensemble_prediction.get("trend", "LATERAL")
            confianza = float(ensemble_prediction.get("confidence", 0))
            
            # Validar señal
            if senal_ia not in ["ALCISTA", "BAJISTA", "LATERAL"]:
                print(f"⚠️ Señal inválida: {senal_ia}, usando LATERAL")
                senal_ia = "LATERAL"
            
            # Construir grafico_prediccion como "cajon desastre" con todas las métricas
            grafico_prediccion = {
                "predicted_price": float(ensemble_prediction.get("predicted_price", 0)),
                "price_upper": float(ensemble_prediction.get("price_upper", 0)),
                "price_lower": float(ensemble_prediction.get("price_lower", 0)),
                "predicted_return": float(ensemble_prediction.get("predicted_return", 0)),
                "predicted_return_pct": float(ensemble_prediction.get("predicted_return_pct", 0)),
                "meta_trend": ensemble_prediction.get("meta_trend", "LATERAL"),
                "meta_score": float(ensemble_prediction.get("meta_score", 0)),
                "xgboost_direction": ensemble_prediction.get("xgboost_direction", "NEUTRAL"),
                "xgboost_probability": float(ensemble_prediction.get("xgboost_probability", 0)),
                "n_individual_models": len(ensemble_prediction.get("individual_predictions", [])),
            }
            
            # Agregar métricas de entrenamiento si están disponibles
            if training_metrics:
                grafico_prediccion["training_metrics"] = {
                    "avg_val_loss": float(training_metrics.get("avg_val_loss", 0)),
                    "avg_directional_accuracy": float(training_metrics.get("avg_directional_accuracy", 0)),
                    "avg_mae": float(training_metrics.get("avg_mae", 0)),
                    "avg_rmse": float(training_metrics.get("avg_rmse", 0)),
                    "dynamic_threshold": float(training_metrics.get("dynamic_threshold", 0)),
                    "xgb_directional_accuracy": training_metrics.get("xgb_directional_accuracy"),
                }
            
            # Preparar datos para actualizar
            update_data = {
                "precio": precio_actual,
                "senal_ia": senal_ia,
                "confianza_bygru": confianza,
                "grafico_prediccion": grafico_prediccion
            }
            
            # Actualizar en la BD
            success = activo_dao.actualizar(ticker, update_data)
            
            if success:
                print(f"✅ {ticker} actualizado post-entrenamiento:")
                print(f"   - Precio: {precio_actual}")
                print(f"   - Señal: {senal_ia}")
                print(f"   - Confianza: {confianza:.4f}")
            else:
                print(f"⚠️ No se pudo actualizar {ticker} en la BD")
            
            return success
        
        except Exception as e:
            print(f"❌ Error guardando datos post-entrenamiento para {ticker}: {e}")
            return False


# Instancia singleton
activo_update_service = ActivoUpdateService()