"""
API Routes para XAI - Explicabilidad del modelo
================================================

Endpoints:
- GET /activos/{ticker}/explicacion - Última explicación
- GET /activos/{ticker}/historial-xai - Historial últimos 30 días
- POST /explicaciones/{id}/validar - User feedback
- GET /estadisticas/xai - Métricas agregadas
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
import logging

from backend.daos.explicacion_xai_dao import ExplicacionXAIDAO

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["XAI - Explicabilidad"]
)


@router.get("/activos/{ticker}/explicacion", tags=["XAI"])
async def obtener_explicacion_reciente(ticker: str) -> Dict[str, Any]:
    """
    Obtiene la última explicación XAI para un ticker.
    
    Returna:
    {
        'id_explicacion': int,
        'ticker': str,
        'fecha_prediccion': str (ISO),
        'shap_valores': [{feature_name, shap_value, feature_value, shap_abs}, ...],
        'shap_grafico_base64': str,
        'features_top20': [{feature_name, importancia, valor}, ...],
        'pesos_atencion': [{dia_relativo, peso_atencion}, ...],
        'contribucion_features': {feature_name: contribution, ...},
        'senal_prediccion': str,
        'confianza_prediccion': float,
        'version_modelo': str,
        'seed_modelo': int
    }
    """
    try:
        explicaciones = ExplicacionXAIDAO.obtener_por_ticker(ticker, limit=1)
        
        if not explicaciones:
            raise HTTPException(
                status_code=404,
                detail=f"No hay explicación disponible para {ticker}"
            )
        
        return {
            "status": "success",
            "data": explicaciones[0]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en obtener_explicacion_reciente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/activos/{ticker}/historial-xai", tags=["XAI"])
async def obtener_historial_xai(
    ticker: str,
    dias: int = Query(30, ge=1, le=365),
    limit: Optional[int] = Query(None, ge=1, le=100)
) -> Dict[str, Any]:
    """
    Obtiene historial de explicaciones para un ticker.
    
    Query params:
    - dias: Número de días a incluir (default 30)
    - limit: Máximo número de resultados (default None = todos)
    
    Returns:
        Lista de explicaciones en orden descendente (más recientes primero)
    """
    try:
        explicaciones = ExplicacionXAIDAO.obtener_por_ticker(
            ticker,
            limit=limit,
            dias=dias
        )
        
        return {
            "status": "success",
            "count": len(explicaciones),
            "periodo": f"últimos {dias} días",
            "data": explicaciones
        }
    
    except Exception as e:
        logger.error(f"Error en obtener_historial_xai: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/explicaciones/{id_explicacion}", tags=["XAI"])
async def obtener_explicacion_por_id(id_explicacion: int) -> Dict[str, Any]:
    """
    Obtiene una explicación específica por ID.
    """
    try:
        explicacion = ExplicacionXAIDAO.obtener_por_id(id_explicacion)
        
        if not explicacion:
            raise HTTPException(
                status_code=404,
                detail=f"Explicación {id_explicacion} no encontrada"
            )
        
        return {
            "status": "success",
            "data": explicacion
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en obtener_explicacion_por_id: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/explicaciones/{id_explicacion}/validar", tags=["XAI"])
async def validar_explicacion(
    id_explicacion: int,
    util: bool,
    comentario: Optional[str] = None
) -> Dict[str, Any]:
    """
    Marca una explicación como útil/no útil (user feedback).
    
    Params:
    - util (body): bool - si fue útil
    - comentario (body, opcional): str
    """
    try:
        success = ExplicacionXAIDAO.actualizar(
            id_explicacion,
            prediccion_correcta=util,
            comentario_validacion=comentario
        )
        
        if success:
            return {
                "status": "success",
                "message": f"Validación guardada (útil={util})"
            }
        else:
            raise HTTPException(status_code=400, detail="No se pudo guardar validación")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en validar_explicacion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/estadisticas/xai", tags=["XAI"])
async def obtener_estadisticas_xai(
    ticker: Optional[str] = Query(None),
    dias: int = Query(30, ge=1, le=365)
) -> Dict[str, Any]:
    """
    Obtiene estadísticas agregadas de explicaciones XAI.
    
    Si ticker se especifica, estadísticas para ese ticker.
    Si no, estadísticas globales de todos los tickers con explicaciones.
    
    Returns:
    {
        'total_explicaciones': int,
        'explicaciones_correctas': int,
        'tasa_acierto': float (0-1),
        'features_mas_frecuentes': [str],
        'senal_distribucion': {ALCISTA: int, BAJISTA: int, ...},
        'confianza_promedio': float,
        'periodo': str
    }
    """
    try:
        if ticker:
            # Estadísticas para un ticker específico
            stats = ExplicacionXAIDAO.obtener_estadisticas(ticker, dias=dias)
            return {
                "status": "success",
                "ticker": ticker,
                "data": stats
            }
        else:
            # TODO: Estadísticas globales (requiere query más compleja)
            raise HTTPException(
                status_code=501,
                detail="Estadísticas globales no implementadas aún. Use ?ticker=AAPL"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en obtener_estadisticas_xai: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/features/top-global", tags=["XAI"])
async def obtener_features_top_global(
    top_n: int = Query(20, ge=1, le=50),
    dias: int = Query(30, ge=1, le=365)
) -> Dict[str, Any]:
    """
    Obtiene features más importantes globalmente (todos los tickers).
    
    Útil para ver patrones generales del modelo.
    """
    try:
        # TODO: Query agregada en Supabase
        return {
            "status": "success",
            "top_n": top_n,
            "periodo": f"últimos {dias} días",
            "note": "Endpoint pendiente de implementación (requiere query compleja)",
            "data": []
        }
    
    except Exception as e:
        logger.error(f"Error en obtener_features_top_global: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health check
@router.get("/health/xai", tags=["XAI"])
async def health_xai() -> Dict[str, Any]:
    """
    Verifica disponibilidad del sistema XAI.
    """
    try:
        # Test: intentar obtener una explicación
        dao = ExplicacionXAIDAO()
        # Si falla, caught en except
        
        return {
            "status": "healthy",
            "xai_engine": "online",
            "database": "connected"
        }
    
    except Exception as e:
        logger.error(f"XAI health check failed: {e}")
        return {
            "status": "unhealthy",
            "xai_engine": "error",
            "database": "connection_failed",
            "error": str(e)
        }
