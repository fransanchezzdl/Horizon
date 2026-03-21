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
import json
import math
from ..daos import activo_dao, historico_dao


class ActivoUpdateService:
    """Servicio para actualizar activos con datos de modelos y predicciones."""
    
    @staticmethod
    def _sanitizar_json_para_supabase(obj) -> dict:
        """
        Convierte dict a JSON seguro para Supabase (sin NaN, Infinity, etc).
        
        Args:
            obj: Objeto a sanitizar
        
        Returns:
            Dict serializable a JSON limpio
        """
        def converter(o):
            if isinstance(o, float):
                # NaN e Infinity no son válidos en JSON
                if math.isnan(o):
                    return None
                elif math.isinf(o):
                    return 999999.99 if o > 0 else -999999.99
                return o
            raise TypeError(f"No serializable: {type(o)}")
        
        try:
            # Serializar y deserializar para asegurar validez
            json_str = json.dumps(obj, default=converter)
            return json.loads(json_str)
        except Exception as e:
            print(f"⚠️ Error sanitizando JSON: {e}. Retornando objeto original.")
            return obj
    
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
            # 1️⃣ Validaciones básicas
            if not ticker or not isinstance(ticker, str):
                print(f"❌ Ticker inválido: {ticker}")
                return False
            
            if not isinstance(ensemble_prediction, dict):
                print(f"❌ ensemble_prediction debe ser un dict, recibido {type(ensemble_prediction)}")
                return False
            
            # 2️⃣ Extraer y validar precio
            precio_actual = ensemble_prediction.get("current_price")
            if precio_actual is None or not isinstance(precio_actual, (int, float)):
                print(f"❌ Precio inválido o faltante: {precio_actual}")
                return False
            precio_actual = float(precio_actual)
            
            if precio_actual <= 0:
                print(f"⚠️ Precio negativo o cero: {precio_actual}, usando |valor|")
                precio_actual = abs(precio_actual)
            
            # 3️⃣ Validar señal
            senal_ia = ensemble_prediction.get("trend", "LATERAL")
            if senal_ia not in ["ALCISTA", "BAJISTA", "LATERAL"]:
                print(f"⚠️ Señal inválida '{senal_ia}', usando LATERAL")
                senal_ia = "LATERAL"
            
            # 4️⃣ Validar confianza
            confianza = ensemble_prediction.get("confidence", 0)
            if not isinstance(confianza, (int, float)):
                print(f"⚠️ Confianza inválida (tipo): {type(confianza)}, usando 0")
                confianza = 0
            else:
                confianza = float(confianza)
                if confianza < 0 or confianza > 1:
                    print(f"⚠️ Confianza fuera de rango [0,1]: {confianza}, clipeando")
                    confianza = max(0, min(1, confianza))
            
            # 5️⃣ Construir y sanitizar grafico_prediccion
            grafico_raw = {
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
            
            if training_metrics and isinstance(training_metrics, dict):
                grafico_raw["training_metrics"] = {
                    "avg_val_loss": float(training_metrics.get("avg_val_loss", 0)),
                    "avg_directional_accuracy": float(training_metrics.get("avg_directional_accuracy", 0)),
                    "avg_mae": float(training_metrics.get("avg_mae", 0)),
                    "avg_rmse": float(training_metrics.get("avg_rmse", 0)),
                    "dynamic_threshold": float(training_metrics.get("dynamic_threshold", 0)),
                    "xgb_directional_accuracy": training_metrics.get("xgb_directional_accuracy"),
                }
            
            # Sanitizar para JSON safety (quitar NaN, Infinity, etc)
            grafico_prediccion = ActivoUpdateService._sanitizar_json_para_supabase(grafico_raw)
            
            # 6️⃣ Preparar datos para actualizar
            update_data = {
                "precio": precio_actual,
                "senal_ia": senal_ia,
                "confianza_bygru": confianza,
                "grafico_prediccion": grafico_prediccion
            }
            
            # 7️⃣ Intentar actualizar
            success = activo_dao.actualizar(ticker, update_data)
            
            if success:
                print(f"\n✅ {ticker} actualizado exitosamente post-entrenamiento:")
                print(f"   • Precio: ${precio_actual:.2f}")
                print(f"   • Señal: {senal_ia}")
                print(f"   • Confianza: {confianza:.2%}")
                print(f"   • Gráfico/Métricas: guardadas ({len(grafico_prediccion)} campos)")
            else:
                print(f"\n❌ No se pudo actualizar {ticker} en la BD")
            
            return success
        
        except Exception as e:
            print(f"\n❌ Excepción en guardar_datos_post_entrenamiento:")
            print(f"   Ticker: {ticker}")
            print(f"   Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False


# Instancia singleton
activo_update_service = ActivoUpdateService()