"""
Servicio de portfolios: Gestiona portfolios de usuarios.

Responsabilidades:
1. CRUD de portfolios
2. CRUD de acciones en portfolios
3. Análisis de portfolios (rendimiento, distribución)
4. Obtener recomendaciones de asignación basadas en IA
5. Calcular métricas de riesgo-retorno
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
import numpy as np

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
    """Servicio para gestionar portfolios de usuarios."""
    
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
        usuario_id: str,
        portfolio_data: PortfolioCreateRequest
    ) -> Optional[str]:
        """
        Crea un nuevo portfolio.
        
        Args:
            usuario_id: ID del usuario propietario
            portfolio_data: Datos del portfolio
        
        Returns:
            str: ID del portfolio creado o None
        """
        try:
            if not self.portfolio_dao:
                logger.error("❌ DAO no disponible")
                return None
            
            portfolio_dict = {
                'usuario_id': usuario_id,
                'nombre': portfolio_data.nombre,
                'descripcion': portfolio_data.descripcion,
                'aversion_riesgo': portfolio_data.aversion_riesgo,
                'capital_inicial': portfolio_data.capital_inicial,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            portfolio_id = self.portfolio_dao.crear(portfolio_dict)
            logger.info(f"✅ Portfolio {portfolio_id} creado para usuario {usuario_id}")
            return portfolio_id
        
        except Exception as e:
            logger.error(f"❌ Error creando portfolio: {e}")
            return None
    
    def get_portfolio(self, portfolio_id: str) -> Optional[PortfolioResponse]:
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
            
            # Enriquecer con precios actuales
            valor_total = 0
            stocks_enriquecidas = []
            
            for stock in stocks:
                current_price = self.finance_service.get_current_price(stock['ticker'])
                if current_price:
                    current_value = stock['shares'] * current_price
                    gain_loss = (current_price - stock['buy_price']) / stock['buy_price'] * 100
                else:
                    current_value = 0
                    gain_loss = 0
                
                valor_total += current_value
                stocks_enriquecidas.append({
                    **stock,
                    'current_price': current_price,
                    'current_value': current_value,
                    'gain_loss_percentage': gain_loss
                })
            
            # Calcular rendimiento
            capital_inicial = portfolio_data.get('capital_inicial', 1)
            rendimiento = ((valor_total - capital_inicial) / capital_inicial * 100) if capital_inicial > 0 else 0
            
            return PortfolioResponse(
                id=portfolio_id,
                usuario_id=portfolio_data['usuario_id'],
                nombre=portfolio_data['nombre'],
                descripcion=portfolio_data.get('descripcion'),
                aversion_riesgo=portfolio_data['aversion_riesgo'],
                capital_inicial=capital_inicial,
                acciones=stocks_enriquecidas,
                valor_total=valor_total,
                rendimiento_actual=rendimiento,
                created_at=portfolio_data['created_at'],
                updated_at=portfolio_data['updated_at']
            )
        
        except Exception as e:
            logger.error(f"❌ Error obteniendo portfolio: {e}")
            return None
    
    def add_stock_to_portfolio(
        self,
        portfolio_id: str,
        ticker: str,
        shares: float,
        buy_price: float,
        buy_date: str
    ) -> bool:
        """
        Añade una acción al portfolio.
        
        Args:
            portfolio_id: ID del portfolio
            ticker: Símbolo
            shares: Cantidad de acciones
            buy_price: Precio de compra por acción
            buy_date: Fecha de compra (YYYY-MM-DD)
        
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
                'portfolio_id': portfolio_id,
                'ticker': ticker.upper(),
                'shares': shares,
                'buy_price': buy_price,
                'buy_date': buy_date,
                'created_at': datetime.now().isoformat()
            }
            
            self.portfolio_dao.crear_stock(stock_data)
            logger.info(f"✅ Acción {ticker} añadida al portfolio {portfolio_id}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error añadiendo acción: {e}")
            return False
    
    def get_portfolio_analysis(self, portfolio_id: str) -> Optional[PortfolioAnalysisResponse]:
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
            
            # Calcular distribución
            distribucion = {}
            valor_total = portfolio.valor_total or 1
            
            for stock in portfolio.acciones:
                porcentaje = (stock['current_value'] / valor_total * 100) if valor_total > 0 else 0
                distribucion[stock['ticker']] = porcentaje
            
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
                valor_actual=portfolio.valor_total or 0,
                variacion_absoluta=(portfolio.valor_total or 0) - portfolio.capital_inicial,
                variacion_porcentaje=portfolio.rendimiento_actual or 0,
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
        portfolio_id: str,
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
            
            # Obtener aversion al riesgo del portfolio
            portfolio_data = self.portfolio_dao.obtener_por_id(portfolio_id)
            if not portfolio_data:
                return None
            
            aversion_riesgo = portfolio_data.get('aversion_riesgo', 0.5)
            
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
        
        # Alerta 1: Concentración excesiva
        if portfolio.acciones:
            max_weight = max(
                [(s.get('current_value', 0) / (portfolio.valor_total or 1)) * 100 
                 for s in portfolio.acciones],
                default=0
            )
            
            if max_weight > 40:
                alertas.append(f"⚠️ Concentración excesiva: {max_weight:.1f}% en una posición")
        
        # Alerta 2: Portfolio perdiendo dinero
        if portfolio.rendimiento_actual and portfolio.rendimiento_actual < -10:
            alertas.append(f"⚠️ Portfolio en pérdidas: {portfolio.rendimiento_actual:.2f}%")
        
        # Alerta 3: Aversión al riesgo no alineada
        if portfolio.aversion_riesgo > 0.7:  # Conservador
            acciones_volatiles = [s for s in portfolio.acciones 
                                 if s.get('gain_loss_percentage', 0) > 20]
            if acciones_volatiles:
                alertas.append(
                    f"⚠️ Perfil conservador pero teniendo acciones volátiles: "
                    f"{', '.join([s['ticker'] for s in acciones_volatiles])}"
                )
        
        if not alertas:
            alertas.append("✅ Portfolio en buen estado")
        
        return alertas


def get_portfolio_service(portfolio_dao=None, prediction_service: PredictionService = None) -> PortfolioService:
    """Helper para obtener instancia del servicio."""
    return PortfolioService(portfolio_dao, prediction_service)
