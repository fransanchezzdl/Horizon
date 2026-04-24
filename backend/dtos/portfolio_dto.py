from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ==========================================
# PORTFOLIO DTOs
# ==========================================

class StockInPortfolioRequest(BaseModel):
    """Request para agregar un activo al portfolio"""
    ticker: str = Field(..., description="Símbolo de la acción (ej: AAPL, GOOGL)")


class StockInPortfolioResponse(BaseModel):
    """Response de un activo dentro de portfolio_activo"""
    id_posicion: int
    id_portfolio: int
    ticker: str
    created_at: datetime
    updated_at: datetime


class PortfolioCreateRequest(BaseModel):
    """Request para crear un nuevo portfolio"""
    nombre_portfolio: str = Field(..., min_length=3, max_length=255)
    descripcion: Optional[str] = Field(None, max_length=500)
    riesgo: float = Field(..., ge=0.0, le=1.0, description="0=Agresivo, 1=Conservador")


class PortfolioUpdateRequest(BaseModel):
    """Request para actualizar un portfolio existente"""
    nombre_portfolio: Optional[str] = Field(None, min_length=3, max_length=255)
    descripcion: Optional[str] = Field(None, max_length=500)
    riesgo: Optional[float] = Field(None, ge=0.0, le=1.0)


class PortfolioResponse(BaseModel):
    """Response completo de un portfolio"""
    id_portfolio: int
    id_usuario: str
    nombre_portfolio: str
    descripcion: Optional[str]
    riesgo: float
    acciones: list[StockInPortfolioResponse] = []
    created_at: datetime
    updated_at: datetime


class PortfolioListResponse(BaseModel):
    """Response simplificado para listar portfolios"""
    id_portfolio: int
    nombre_portfolio: str
    descripcion: Optional[str] = None
    riesgo: float
    created_at: datetime
    updated_at: datetime


# ==========================================
# RECOMMENDACIÓN DTOs
# ==========================================

class PortfolioRecommendationRequest(BaseModel):
    """Request para obtener recomendación de portafolio"""
    portfolio_id: int = Field(..., description="ID del portfolio")
    tickers: list[str] = Field(..., min_length=1, description="Tickers a considerar")
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

class AlertaPortfolio(BaseModel):
    """Alerta de salud del portfolio"""
    mensaje: str
    nivel: str   # "ok" | "warning" | "danger"
    estado: str  # "ok" | "infra" | "sobre"


class PortfolioAnalysisResponse(BaseModel):
    """Análisis detallado del portfolio actual"""
    portfolio_id: int
    valor_actual: float
    variacion_absoluta: float  # valor_actual - capital_inicial
    variacion_porcentaje: float  # %
    acciones: list[StockInPortfolioResponse]
    distribucion: dict  # {ticker: porcentaje}
    alerta: Optional[AlertaPortfolio] = None
    recomendacion_automatica: Optional[PortfolioRecommendationResponse] = None
