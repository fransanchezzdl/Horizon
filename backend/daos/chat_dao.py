from datetime import datetime, timedelta


class ChatDAO:
    """DAO para acceso a datos relacionados con el chat (rate limiting)."""
    
    # Límites de mensajes por minuto según membresía
    LIMITES_MEMBRESIA = {
        "Gratis": 1,
        "PRO": 1
    }
    
    def __init__(self):
        """
        Inicializa el DAO del chat.
        Mantiene un registro en memoria de los mensajes enviados por usuario.
        """
        # Diccionario para trackear mensajes: {user_id: [timestamp1, timestamp2, ...]}
        self.mensajes_por_usuario = {}

    def verificar_limite_mensajes(self, id_usuario: str, membresia: str) -> tuple[bool, int, int]:
        """
        Verifica si el usuario ha excedido su límite de mensajes por minuto.
        
        Args:
            id_usuario: ID del usuario
            membresia: Tipo de membresía del usuario ("Gratis" o "PRO")
            
        Returns:
            tupla (puede_enviar: bool, mensajes_enviados: int, limite: int)
        """
        # Determinar el límite según membresía
        limite = self.LIMITES_MEMBRESIA.get(membresia, 1)
        
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
    
    def registrar_mensaje(self, id_usuario: str) -> None:
        """
        Registra un mensaje enviado por el usuario para el rate limiting.
        
        Args:
            id_usuario: ID del usuario
        """
        if id_usuario not in self.mensajes_por_usuario:
            self.mensajes_por_usuario[id_usuario] = []
        
        self.mensajes_por_usuario[id_usuario].append(datetime.now())

