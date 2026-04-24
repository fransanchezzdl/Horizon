"""DAO para acceso a datos relacionados con el chat (rate limiting)."""

from typing import Any

from ..database import supabase, supabase_admin


class ChatDAO:
    """DAO para acceso a datos relacionados con el chat (rate limiting)."""
    
    # Límites de mensajes por minuto según membresía
    LIMITES_MEMBRESIA = {
        "Gratis": 1,
        "PRO": 1
    }
    
    RATE_LIMIT_WINDOW_SECONDS = 60
    RATE_LIMIT_RPC = "verificar_y_registrar_chat_rate_limit"

    def __init__(self, db_client: Any = None):
        """
        Inicializa el DAO del chat.

        Usa el cliente admin de Supabase si está disponible para ejecutar la
        función RPC transaccional de rate limiting.
        """
        self.db = db_client or supabase_admin or supabase

    def verificar_limite_mensajes(self, id_usuario: str, membresia: str) -> tuple[bool, int, int]:
        """
        Verifica e incrementa el contador de mensajes en una sola operación transaccional.
        
        Args:
            id_usuario: ID del usuario
            membresia: Tipo de membresía del usuario ("Gratis" o "PRO")
            
        Returns:
            tupla (puede_enviar: bool, mensajes_enviados: int, limite: int)
        """
        # Determinar el límite según membresía
        limite = self.LIMITES_MEMBRESIA.get(membresia, 1)

        try:
            response = (
                self.db.rpc(
                    self.RATE_LIMIT_RPC,
                    {
                        "p_id_usuario": id_usuario,
                        "p_limite": limite,
                        "p_window_seconds": self.RATE_LIMIT_WINDOW_SECONDS,
                    },
                )
                .execute()
            )

            data = getattr(response, "data", None) or []
            if not data:
                return False, 0, limite

            resultado = data[0] if isinstance(data, list) else data
            puede_enviar = bool(resultado.get("puede_enviar", False))
            mensajes_enviados = int(resultado.get("mensajes_enviados", 0) or 0)
            limite_devuelto = int(resultado.get("limite", limite) or limite)
            return puede_enviar, mensajes_enviados, limite_devuelto

        except Exception as exc:
            print(f"[CHAT] Error ejecutando rate limit en BD: {exc}")
            raise

