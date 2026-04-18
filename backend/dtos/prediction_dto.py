from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ==========================================
# PREDICTION DTOs
# ==========================================

class PredictionRequest(BaseModel):
    """Request para obtener predicción de un ticker"""
    ticker: str = Field(..., min_length=1, max_length=10, 
                        description="Símbolo de la acción (ej: AAPL, TSLA)")
    dias_adelante: int = Field(default=1, ge=1, le=365, 
                               description="Cuántos días predecir adelante")


class PredictionDetailDay(BaseModel):
    """Predicción detallada para un día específico"""
    fecha: str  # YYYY-MM-DD
    precio_predicho: float
    cambio_esperado: float  # %
    confianza: float  # 0-1


class PredictionResponse(BaseModel):
    """Response de una predicción"""
    ticker: str
    precio_actual: float
    fecha_prediccion: datetime
    predicciones: list[PredictionDetailDay]
    
    # Resumen
    precio_predicho_final: float  # Precio al final del horizonte
    cambio_esperado_total: float  # % total
    confianza_promedio: float  # Promedio de confianza
    
    # Metadata
    modelo_version: str
    indicadores_usados: list[str]  # [Close, RSI, MACD, EMA]
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "KO",
                "precio_actual": 64.32,
                "fecha_prediccion": "2026-03-01T15:30:00",
                "predicciones": [
                    {"fecha": "2026-03-02", "precio_predicho": 64.85, "cambio_esperado": 0.82, "confianza": 0.92},
                    {"fecha": "2026-03-03", "precio_predicho": 65.10, "cambio_esperado": 1.21, "confianza": 0.89}
                ],
                "precio_predicho_final": 65.10,
                "cambio_esperado_total": 1.21,
                "confianza_promedio": 0.91,
                "modelo_version": "1.0.0",
                "indicadores_usados": ["Close", "RSI", "MACD", "EMA"]
            }
        }


class BlendedReturnRequest(BaseModel):
    """Request para calcular retorno blended (IA + Historia)"""
    ticker: str
    aversion_riesgo: float = Field(..., ge=0.0, le=1.0, 
                                   description="0=Agresivo, 1=Conservador")
    dias_adelante: int = Field(default=365, ge=1, le=365)


class BlendedReturnResponse(BaseModel):
    """Response del retorno blended"""
    ticker: str
    retorno_historico: float  # %
    retorno_ia: float  # %
    retorno_blended: float  # % (final)
    peso_historico: float  # % del peso en la fórmula
    peso_ia: float  # % del peso en la fórmula
    confianza: float  # 0-1
    explicacion: str


class HistoricalPredictionResponse(BaseModel):
    """Response de una predicción guardada en historial"""
    id: str
    ticker: str
    precio_predicho: float
    precio_real: Optional[float] = None  # Se llena después si la fecha ha pasado
    confianza: float
    error_absoluto: Optional[float] = None  # |precio_real - precio_predicho|
    error_porcentaje: Optional[float] = None  # % de error
    prediction_date: datetime
    forecast_for_date: str  # YYYY-MM-DD
    model_version: str
    accuracy: Optional[float] = None  # 0-1, acierto cuando el cambio de dirección fue correcto


class PredictionStatsResponse(BaseModel):
    """Estadísticas de predicciones históricas"""
    ticker: str
    total_predicciones: int
    predicciones_correctas: int  # Cuando predicted_direction == actual_direction
    accuracy_rate: float  # % de acierto
    rmse: float  # Root Mean Squared Error
    mae: float  # Mean Absolute Error
    mape: float  # Mean Absolute Percentage Error %
    confianza_promedio: float
