from pydantic import BaseModel, ConfigDict
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

    model_config = ConfigDict(from_attributes=True)


class ReflexionArticuloResponse(BaseModel):
    """Response completo con todos los datos del artículo extendido."""
    id_reflexion: int
    cita: str
    autor: str
    tema: str
    titulo_articulo: str
    contenido: str
    tiempo_lectura: Optional[int] = None
    tags: Optional[List[str]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
