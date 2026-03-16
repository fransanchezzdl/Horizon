"""Excepciones personalizadas para la lógica de negocio de Horizon."""


# ===== EXCEPCIONES DEL SERVICIO DE CHAT =====

class RateLimitExceededError(Exception):
    """Excepción cuando un usuario excede su límite de mensajes."""
    
    def __init__(self, mensajes_enviados: int, limite: int, membresia: str):
        self.mensajes_enviados = mensajes_enviados
        self.limite = limite
        self.membresia = membresia
        super().__init__(
            f"Has alcanzado el límite de {limite} mensaje/s por minuto para tu membresía {membresia}. "
            f"Has enviado {mensajes_enviados} mensaje/s. Intenta de nuevo luego o mejora tu membresía."
        )


class MessageTooLongError(Exception):
    """Excepción cuando un mensaje excede el límite de caracteres."""
    
    def __init__(self, longitud: int, limite: int = 100):
        self.longitud = longitud
        self.limite = limite
        super().__init__(
            f"El mensaje es demasiado largo. Máximo {limite} caracteres. "
            f"Tu mensaje tiene {longitud} caracteres."
        )


class EmptyMessageError(Exception):
    """Excepción cuando un mensaje está vacío."""
    
    def __init__(self):
        super().__init__("El mensaje no puede estar vacío.")


class UsuarioNoEncontradoError(Exception):
    """Excepción cuando un usuario no existe en la base de datos."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        super().__init__(f"Usuario con ID {user_id} no encontrado.")


# ===== EXCEPCIONES DEL SERVICIO DE GEMINI =====

class GeminiAPIKeyMissingError(Exception):
    """Excepción cuando la API key de Gemini no está configurada."""
    
    def __init__(self):
        super().__init__(
            "API key de Gemini no configurada. Asegúrate de incluir GEMINI_API_KEY en tu archivo backend/.env"
        )


class GeminiQuotaExceededError(Exception):
    """Excepción cuando se agota la cuota de la API de Gemini."""
    
    def __init__(self):
        super().__init__("Cuota de la API de Gemini agotada. Intenta de nuevo más tarde.")


class GeminiAPIConfigError(Exception):
    """Excepción para errores de configuración de la API de Gemini."""
    
    def __init__(self, detalle: str):
        self.detalle = detalle
        super().__init__(f"Error de configuración de Gemini API: {detalle}")


class GeminiAPIError(Exception):
    """Excepción genérica para errores de la API de Gemini."""
    
    def __init__(self, detalle: str):
        self.detalle = detalle
        super().__init__(f"Error al generar respuesta con Gemini: {detalle}")


# ===== EXCEPCIONES DEL SERVICIO DE REFLEXIONES =====

class ReflexionNoEncontradaError(Exception):
    """Excepción cuando no existe ninguna reflexión activa o el ID no corresponde a ningún registro."""

    def __init__(self, id_reflexion: int = None):
        self.id_reflexion = id_reflexion
        if id_reflexion is not None:
            super().__init__(f"Reflexión con ID {id_reflexion} no encontrada.")
        else:
            super().__init__("No hay reflexiones disponibles en este momento.")
