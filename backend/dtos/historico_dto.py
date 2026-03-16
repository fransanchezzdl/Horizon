from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


# ==========================================
# HISTÓRICO ACTIVOS DTOs
# ==========================================

class HistoricoActivoCreateRequest(BaseModel):
    """Request para crear un registro histórico de un activo"""
    ticker: str = Field(..., min_length=1, max_length=10, description="Símbolo del ticker")
    fecha: date = Field(..., description="Fecha del registro histórico (YYYY-MM-DD)")
    precio_cierre: float = Field(..., gt=0, description="Precio de cierre en esa fecha")
    prediccion_ia: Optional[float] = Field(None, description="Predicción de IA para el precio")


class HistoricoActivoUpdateRequest(BaseModel):
    """Request para actualizar un registro histórico"""
    precio_cierre: Optional[float] = Field(None, gt=0)
    prediccion_ia: Optional[float] = None


class HistoricoActivoResponse(BaseModel):
    """Response de un registro histórico de activo"""
    id_historico: int
    ticker: str
    fecha: date
    precio_cierre: float
    prediccion_ia: Optional[float] = None
    
    class Config:
        from_attributes = True


class HistoricoActivoListResponse(BaseModel):
    """Response simplificado para listar históricos"""
    id_historico: int
    ticker: str
    fecha: date
    precio_cierre: float
    prediccion_ia: Optional[float] = None
    
    class Config:
        from_attributes = True
