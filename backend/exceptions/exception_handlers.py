"""Exception handlers globales para la aplicación FastAPI."""

from fastapi import Request
from fastapi.responses import JSONResponse

from .exceptions import (
    RateLimitExceededError,
    MessageTooLongError,
    EmptyMessageError,
    UsuarioNoEncontradoError,
    GeminiAPIKeyMissingError,
    GeminiQuotaExceededError,
    GeminiAPIConfigError,
    GeminiAPIError
)


async def rate_limit_handler(request: Request, exc: RateLimitExceededError):
    """Maneja errores de rate limiting (429 Too Many Requests)."""
    return JSONResponse(
        status_code=429,
        content={"detail": str(exc)}
    )


async def message_too_long_handler(request: Request, exc: MessageTooLongError):
    """Maneja errores de mensaje demasiado largo (400 Bad Request)."""
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )


async def empty_message_handler(request: Request, exc: EmptyMessageError):
    """Maneja errores de mensaje vacío (400 Bad Request)."""
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )


async def usuario_no_encontrado_handler(request: Request, exc: UsuarioNoEncontradoError):
    """Maneja errores de usuario no encontrado (404 Not Found)."""
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)}
    )


async def gemini_api_key_missing_handler(request: Request, exc: GeminiAPIKeyMissingError):
    """Maneja errores de API key de Gemini faltante (500 Internal Server Error)."""
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Error de configuración: La API key de Gemini no está configurada correctamente. Contacta al administrador."
        }
    )


async def gemini_quota_exceeded_handler(request: Request, exc: GeminiQuotaExceededError):
    """Maneja errores de cuota agotada de Gemini (503 Service Unavailable)."""
    return JSONResponse(
        status_code=503,
        content={
            "detail": "El servicio de IA ha alcanzado su límite de uso. Por favor intenta de nuevo más tarde."
        }
    )


async def gemini_api_config_handler(request: Request, exc: GeminiAPIConfigError):
    """Maneja errores de configuración de la API de Gemini (500 Internal Server Error)."""
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )


async def gemini_api_error_handler(request: Request, exc: GeminiAPIError):
    """Maneja errores genéricos de la API de Gemini (500 Internal Server Error)."""
    return JSONResponse(
        status_code=500,
        content={"detail": f"Error del servicio de IA: {exc.detalle}"}
    )


def register_exception_handlers(app):
    """
    Registra todos los exception handlers en la aplicación FastAPI.
    
    Args:
        app: Instancia de FastAPI
        
    Uso:
        from backend.exceptions import register_exception_handlers
        
        app = FastAPI()
        register_exception_handlers(app)
    """
    app.add_exception_handler(RateLimitExceededError, rate_limit_handler)
    app.add_exception_handler(MessageTooLongError, message_too_long_handler)
    app.add_exception_handler(EmptyMessageError, empty_message_handler)
    app.add_exception_handler(UsuarioNoEncontradoError, usuario_no_encontrado_handler)
    app.add_exception_handler(GeminiAPIKeyMissingError, gemini_api_key_missing_handler)
    app.add_exception_handler(GeminiQuotaExceededError, gemini_quota_exceeded_handler)
    app.add_exception_handler(GeminiAPIConfigError, gemini_api_config_handler)
    app.add_exception_handler(GeminiAPIError, gemini_api_error_handler)
