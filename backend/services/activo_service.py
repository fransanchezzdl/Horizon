"""Servicio de activos – lógica de negocio para la gestión de activos (tickers)."""

from ..daos.activo_dao import ActivoDAO


class ActivoService:
    """
    Servicio que maneja la lógica de negocio de los activos.
    Orquesta el DAO de activos para listar y buscar tickers.
    """

    def __init__(self, activo_dao_cls=ActivoDAO):
        self.activo_dao = activo_dao_cls

    def listar_activos(self) -> list[dict]:
        """
        Devuelve todos los activos disponibles como lista de dicts.
        """
        activos = self.activo_dao.obtener_todos()
        return [a.model_dump() for a in activos]

    def buscar_activos(self, query: str) -> list[dict]:
        """
        Busca activos cuyo ticker o nombre contenga el texto proporcionado.
        La búsqueda es case-insensitive.
        """
        todos = self.activo_dao.obtener_todos()
        q = query.strip().lower()
        resultados = [
            a for a in todos
            if q in a.ticker.lower() or q in a.nombre_completo.lower()
        ]
        return [a.model_dump() for a in resultados]

    def obtener_activo(self, ticker: str) -> dict | None:
        """
        Devuelve un activo concreto por su ticker, o None si no existe.
        """
        activo = self.activo_dao.obtener_por_ticker(ticker.upper())
        return activo.model_dump() if activo else None

