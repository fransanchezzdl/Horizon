"""
DAO (Data Access Object) para predicciones.

Responsabilidades:
- CRUD de registros de predicciones
- Consultas específicas por ticker/fecha
- Cálculos de acuracidad
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from ..database import supabase


class PredictionDAO:
    """Acceso a datos de predicciones."""
    
    TABLE_NAME = "stock_predictions"
    
    @staticmethod
    def crear(prediction_data: Dict) -> bool:
        """
        Crea un nuevo registro de predicción.
        
        Args:
            prediction_data: Dict con datos de predicción
                - ticker: str
                - predicted_price: float
                - confidence: float (0-1)
                - prediction_date: str
                - forecast_for_date: str (YYYY-MM-DD)
                - model_version: str
        
        Returns:
            bool: True si exitoso
        """
        try:
            supabase.table(PredictionDAO.TABLE_NAME).insert(prediction_data).execute()
            return True
        except Exception as e:
            print(f"❌ Error creando predicción: {e}")
            return False
    
    @staticmethod
    def obtener_por_id(prediction_id: str) -> Optional[Dict]:
        """
        Obtiene una predicción por ID.
        
        Args:
            prediction_id: ID de la predicción
        
        Returns:
            Dict con datos o None
        """
        try:
            response = (
                supabase.table(PredictionDAO.TABLE_NAME)
                .select("*")
                .eq("id", prediction_id)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"❌ Error obtener predicción: {e}")
            return None
    
    @staticmethod
    def obtener_por_ticker(
        ticker: str,
        limit: int = 100,
        dias_atras: int = 30
    ) -> Optional[List[Dict]]:
        """
        Obtiene predicciones por ticker.
        
        Args:
            ticker: Símbolo
            limit: Límite de registros
            dias_atras: Predicciones de los últimos N días
        
        Returns:
            Lista de predicciones o None
        """
        try:
            fecha_limite = (datetime.now() - timedelta(days=dias_atras)).isoformat()
            
            response = (
                supabase.table(PredictionDAO.TABLE_NAME)
                .select("*")
                .eq("ticker", ticker)
                .gte("prediction_date", fecha_limite)
                .order("prediction_date", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            print(f"❌ Error obtener predicciones: {e}")
            return None
    
    @staticmethod
    def obtener_por_fecha(forecast_date: str) -> Optional[List[Dict]]:
        """
        Obtiene predicciones para una fecha específica.
        
        Args:
            forecast_date: Fecha (YYYY-MM-DD)
        
        Returns:
            Lista de predicciones
        """
        try:
            response = (
                supabase.table(PredictionDAO.TABLE_NAME)
                .select("*")
                .eq("forecast_for_date", forecast_date)
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            print(f"❌ Error obtener predicciones por fecha: {e}")
            return None
    
    @staticmethod
    def actualizar(prediction_id: str, update_data: Dict) -> bool:
        """
        Actualiza una predicción existente.
        
        Útil para agregar precio real después de que pase la fecha.
        
        Args:
            prediction_id: ID de la predicción
            update_data: Dict con campos a actualizar
                - precio_real (optional)
                - error_absoluto (optional)
                - error_porcentaje (optional)
                - accuracy (optional)
        
        Returns:
            bool: True si exitoso
        """
        try:
            update_data['updated_at'] = datetime.now().isoformat()
            
            supabase.table(PredictionDAO.TABLE_NAME).update(
                update_data
            ).eq("id", prediction_id).execute()
            
            return True
        except Exception as e:
            print(f"❌ Error actualizando predicción: {e}")
            return False
    
    @staticmethod
    def eliminar(prediction_id: str) -> bool:
        """
        Elimina una predicción.
        
        Args:
            prediction_id: ID de la predicción
        
        Returns:
            bool: True si exitoso
        """
        try:
            supabase.table(PredictionDAO.TABLE_NAME).delete().eq(
                "id", prediction_id
            ).execute()
            return True
        except Exception as e:
            print(f"❌ Error eliminando predicción: {e}")
            return False
    
    @staticmethod
    def obtener_estadisticas(ticker: str, dias: int = 90) -> Optional[Dict]:
        """
        Obtiene estadísticas de precisión del modelo.
        
        Args:
            ticker: Símbolo
            dias: Días a analizar
        
        Returns:
            Dict con estadísticas o None
        """
        try:
            fecha_limite = (datetime.now() - timedelta(days=dias)).isoformat()
            
            response = (
                supabase.table(PredictionDAO.TABLE_NAME)
                .select("*")
                .eq("ticker", ticker)
                .gte("prediction_date", fecha_limite)
                .execute()
            )
            
            if not response.data:
                return None
            
            predictions = response.data
            
            # Calcular estadísticas
            total = len(predictions)
            
            # Predicciones con error calculado
            with_error = [p for p in predictions if p.get('error_porcentaje') is not None]
            
            if not with_error:
                return {
                    'ticker': ticker,
                    'total_predicciones': total,
                    'predicciones_evaluadas': 0,
                    'confianza_promedio': sum(p.get('confidence', 0) for p in predictions) / total if total > 0 else 0
                }
            
            errors = [abs(p['error_porcentaje']) for p in with_error]
            mae = sum(errors) / len(errors)
            rmse = (sum(e**2 for e in errors) / len(errors)) ** 0.5
            mape = mae * 100
            
            return {
                'ticker': ticker,
                'total_predicciones': total,
                'predicciones_evaluadas': len(with_error),
                'mae': mae,
                'rmse': rmse,
                'mape': mape,
                'confianza_promedio': sum(p.get('confidence', 0) for p in predictions) / total if total > 0 else 0,
                'accuracy': max(0, 1 - mape/100)
            }
        
        except Exception as e:
            print(f"❌ Error calculando estadísticas: {e}")
            return None


