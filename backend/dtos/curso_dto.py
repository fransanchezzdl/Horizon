"""
DTOs (Data Transfer Objects) para cursos y diapositivas.
"""

from pydantic import BaseModel, Field
from typing import Optional, List

# ==========================================
# DTOs DE CURSOS
# ==========================================

class CursoListResponse(BaseModel):
    id_curso: int = Field(alias="id") # Mapeamos 'id' de la BD a 'id_curso'
    titulo: str
    descripcion: Optional[str] = None
    
    class Config:
        populate_by_name = True
        from_attributes = True

class DiapositivaResponse(BaseModel):
    id: int
    id_curso: int
    num_pag: int 
    contenido: str
    
    class Config:
        from_attributes = True

class CursoDetailResponse(BaseModel):
    id_curso: int = Field(alias="id")
    titulo: str
    descripcion: Optional[str] = None
    diapositivas: List[DiapositivaResponse] = []
    
    class Config:
        populate_by_name = True
        from_attributes = True


# ==========================================
# DTOs DE PROGRESO
# ==========================================

class ProgresoResponse(BaseModel):
    id_usuario: str
    id_curso: int
    diapositiva_alcanzada: int 
    completado: bool 
    progreso_pct: float = Field(..., description="Calculado al vuelo (0-100)")
    
    class Config:
        from_attributes = True

class ProgresoDiapositivaRequest(BaseModel):
    diapositiva_numero: int = Field(..., ge=1)
    
    class Config:
        from_attributes = True