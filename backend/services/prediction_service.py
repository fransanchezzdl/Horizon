"""
Servicio de predicciones: Orquesta el modelo de IA con la BD.

Responsabilidades:
1. Obtener predicciones del modelo
2. Guardar predicciones en BD
3. Calcular confianza y métricas
4. Consultar históricos de predicciones
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from ..models import get_prediction, calculate_blended_return
from ..services.finance_service import FinanceService
from ..dtos.prediction_dto import (
    PredictionResponse,
    PredictionDetailDay,
    BlendedReturnResponse,
)

logger = logging.getLogger(__name__)


class PredictionService:
    """Servicio de predicciones basado en IA."""
    
    def __init__(self, db_client=None, prediction_dao=None):
        """
        Inicializa el servicio.
        
        Args:
            db_client: Cliente de Supabase (opcional)
            prediction_dao: DAO para guardar predicciones (opcional)
        """
        self.db = db_client
        self.prediction_dao = prediction_dao
        self.finance_service = FinanceService()
    
    def get_prediction(
        self,
        ticker: str,
        dias_adelante: int = 1
    ) -> Optional[Dict]:
        """
        Obtiene predicción para un ticker.
        
        Args:
            ticker: Símbolo
            dias_adelante: Días a predecir adelante
        
        Returns:
            Dict con predicción o None si error
        """
        try:
            logger.info(f"🔮 Obteniendo predicción para {ticker} ({dias_adelante} días)")
            
            result = get_prediction(
                ticker=ticker,
                dias_adelante=dias_adelante
            )
            
            if 'error' in result:
                logger.error(f"❌ Error en predicción: {result['error']}")
                return None
            
            return result
        
        except Exception as e:
            logger.error(f"❌ Error en get_prediction: {e}")
            return None
    
    def get_prediction_with_confidence(
        self,
        ticker: str,
        dias_adelante: int = 1
    ) -> Optional[PredictionResponse]:
        """
        Obtiene predicción formateada con DTO.
        
        Args:
            ticker: Símbolo
            dias_adelante: Días a predecir
        
        Returns:
            PredictionResponse o None
        """
        try:
            # Obtener predicción bruta
            pred_data = self.get_prediction(ticker, dias_adelante)
            if not pred_data:
                return None
            
            # Obtener precio actual
            current_price = self.finance_service.get_current_price(ticker) or pred_data['precio_actual']
            
            # Construir respuesta con DTO
            predicciones = [
                PredictionDetailDay(
                    fecha=p['fecha'],
                    precio_predicho=p['precio_predicho'],
                    cambio_esperado=p['cambio_esperado'],
                    confianza=p['confianza']
                )
                for p in pred_data['predicciones']
            ]
            
            response = PredictionResponse(
                ticker=ticker,
                precio_actual=current_price,
                fecha_prediccion=datetime.now(),
                predicciones=predicciones,
                precio_predicho_final=pred_data['precio_predicho_final'],
                cambio_esperado_total=pred_data['cambio_esperado_total'],
                confianza_promedio=pred_data['confianza_promedio'],
                modelo_version=pred_data['modelo_version'],
                indicadores_usados=pred_data['indicadores_usados']
            )
            
            # Guardar en BD si DAO disponible
            if self.prediction_dao:
                self._save_prediction(response)
            
            logger.info(f"✅ Predicción obtenida para {ticker}")
            return response
        
        except Exception as e:
            logger.error(f"❌ Error en get_prediction_with_confidence: {e}")
            return None
    
    def get_blended_return(
        self,
        ticker: str,
        aversion_riesgo: float,
        dias_adelante: int = 365
    ) -> Optional[BlendedReturnResponse]:
        """
        Calcula retorno blended (IA + Historia).
        
        Args:
            ticker: Símbolo
            aversion_riesgo: 0=Agresivo, 1=Conservador
            dias_adelante: Horizonte de proyección
        
        Returns:
            BlendedReturnResponse o None
        """
        try:
            logger.info(f"📊 Calculando retorno blended para {ticker}...")
            
            # 1. Obtener predicción IA (1 día)
            pred = self.get_prediction(ticker, dias_adelante=1)
            if not pred or 'error' in pred:
                logger.warning(f"⚠️ No se pudo obtener predicción IA para {ticker}")
                ai_move = 0.0
            else:
                ai_move = pred['predicciones'][0]['cambio_esperado'] / 100
            
            # 2. Obtener histórico
            returns_data = self.finance_service.calculate_returns(ticker)
            if not returns_data:
                logger.warning(f"⚠️ No se pudo obtener histórico para {ticker}")
                historical_return = 0.0
            else:
                historical_return = returns_data['return_annual']
            
            # 3. Calcular blended
            blended = calculate_blended_return(
                ai_short_term_move=ai_move,
                historical_annual_return=historical_return,
                aversion_riesgo=aversion_riesgo,
                projection_days=dias_adelante
            )
            
            # 4. Pesos utilizados
            peso_ia = 0.2 + (aversion_riesgo * 0.2)
            peso_historico = 1.0 - peso_ia
            
            # Formatear respuesta
            response = BlendedReturnResponse(
                ticker=ticker,
                retorno_historico=historical_return * 100,
                retorno_ia=ai_move * 100,
                retorno_blended=blended * 100,
                peso_historico=peso_historico * 100,
                peso_ia=peso_ia * 100,
                confianza=pred.get('confianza_promedio', 0.5) if pred else 0.5,
                explicacion=(
                    f"Para {ticker}: {peso_historico*100:.0f}% basado en rentabilidad histórica "
                    f"({historical_return*100:.2f}% anual) + {peso_ia*100:.0f}% según predicción IA "
                    f"(cambio estimado {ai_move*100:.2f}% mañana). "
                    f"Resultado blended: {blended*100:.2f}% anual."
                )
            )
            
            logger.info(f"✅ Retorno blended calculado: {blended*100:.2f}%")
            return response
        
        except Exception as e:
            logger.error(f"❌ Error en get_blended_return: {e}")
            return None
    
    def get_multiple_predictions(
        self,
        tickers: List[str],
        dias_adelante: int = 1
    ) -> Dict[str, Optional[PredictionResponse]]:
        """
        Obtiene predicciones para múltiples tickers.
        
        Args:
            tickers: Lista de símbolos
            dias_adelante: Días a predecir
        
        Returns:
            Dict con {ticker: PredictionResponse}
        """
        predictions = {}
        for ticker in tickers:
            predictions[ticker] = self.get_prediction_with_confidence(ticker, dias_adelante)
        return predictions
    
    def _save_prediction(self, prediction_response: PredictionResponse) -> bool:
        """
        Guarda una predicción en la BD.
        
        Args:
            prediction_response: Respuesta de predicción
        
        Returns:
            bool: True si guardado exitosamente
        """
        try:
            if not self.prediction_dao:
                logger.warning("⚠️ No hay DAO disponible para guardar predicción")
                return False
            
            # Crear registros por cada predicción
            for pred_detail in prediction_response.predicciones:
                record = {
                    'ticker': prediction_response.ticker,
                    'predicted_price': pred_detail.precio_predicho,
                    'confidence': pred_detail.confianza,
                    'prediction_date': datetime.now().isoformat(),
                    'forecast_for_date': pred_detail.fecha,
                    'model_version': prediction_response.modelo_version
                }
                
                self.prediction_dao.crear(record)
            
            logger.info(f"✅ Predicción guardada en BD para {prediction_response.ticker}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error guardando predicción: {e}")
            return False
    
    def get_prediction_accuracy(
        self,
        ticker: str,
        days_back: int = 30
    ) -> Optional[Dict]:
        """
        Calcula acuracidad histórica del modelo.
        
        Args:
            ticker: Símbolo
            days_back: Días atrás a analizar
        
        Returns:
            Dict con métricas de acuracidad
        """
        try:
            if not self.prediction_dao:
                logger.warning("⚠️ No hay DAO para obtener histórico")
                return None
            
            # Obtener predicciones históricas
            predictions = self.prediction_dao.obtener_por_ticker(
                ticker=ticker,
                dias_atras=days_back
            )
            
            if not predictions or len(predictions) < 2:
                logger.warning(f"⚠️ Pocas predicciones históricas para {ticker}")
                return None
            
            # Calcular precios reales
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            real_prices = self.finance_service.get_historical_prices(
                ticker,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )
            
            if real_prices is None:
                return None
            
            # Calcular errores
            errors = []
            for pred in predictions:
                forecast_date = pred['forecast_for_date']
                
                try:
                    real_price = real_prices.loc[forecast_date, 'Close']
                    predicted_price = pred['predicted_price']
                    
                    error = abs(real_price - predicted_price) / predicted_price
                    errors.append(error)
                
                except KeyError:
                    continue  # Fecha no disponible
            
            if not errors:
                logger.warning(f"⚠️ No se pudieron calcular errores para {ticker}")
                return None
            
            mae = sum(errors) / len(errors)
            rmse = (sum(e**2 for e in errors) / len(errors)) ** 0.5
            mape = mae * 100
            
            return {
                'ticker': ticker,
                'predicciones_analizadas': len(errors),
                'mae': mae,
                'rmse': rmse,
                'mape': mape,
                'accuracy': max(0, 1 - mape/100)
            }
        
        except Exception as e:
            logger.error(f"❌ Error calculando acuracidad: {e}")
            return None


def get_prediction_service(db_client=None, prediction_dao=None) -> PredictionService:
    """Helper para obtener instancia del servicio."""
    return PredictionService(db_client, prediction_dao)
