"""Servicio de chat que orquesta la lógica de negocio del chatbot."""

from ..dtos.chat_dto import ChatMessageRequest, ChatMessageResponse
from ..daos.usuario_dao import usuario_dao
from ..daos.chat_dao import chat_dao
from .gemini_service import gemini_service
from ..exceptions import (
    RateLimitExceededError,
    MessageTooLongError,
    EmptyMessageError,
    UsuarioNoEncontradoError
)


class ChatService:
    """
    Servicio que maneja la lógica de negocio del chatbot.
    Orquesta los DAOs (usuario, chat) y servicios externos (Gemini).
    """
    
    def __init__(self, usuario_dao_instance, chat_dao_instance, gemini_service_instance):
        self.usuario_dao = usuario_dao_instance
        self.chat_dao = chat_dao_instance
        self.gemini_service = gemini_service_instance
    
    def procesar_mensaje(self, id_usuario: str, mensaje: str) -> ChatMessageResponse:
        """
        Procesa un mensaje del usuario y obtiene respuesta de Gemini.
        
        Flujo:
        1. Valida longitud del mensaje
        2. Obtiene información del usuario (membresía)
        3. Verifica límite de rate limiting
        4. Registra el mensaje
        5. Llama a Gemini para obtener respuesta
        6. Devuelve la respuesta
        
        Args:
            id_usuario: ID del usuario autenticado
            mensaje: Mensaje del usuario
            
        Returns:
            ChatMessageResponse con el mensaje y la respuesta de la IA
            
        Raises:
            Exception: Si hay errores de validación, rate limiting, usuario no encontrado,
                      o problemas con el servicio de IA
        """
        # 1. Validar longitud del mensaje
        self._validar_longitud_mensaje(mensaje)
        
        # 2. Obtener usuario (necesitamos su membresía para rate limiting)
        usuario = self.usuario_dao.obtener_por_id(id_usuario)
        if not usuario:
            raise UsuarioNoEncontradoError(id_usuario)
        
        # 3. Verificar límite de mensajes (rate limiting)
        puede_enviar, mensajes_enviados, limite = self.chat_dao.verificar_limite_mensajes(
            id_usuario=id_usuario,
            membresia=usuario.membresia
        )
        
        if not puede_enviar:
            raise RateLimitExceededError(mensajes_enviados, limite, usuario.membresia)
        
        # 4. Registrar el mensaje (para rate limiting)
        self.chat_dao.registrar_mensaje(id_usuario)
        
        # 5. Generar respuesta con Gemini
        respuesta_ia = self.gemini_service.generar_respuesta(mensaje)
        
        # 6. Devolver respuesta
        return ChatMessageResponse(
            usuario_mensaje=mensaje,
            respuesta_ia=respuesta_ia
        )
    
    def _validar_longitud_mensaje(self, mensaje: str) -> None:
        """
        Valida que el mensaje no exceda 100 caracteres.
        
        Args:
            mensaje: Mensaje del usuario
            
        Raises:
            Exception: Si el mensaje excede 100 caracteres o está vacío
        """
        longitud = len(mensaje.strip())
        if longitud > 100:
            raise MessageTooLongError(longitud)
        if longitud == 0:
            raise EmptyMessageError()


# Instancia singleton del servicio
chat_service = ChatService(usuario_dao, chat_dao, gemini_service)
