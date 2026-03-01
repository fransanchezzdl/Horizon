from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ==========================================
# PORTFOLIO DTOs
# ==========================================

class StockInPortfolioRequest(BaseModel):
    """Request para agregar/actualizar una acción al portfolio"""
    ticker: str = Field(..., description="Símbolo de la acción (ej: AAPL, GOOGL)")
    shares: float = Field(..., gt=0, description="Cantidad de acciones")
    buy_price: float = Field(..., gt=0, description="Precio de compra por acción")
    buy_date: str = Field(..., description="Fecha de compra (YYYY-MM-DD)")


class StockInPortfolioResponse(BaseModel):
    """Response de una acción en el portfolio"""
    id: str
    ticker: str
    shares: float
    buy_price: float
    buy_date: str
    current_price: Optional[float] = None  # Obtenido en tiempo real
    current_value: Optional[float] = None  # shares * current_price
    gain_loss_percentage: Optional[float] = None  # (current - buy) / buy * 100


class PortfolioCreateRequest(BaseModel):
    """Request para crear un nuevo portfolio"""
    nombre: str = Field(..., min_length=3, max_length=255)
    descripcion: Optional[str] = Field(None, max_length=500)
    aversion_riesgo: float = Field(..., ge=0.0, le=1.0, 
                                   description="0=Agresivo, 1=Conservador")
    capital_inicial: float = Field(..., gt=0, description="Capital invertido")


class PortfolioUpdateRequest(BaseModel):
    """Request para actualizar un portfolio existente"""
    nombre: Optional[str] = Field(None, min_length=3, max_length=255)
    descripcion: Optional[str] = Field(None, max_length=500)
    aversion_riesgo: Optional[float] = Field(None, ge=0.0, le=1.0)
    capital_inicial: Optional[float] = Field(None, gt=0)


class PortfolioResponse(BaseModel):
    """Response completo de un portfolio"""
    id: str
    usuario_id: str
    nombre: str
    descripcion: Optional[str]
    aversion_riesgo: float
    capital_inicial: float
    acciones: list[StockInPortfolioResponse] = []
    valor_total: Optional[float] = None  # Suma de current_value
    rendimiento_actual: Optional[float] = None  # (valor_total - capital_inicial) / capital_inicial * 100
    created_at: datetime
    updated_at: datetime


class PortfolioListResponse(BaseModel):
    """Response simplificado para listar portfolios"""
    id: str
    nombre: str
    aversion_riesgo: float
    capital_inicial: float
    valor_total: Optional[float] = None
    rendimiento_actual: Optional[float] = None


# ==========================================
# RECOMMENDACIÓN DTOs
# ==========================================

class PortfolioRecommendationRequest(BaseModel):
    """Request para obtener recomendación de portafolio"""
    portfolio_id: str = Field(..., description="ID del portfolio")
    tickers: list[str] = Field(..., min_items=1, description="Tickers a considerar")
    horizonte_dias: int = Field(default=30, ge=1, le=365, 
                                description="Horizonte de predicción en días")


class AllocationRecommendation(BaseModel):
    """Una recomendación de asignación individual"""
    ticker: str
    porcentaje: float  # 0-100
    retorno_esperado: float  # %
    riesgo_estimado: float  # volatilidad %
    confianza_ia: float  # 0-1


class PortfolioRecommendationResponse(BaseModel):
    """Response con recomendación de portafolio optimizado"""
    escenario: str  # "max_sharpe" o "min_riesgo"
    asignacion: list[AllocationRecommendation]
    retorno_esperado_anual: float  # %
    riesgo_esperado_anual: float  # volatilidad %
    ratio_sharpe: float
    recomendacion_texto: str  # Descripción amigable
    fecha_generacion: datetime


# ==========================================
# ANÁLISIS DE PORTFOLIO
# ==========================================

class PortfolioAnalysisResponse(BaseModel):
    """Análisis detallado del portfolio actual"""
    portfolio_id: str
    valor_actual: float
    variacion_absoluta: float  # valor_actual - capital_inicial
    variacion_porcentaje: float  # %
    acciones: list[StockInPortfolioResponse]
    distribucion: dict  # {ticker: porcentaje}
    alertas: list[str]  # Advertencias automáticas
    recomendacion_automatica: Optional[PortfolioRecommendationResponse] = None
