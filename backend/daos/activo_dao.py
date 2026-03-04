from typing import Any
from ..database import supabase
from ..dtos import ActivoResponse

class ActivoDAO:
    def __init__(self, db_client: Any):
        self.db = db_client

    def obtener_todos(self) -> list[ActivoResponse]:
        """
        Trae todos los activos desde la tabla `activos`.
        """
        response = self.db.table("activos").select("ticker,nombre_completo,estabilidad,tamano").execute()
        data = getattr(response, "data", None) or (response.get("data") if isinstance(response, dict) else None)
        items = data or []
        return [ActivoResponse(**item) for item in items]

    def buscar_por_ticker(self, ticker: str) -> ActivoResponse | None:
        """
        Busca un activo por su ticker.
        """
        resp = self.db.table("activos").select("*").eq("ticker", ticker).execute()
        data = getattr(resp, "data", None) or (resp.get("data") if isinstance(resp, dict) else None)
        if data and len(data) > 0:
            return ActivoResponse(**data[0])
        return None

    def crear_activo(self, ticker: str, nombre_completo: str, estabilidad: str, tamano: str) -> None:
        """
        Inserta un nuevo activo en la tabla `activos`.
        """
        self.db.table("activos").insert({
            "ticker": ticker,
            "nombre_completo": nombre_completo,
            "estabilidad": estabilidad,
            "tamano": tamano,
        }).execute()


# Instancia global del DAO para uso en servicios y rutas
activo_dao = ActivoDAO(supabase)
