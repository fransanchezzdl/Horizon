"""Servicio de portfolios alineado con tablas portfolios y portfolio_activo."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from ..models import optimize_portfolio
from ..services.finance_service import FinanceService
from ..services.prediction_service import PredictionService
from ..dtos.portfolio_dto import (
    PortfolioCreateRequest,
    PortfolioResponse,
    PortfolioRecommendationResponse,
    AllocationRecommendation,
    PortfolioAnalysisResponse,
)

logger = logging.getLogger(__name__)


class PortfolioService:
    """Servicio para gestionar portfolios y posiciones de tickers."""
    
    def __init__(self, portfolio_dao=None, prediction_service: PredictionService = None):
        """
        Inicializa el servicio.
        
        Args:
            portfolio_dao: DAO para acceder a BD
            prediction_service: Servicio de predicciones
        """
        self.portfolio_dao = portfolio_dao
        self.prediction_service = prediction_service or PredictionService()
        self.finance_service = FinanceService()
    
    def create_portfolio(
        self,
        id_usuario: str,
        portfolio_data: PortfolioCreateRequest
    ) -> Optional[int]:
        """
        Crea un nuevo portfolio.
        
        Args:
            id_usuario: ID del usuario propietario
            portfolio_data: Datos del portfolio
        
        Returns:
            int: ID del portfolio creado o None
        """
        try:
            if not self.portfolio_dao:
                logger.error("❌ DAO no disponible")
                return None
            
            portfolio_dict = {
                'id_usuario': id_usuario,
                'nombre_portfolio': portfolio_data.nombre_portfolio,
                'descripcion': portfolio_data.descripcion,
                'riesgo': portfolio_data.riesgo,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            portfolio_id = self.portfolio_dao.crear(portfolio_dict)
            logger.info(f"✅ Portfolio {portfolio_id} creado para usuario {id_usuario}")
            return portfolio_id
        
        except Exception as e:
            logger.error(f"❌ Error creando portfolio: {e}")
            return None
    
    def get_portfolio(self, portfolio_id: int) -> Optional[PortfolioResponse]:
        """
        Obtiene un portfolio completo con análisis.
        
        Args:
            portfolio_id: ID del portfolio
        
        Returns:
            PortfolioResponse o None
        """
        try:
            if not self.portfolio_dao:
                logger.error("❌ DAO no disponible")
                return None
            
            portfolio_data = self.portfolio_dao.obtener_por_id(portfolio_id)
            if not portfolio_data:
                logger.warning(f"⚠️ Portfolio {portfolio_id} no encontrado")
                return None
            
            # Obtener acciones del portfolio
            stocks = self.portfolio_dao.obtener_stocks(portfolio_id)
            
            return PortfolioResponse(
                id_portfolio=portfolio_data['id_portfolio'],
                id_usuario=portfolio_data['id_usuario'],
                nombre_portfolio=portfolio_data['nombre_portfolio'],
                descripcion=portfolio_data.get('descripcion'),
                riesgo=portfolio_data['riesgo'],
                acciones=stocks,
                created_at=portfolio_data['created_at'],
                updated_at=portfolio_data['updated_at']
            )
        
        except Exception as e:
            logger.error(f"❌ Error obteniendo portfolio: {e}")
            return None
    
    def add_stock_to_portfolio(
        self,
        portfolio_id: int,
        ticker: str,
    ) -> bool:
        """
        Añade una acción al portfolio.
        
        Args:
            portfolio_id: ID del portfolio
            ticker: Símbolo
            ticker: Símbolo
        
        Returns:
            bool: True si exitoso
        """
        try:
            if not self.portfolio_dao:
                logger.error("❌ DAO no disponible")
                return False
            
            # Validar ticker
            if not self.finance_service.validate_ticker(ticker):
                logger.warning(f"⚠️ Ticker {ticker} inválido")
                return False
            
            stock_data = {
                'id_portfolio': portfolio_id,
                'ticker': ticker.upper(),
            }
            
            self.portfolio_dao.crear_stock(stock_data)
            logger.info(f"✅ Acción {ticker} añadida al portfolio {portfolio_id}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error añadiendo acción: {e}")
            return False
    
    def get_portfolio_analysis(self, portfolio_id: int) -> Optional[PortfolioAnalysisResponse]:
        """
        Genera análisis detallado del portfolio.
        
        Args:
            portfolio_id: ID del portfolio
        
        Returns:
            PortfolioAnalysisResponse o None
        """
        try:
            # Obtener portfolio
            portfolio = self.get_portfolio(portfolio_id)
            if not portfolio:
                return None
            
            # Distribución por número de posiciones por ticker
            distribucion: Dict[str, int] = {}
            for stock in portfolio.acciones:
                ticker = stock['ticker']
                distribucion[ticker] = distribucion.get(ticker, 0) + 1
            
            # Generar alertas
            alertas = self._generar_alertas(portfolio)
            
            # Obtener recomendación automática
            tickers = [s['ticker'] for s in portfolio.acciones]
            recomendacion = None
            
            if tickers:
                recomendacion = self.get_portfolio_recommendation(
                    portfolio_id=portfolio_id,
                    tickers=tickers,
                    horizonte_dias=30
                )
            
            return PortfolioAnalysisResponse(
                portfolio_id=portfolio_id,
                valor_actual=0,
                variacion_absoluta=0,
                variacion_porcentaje=0,
                acciones=portfolio.acciones,
                distribucion=distribucion,
                alertas=alertas,
                recomendacion_automatica=recomendacion
            )
        
        except Exception as e:
            logger.error(f"❌ Error en análisis: {e}")
            return None
    
    def get_portfolio_recommendation(
        self,
        portfolio_id: int,
        tickers: List[str],
        horizonte_dias: int = 30
    ) -> Optional[PortfolioRecommendationResponse]:
        """
        Obtiene recomendación de asignación para los tickers.
        
        Args:
            portfolio_id: ID del portfolio (para obtener aversion_riesgo)
            tickers: Símbolos a considerar
            horizonte_dias: Días de horizonte
        
        Returns:
            PortfolioRecommendationResponse o None
        """
        try:
            if not self.portfolio_dao or not self.prediction_service:
                logger.error("❌ Servicios no disponibles")
                return None
            
            # Obtener riesgo del portfolio
            portfolio_data = self.portfolio_dao.obtener_por_id(portfolio_id)
            if not portfolio_data:
                return None
            
            aversion_riesgo = portfolio_data.get('riesgo', 0.5)
            
            # Obtener predicciones IA para cada ticker
            logger.info(f"🔮 Obteniendo predicciones para {len(tickers)} tickers...")
            ai_predictions = {}
            
            for ticker in tickers:
                pred = self.prediction_service.get_prediction(ticker, dias_adelante=1)
                if pred and 'predicciones' in pred:
                    # Cambio predicho (convertir % a decimal)
                    ai_predictions[ticker] = pred['predicciones'][0]['cambio_esperado'] / 100
                else:
                    ai_predictions[ticker] = 0.0
            
            # Optimizar portfolio usando Markowitz
            logger.info("⚙️  Ejecutando optimizador Markowitz...")
            optimization_result = optimize_portfolio(
                tickers=tickers,
                ai_predictions=ai_predictions,
                aversion_riesgo=aversion_riesgo
            )
            
            # Determinar escenario recomendado
            recomendacion_escenario = optimization_result['recomendacion_escenario']
            escenario_data = optimization_result[f'escenario_{recomendacion_escenario}']
            
            # Construir asignaciones
            asignaciones = [
                AllocationRecommendation(
                    ticker=ticker,
                    porcentaje=peso * 100,
                    retorno_esperado=optimization_result['retornos_esperados'].get(ticker, 0),
                    riesgo_estimado=0.0,  # Simplificación: calcular volatilidad individual después
                    confianza_ia=0.85
                )
                for ticker, peso in escenario_data['pesos'].items()
            ]
            
            # Construir respuesta
            response = PortfolioRecommendationResponse(
                escenario=recomendacion_escenario,
                asignacion=asignaciones,
                retorno_esperado_anual=escenario_data['retorno_esperado'] * 100,
                riesgo_esperado_anual=escenario_data['volatilidad'] * 100,
                ratio_sharpe=escenario_data['sharpe_ratio'],
                recomendacion_texto=optimization_result['recomendacion_texto'],
                fecha_generacion=datetime.now()
            )
            
            logger.info(f"✅ Recomendación generada: Sharpe={response.ratio_sharpe:.2f}")
            return response
        
        except Exception as e:
            logger.error(f"❌ Error en recomendación: {e}")
            return None
    
    def _generar_alertas(self, portfolio: PortfolioResponse) -> List[str]:
        """
        Genera alertas automáticas basadas en el portfolio.
        
        Args:
            portfolio: Datos del portfolio
        
        Returns:
            Lista de alertas
        """
        alertas = []
        
        if not portfolio.acciones:
            alertas.append("⚠️ Portfolio sin activos en portfolio_activo")
        elif len(portfolio.acciones) == 1:
            alertas.append("⚠️ Portfolio con una sola posición")

        if portfolio.riesgo > 0.8 and len(portfolio.acciones) < 3:
            alertas.append("⚠️ Perfil conservador con baja diversificación")
        
        if not alertas:
            alertas.append("✅ Portfolio en buen estado")
        
        return alertas


def get_portfolio_service(portfolio_dao=None, prediction_service: PredictionService = None) -> PortfolioService:
    """Helper para obtener instancia del servicio."""
    return PortfolioService(portfolio_dao, prediction_service)
