"""Servicio de portfolios alineado con tablas portfolios y portfolio_activo."""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import HTTPException

from ..models import optimize_portfolio
from ..services.finance_service import FinanceService
from ..services.prediction_service import PredictionService
from ..daos.portfolio_dao import PortfolioDAO
from ..dtos.portfolio_dto import (
    PortfolioCreateRequest,
    PortfolioUpdateRequest,
    PortfolioResponse,
    PortfolioListResponse,
    StockInPortfolioRequest,
    StockInPortfolioResponse,
    PortfolioRecommendationResponse,
    AllocationRecommendation,
    PortfolioAnalysisResponse,
)

logger = logging.getLogger(__name__)


class PortfolioService:
    """Servicio para gestionar portfolios y posiciones de tickers."""

    # -----------------------------------------------------------------
    # BLOQUE 1: INFRAESTRUCTURA Y HELPERS COMUNES
    # -----------------------------------------------------------------
    # Este bloque contiene utilidades internas de inicialización, mapeo
    # de respuestas y validaciones de ownership.

    # Inicializa dependencias del servicio y configura implementaciones
    # por defecto para DAO, finanzas y predicción.
    def __init__(self, portfolio_dao=None, prediction_service: PredictionService = None):
        """
        Inicializa el servicio.
        
        Args:
            portfolio_dao: DAO para acceder a BD
            prediction_service: Servicio de predicciones
        """
        self.portfolio_dao = portfolio_dao or PortfolioDAO
        self.prediction_service = prediction_service or PredictionService()
        self.finance_service = FinanceService()

    # Construye un PortfolioResponse uniforme a partir de datos crudos
    # de portfolio y sus posiciones en portfolio_activo.
    def _build_portfolio_response(self, portfolio_data: Dict, acciones: List[Dict]) -> PortfolioResponse:
        return PortfolioResponse(
            **portfolio_data,
            acciones=[StockInPortfolioResponse(**item) for item in acciones]
        )

    # Valida que el portfolio exista y pertenezca al usuario autenticado.
    # Si no cumple, corta flujo con HTTP 404/403.
    def _obtener_portfolio_si_es_propietario(self, user_id: str, id_portfolio: int) -> Dict:
        portfolio = self.portfolio_dao.obtener_por_id(id_portfolio)
        print(f"🔍 DEBUG: Buscando portfolio {id_portfolio}")
        print(f"🔍 DEBUG: Usuario autenticado: {user_id}")
        print(f"🔍 DEBUG: Portfolio encontrado: {portfolio}")
        
        if not portfolio:
            print(f"❌ Portfolio {id_portfolio} no encontrado")
            raise HTTPException(status_code=404, detail="Portfolio no encontrado")
        
        portfolio_user = portfolio.get("id_usuario")
        print(f"🔍 DEBUG: ID usuario del portfolio: {portfolio_user}")
        print(f"🔍 DEBUG: ¿Tipos iguales?: {type(portfolio_user)} vs {type(user_id)}")
        
        if portfolio_user != user_id:
            print(f"❌ Usuario {user_id} no es propietario del portfolio (propietario: {portfolio_user})")
            raise HTTPException(status_code=403, detail="No autorizado para este portfolio")
        
        return portfolio

    # -----------------------------------------------------------------
    # BLOQUE 2: CRUD OPERATIVO (EN USO ACTUAL)
    # -----------------------------------------------------------------
    # Este bloque implementa altas, consultas, edición y borrado de
    # portfolios y posiciones, usado por los endpoints actuales.

    # Lista todos los portfolios del usuario autenticado.
    # Devuelve una vista ligera para listados.
    def listar_portfolios_usuario(self, user_id: str) -> List[PortfolioListResponse]:
        portfolios = self.portfolio_dao.obtener_por_usuario(user_id) or []
        return [PortfolioListResponse(**item) for item in portfolios]

    # Crea un portfolio nuevo para el usuario y devuelve el recurso
    # completo ya persistido en base de datos.
    def crear_portfolio_usuario(self, user_id: str, datos: PortfolioCreateRequest) -> PortfolioResponse:
        print(f"\n📝 Creando portfolio para usuario {user_id}")
        print(f"   Datos: nombre={datos.nombre_portfolio}, desc={datos.descripcion}, riesgo={datos.riesgo}")
        
        payload = {
            "id_usuario": user_id,
            "nombre_portfolio": datos.nombre_portfolio,
            "descripcion": datos.descripcion or "",  # Si es None, enviar string vacío
            "riesgo": datos.riesgo,
        }
        
        print(f"   Payload final: {payload}")

        try:
            portfolio_id = self.portfolio_dao.crear(payload)
            if not portfolio_id:
                print(f"❌ DAO retornó portfolio_id=None")
                raise HTTPException(status_code=500, detail="No se pudo crear el portfolio (DAO retornó None)")

            print(f"✅ Portfolio creado con ID {portfolio_id}")
            return self.obtener_portfolio_usuario(user_id, portfolio_id)
        
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Error creando portfolio: {str(e)}")

    # Obtiene el detalle de un portfolio del usuario, incluyendo
    # sus posiciones de portfolio_activo.
    def obtener_portfolio_usuario(self, user_id: str, id_portfolio: int) -> PortfolioResponse:
        print(f"\n🔍 OBTENER: Buscando portfolio {id_portfolio} para usuario {user_id}")
        
        portfolio = self._obtener_portfolio_si_es_propietario(user_id, id_portfolio)
        print(f"✅ Portfolio autorizado para el usuario")
        
        try:
            acciones = self.portfolio_dao.obtener_stocks(id_portfolio)
            print(f"📊 Stocks obtenidos: {len(acciones)} activos")
            
            response = self._build_portfolio_response(portfolio, acciones)
            print(f"✅ Response construido exitosamente")
            return response
        
        except Exception as e:
            print(f"❌ Error construyendo response: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Error obteniendo portfolio: {str(e)}")

    # Actualiza campos editables del portfolio y devuelve el estado final
    # tras persistir los cambios.
    def actualizar_portfolio_usuario(
        self,
        user_id: str,
        id_portfolio: int,
        datos: PortfolioUpdateRequest,
    ) -> PortfolioResponse:
        self._obtener_portfolio_si_es_propietario(user_id, id_portfolio)

        update_data = datos.model_dump(exclude_none=True)
        if update_data:
            ok = self.portfolio_dao.actualizar(id_portfolio, update_data)
            if not ok:
                raise HTTPException(status_code=500, detail="No se pudo actualizar el portfolio")

        return self.obtener_portfolio_usuario(user_id, id_portfolio)

    # Elimina un portfolio del usuario (y sus posiciones asociadas por
    # cascada en base de datos).
    def eliminar_portfolio_usuario(self, user_id: str, id_portfolio: int) -> Dict[str, str]:
        self._obtener_portfolio_si_es_propietario(user_id, id_portfolio)
        ok = self.portfolio_dao.eliminar(id_portfolio)
        if not ok:
            raise HTTPException(status_code=500, detail="No se pudo eliminar el portfolio")
        return {"detail": "Portfolio eliminado"}

    # Lista las posiciones de portfolio_activo para un portfolio del
    # usuario autenticado.
    def listar_activos_portfolio_usuario(self, user_id: str, id_portfolio: int) -> List[StockInPortfolioResponse]:
        self._obtener_portfolio_si_es_propietario(user_id, id_portfolio)
        acciones = self.portfolio_dao.obtener_stocks(id_portfolio)
        return [StockInPortfolioResponse(**item) for item in acciones]

    # Añade un ticker a portfolio_activo tras validar ownership y validez
    # del ticker contra el proveedor financiero.
    def agregar_activo_portfolio_usuario(
        self,
        user_id: str,
        id_portfolio: int,
        datos: StockInPortfolioRequest,
    ) -> StockInPortfolioResponse:
        self._obtener_portfolio_si_es_propietario(user_id, id_portfolio)

        if not self.finance_service.validate_ticker(datos.ticker.upper()):
            raise HTTPException(status_code=400, detail="Ticker inválido")

        stock_id = self.portfolio_dao.crear_stock({
            "id_portfolio": id_portfolio,
            "ticker": datos.ticker.upper(),
        })
        if not stock_id:
            raise HTTPException(status_code=500, detail="No se pudo añadir el activo al portfolio")

        stock = self.portfolio_dao.obtener_stock(stock_id)
        if not stock:
            raise HTTPException(status_code=500, detail="Activo creado pero no recuperable")
        return StockInPortfolioResponse(**stock)

    # Elimina una posición concreta de portfolio_activo validando que
    # pertenece al portfolio del usuario.
    def eliminar_activo_portfolio_usuario(self, user_id: str, id_portfolio: int, id_posicion: int) -> Dict[str, str]:
        self._obtener_portfolio_si_es_propietario(user_id, id_portfolio)
        posicion = self.portfolio_dao.obtener_stock(id_posicion)
        if not posicion or posicion["id_portfolio"] != id_portfolio:
            raise HTTPException(status_code=404, detail="Posición no encontrada en este portfolio")

        ok = self.portfolio_dao.eliminar_stock(id_posicion)
        if not ok:
            raise HTTPException(status_code=500, detail="No se pudo eliminar la posición")
        return {"detail": "Posición eliminada"}

    # -----------------------------------------------------------------
    # BLOQUE 3: ANÁLISIS Y RECOMENDACIÓN (NO USADO EN MAIN POR AHORA)
    # -----------------------------------------------------------------
    # Este bloque prepara analítica y recomendaciones IA para uso futuro
    # en endpoints o procesos específicos.

    # Carga un portfolio con sus posiciones para procesos analíticos.
    # No aplica ownership porque está pensado para flujo interno.
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
            
            return self._build_portfolio_response(portfolio_data, stocks)
        
        except Exception as e:
            logger.error(f"❌ Error obteniendo portfolio: {e}")
            return None

    # Genera un resumen analítico del portfolio: distribución, alertas y
    # recomendación automática si hay tickers.
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
                ticker = stock.ticker
                distribucion[ticker] = distribucion.get(ticker, 0) + 1
            
            # Generar alertas
            alertas = self._generar_alertas(portfolio)
            
            # Obtener recomendación automática
            tickers = [s.ticker for s in portfolio.acciones]
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

    # Calcula una asignación recomendada usando predicción IA +
    # optimización de portfolio según el perfil de riesgo.
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

    # Crea alertas básicas de estado del portfolio en función de número
    # de posiciones y perfil de riesgo.
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


# Factory helper para crear instancias personalizadas del servicio
# (tests o wiring manual de dependencias).
def get_portfolio_service(portfolio_dao=None, prediction_service: PredictionService = None) -> PortfolioService:
    """Helper para obtener instancia del servicio."""
    return PortfolioService(portfolio_dao, prediction_service)

