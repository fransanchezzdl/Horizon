"""
DAO (Data Access Object) para reflexiones financieras.

Responsabilidades:
- Obtener una reflexión aleatoria activa (vía RPC de Supabase)
- Obtener una reflexión concreta por su ID
"""

from typing import Optional
from ..database import supabase
from ..dtos.reflexion_dto import ReflexionArticuloResponse


class ReflexionDAO:
    """Acceso a datos de reflexiones financieras."""

    TABLE = "reflexiones"

    @staticmethod
    def obtener_aleatoria() -> Optional[ReflexionArticuloResponse]:
        """
        Devuelve una reflexión activa elegida aleatoriamente mediante la
        función RPC get_reflexion_aleatoria() definida en Supabase.

        Returns:
            ReflexionArticuloResponse con los datos completos, o None si no
            hay reflexiones activas en la base de datos.
        """
        response = supabase.rpc("get_reflexion_aleatoria").execute()
        if response.data:
            return ReflexionArticuloResponse(**response.data[0])
        return None

    @staticmethod
    def obtener_por_id(id_reflexion: int) -> Optional[ReflexionArticuloResponse]:
        """
        Devuelve una reflexión concreta por su ID primario.

        Args:
            id_reflexion: Clave primaria de la reflexión.

        Returns:
            ReflexionArticuloResponse con los datos completos, o None si no existe.
        """
        response = (
            supabase.table(ReflexionDAO.TABLE)
            .select("*")
            .eq("id_reflexion", id_reflexion)
            .execute()
        )
        if response.data:
            return ReflexionArticuloResponse(**response.data[0])
        return None


