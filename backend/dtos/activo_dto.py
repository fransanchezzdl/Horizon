from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ==========================================
# ACTIVOS DTOs
# ==========================================

class ActivoCreateRequest(BaseModel):
    """Request para crear un nuevo activo"""
    ticker: str = Field(..., min_length=1, max_length=10, description="Símbolo del ticker (ej: AAPL, BTC-USD)")
    nombre_completo: str = Field(..., min_length=1, max_length=255, description="Nombre completo del activo")
    estabilidad: Optional[bool] = Field(None, description="Indica si el activo es estable")
    logo_activo: Optional[str] = Field(None, description="URL del logo del activo")
    precio: Optional[float] = Field(None, gt=0, description="Precio actual del activo")


class ActivoUpdateRequest(BaseModel):
    """Request para actualizar un activo existente"""
    nombre_completo: Optional[str] = Field(None, min_length=1, max_length=255)
    estabilidad: Optional[bool] = None
    logo_activo: Optional[str] = None
    precio: Optional[float] = Field(None, gt=0)
    confianza_bygru: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confianza del modelo (0-1)")
    senal_ia: Optional[str] = Field(None, description="Señal de IA: ALCISTA, BAJISTA o LATERAL")
    grafico_prediccion: Optional[dict] = Field(None, description="Datos del gráfico de predicción en JSON")
    noticias: Optional[dict] = Field(None, description="Noticias relacionadas en formato JSON")
    senal_actualizada_en: Optional[datetime] = Field(None, description="Timestamp de la última actualización de señal IA")
    precio_predicho: Optional[float] = Field(None, description="Precio objetivo predicho por el modelo")
    retorno_predicho_pct: Optional[float] = Field(None, description="Retorno esperado en % para el horizonte de predicción")
    live_accuracy_30d: Optional[float] = Field(None, ge=0.0, le=100.0, description="Accuracy real del modelo en los últimos 30 días (%)")
    sector: Optional[str] = Field(None, description="Sector del activo (Tecnología, Consumo Básico, etc.)")
    probabilidades_xgb: Optional[dict] = Field(None, description="Probabilidades XGBoost por clase: {alcista, lateral, bajista}")
    volatilidad_30d: Optional[float] = Field(None, ge=0.0, description="Volatilidad histórica diaria 30 días (%)")


class ActivoResponse(BaseModel):
    """Response completo de un activo con todos sus datos"""
    ticker: str
    nombre_completo: str
    estabilidad: Optional[bool] = None
    logo_activo: Optional[str] = None
    precio: Optional[float] = None
    confianza_bygru: Optional[float] = None
    senal_ia: Optional[str] = None
    grafico_prediccion: Optional[dict] = None
    noticias: Optional[dict] = None
    updated_at: datetime
    senal_actualizada_en: Optional[datetime] = None
    precio_predicho: Optional[float] = None
    retorno_predicho_pct: Optional[float] = None
    live_accuracy_30d: Optional[float] = None
    sector: Optional[str] = None
    probabilidades_xgb: Optional[dict] = None
    volatilidad_30d: Optional[float] = None

    class Config:
        from_attributes = True


class ActivoListResponse(BaseModel):
    """Response simplificado para listar activos"""
    ticker: str
    nombre_completo: str
    precio: Optional[float] = None
    confianza_bygru: Optional[float] = None
    senal_ia: Optional[str] = None
    estabilidad: Optional[bool] = None
    senal_actualizada_en: Optional[datetime] = None
    precio_predicho: Optional[float] = None
    retorno_predicho_pct: Optional[float] = None
    live_accuracy_30d: Optional[float] = None
    sector: Optional[str] = None
    volatilidad_30d: Optional[float] = None

    class Config:
        from_attributes = True
