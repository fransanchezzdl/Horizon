from typing import Any
from datetime import datetime, timedelta
from ..dtos.chat_dto import ChatMessageRequest, ChatMessageResponse
from ..services.gemini_service import gemini_service
from .usuario_dao import usuario_dao


class ChatDAO:
    # Límites de mensajes por hora según membresía
    LIMITES_MEMBRESIA = {
        "Gratis": 1,
        "PRO": 1
    }
    
    def __init__(self, ai_service: Any = None):
        """
        Inicializa el DAO del chat.
        
        Args:
            ai_service: Servicio de IA (Gemini) para generar respuestas
        """
        self.ai_service = ai_service 
        # Diccionario para trackear mensajes: {user_id: [timestamp1, timestamp2, ...]}
        self.mensajes_por_usuario = {}

    def _verificar_limite_mensajes(self, id_usuario: str) -> tuple[bool, int, int]:
        """
        Verifica si el usuario ha excedido su límite de mensajes por hora.
        
        Args:
            id_usuario: ID del usuario
            
        Returns:
            tupla (puede_enviar: bool, mensajes_enviados: int, limite: int)
            
        Raises:
            Exception: Si no se puede obtener la información del usuario
        """
        # Obtener información del usuario
        usuario = usuario_dao.obtener_por_id(id_usuario)
        
        if not usuario:
            raise Exception("Usuario no encontrado")
        
        # Determinar el límite según membresía
        limite = self.LIMITES_MEMBRESIA.get(usuario.membresia, 10)
        
        # Obtener timestamp actual y hace 1 min
        ahora = datetime.now()
        hace_un_minuto = ahora - timedelta(minutes=1)
        
        # Obtener mensajes del usuario en el útlimo minuto
        if id_usuario in self.mensajes_por_usuario:
            # Filtrar solo los mensajes del último minuto
            mensajes_recientes = [
                ts for ts in self.mensajes_por_usuario[id_usuario]
                if ts > hace_un_minuto
            ]
            # Actualizar el registro con solo mensajes recientes
            self.mensajes_por_usuario[id_usuario] = mensajes_recientes
        else:
            mensajes_recientes = []
            self.mensajes_por_usuario[id_usuario] = []
        
        mensajes_enviados = len(mensajes_recientes)
        puede_enviar = mensajes_enviados < limite
        
        return puede_enviar, mensajes_enviados, limite

    def _validar_longitud_mensaje(self, usuario_mensaje: str) -> None:
        """
        Valida que el mensaje no exceda 100 caracteres.
        
        Args:
            usuario_mensaje: Mensaje del usuario
            
        Raises:
            Exception: Si el mensaje excede 100 caracteres
        """
        longitud = len(usuario_mensaje.strip())
        if longitud > 100:
            raise Exception(
                f"El mensaje es demasiado largo. Máximo 100 caracteres. "
                f"Tu mensaje tiene {longitud} caracteres."
            )
        if longitud == 0:
            raise Exception("El mensaje no puede estar vacío.")

    def procesar_mensaje(
        self, 
        id_usuario: str, 
        usuario_mensaje: str
    ) -> ChatMessageResponse:
        """
        Procesa un mensaje del usuario y obtiene la respuesta del modelo de IA (Gemini).
        
        Args:
            id_usuario: ID del usuario
            usuario_mensaje: Mensaje del usuario
            
        Returns:
            ChatMessageResponse con el mensaje y la respuesta del IA
            
        Raises:
            Exception: Si el usuario excede el límite de mensajes, si el mensaje es inválido,
                      o si hay errores con el servicio de IA
        """
        # Validar longitud del mensaje (máximo 100 caracteres)
        self._validar_longitud_mensaje(usuario_mensaje)
        
        # Verificar límite de mensajes
        puede_enviar, mensajes_enviados, limite = self._verificar_limite_mensajes(id_usuario)
        
        if not puede_enviar:
            raise Exception(
                f"Has alcanzado el límite de {limite} mensaje/s por minuto para tu membresía. "
                f"Has enviado {mensajes_enviados} mensaje/s. Intenta de nuevo luego o mejora tu membresía."
            )
        
        # Registrar el mensaje actual
        self.mensajes_por_usuario[id_usuario].append(datetime.now())
        
        # Procesar con Gemini - dejamos que las excepciones se propaguen
        respuesta_ia = self.ai_service.generar_respuesta(id_usuario, usuario_mensaje)
        
        return ChatMessageResponse(
            usuario_mensaje=usuario_mensaje,
            respuesta_ia=respuesta_ia
        )


# Instanciamos el DAO para usarlo en nuestras rutas
chat_dao = ChatDAO(gemini_service)
