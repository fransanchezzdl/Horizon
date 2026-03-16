from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ==========================================
# REFLEXIONES DTOs
# ==========================================

class ReflexionCardResponse(BaseModel):
    """Response reducido para mostrar en la tarjeta del dashboard."""
    id_reflexion: int
    cita: str
    autor: str
    tema: str

    class Config:
        from_attributes = True


class ReflexionArticuloResponse(BaseModel):
    """Response completo con todos los datos del artículo extendido."""
    id_reflexion: int
    cita: str
    autor: str
    tema: str
    titulo_articulo: str
    contenido: str
    imagen_url: Optional[str] = None
    tiempo_lectura: Optional[int] = None
    tags: Optional[List[str]] = None
    created_at: datetime

    class Config:
        from_attributes = True
