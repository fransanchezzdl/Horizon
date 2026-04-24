"""Servicio de reflexiones – lógica de negocio para las reflexiones financieras."""

from ..daos.reflexion_dao import ReflexionDAO
from ..exceptions.exceptions import ReflexionNoEncontradaError


class ReflexionService:
    """
    Servicio que gestiona la lógica de negocio de las reflexiones financieras.
    Orquesta el DAO de reflexiones y lanza excepciones de dominio cuando
    no se encuentran resultados.
    """

    def __init__(self, reflexion_dao_cls=ReflexionDAO):
        self.reflexion_dao = reflexion_dao_cls

    def obtener_aleatoria(self) -> dict:
        """
        Devuelve una reflexión activa aleatoria como dict.

        Raises:
            ReflexionNoEncontradaError: si la base de datos no contiene
                ninguna reflexión activa.
        """
        reflexion = self.reflexion_dao.obtener_aleatoria()
        if not reflexion:
            raise ReflexionNoEncontradaError()
        return reflexion.model_dump()

    def obtener_por_id(self, id_reflexion: int) -> dict:
        """
        Devuelve una reflexión concreta por su ID como dict.

        Args:
            id_reflexion: Clave primaria de la reflexión buscada.

        Raises:
            ReflexionNoEncontradaError: si no existe ninguna reflexión con ese ID.
        """
        reflexion = self.reflexion_dao.obtener_por_id(id_reflexion)
        if not reflexion:
            raise ReflexionNoEncontradaError(id_reflexion=id_reflexion)
        return reflexion.model_dump()

