"""Paquete de excepciones personalizadas y sus handlers."""

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

from .exception_handlers import register_exception_handlers

__all__ = [
    # Excepciones del chat
    "RateLimitExceededError",
    "MessageTooLongError",
    "EmptyMessageError",
    "UsuarioNoEncontradoError",
    # Excepciones de Gemini
    "GeminiAPIKeyMissingError",
    "GeminiQuotaExceededError",
    "GeminiAPIConfigError",
    "GeminiAPIError",
    # Handler registration
    "register_exception_handlers",
]
