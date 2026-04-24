"""
DTOs (Data Transfer Objects) para cursos y diapositivas.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

# ==========================================
# DTOs DE CURSOS
# ==========================================

class CursoListResponse(BaseModel):
    id_curso: int = Field(alias="id") # Mapeamos 'id' de la BD a 'id_curso'
    titulo: str
    descripcion: Optional[str] = None
    plan_pro: bool = False
    
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

class DiapositivaResponse(BaseModel):
    id: int
    id_curso: int
    num_pag: int 
    contenido: str
    
    model_config = ConfigDict(from_attributes=True)

class CursoDetailResponse(BaseModel):
    id_curso: int = Field(alias="id")
    titulo: str
    descripcion: Optional[str] = None
    plan_pro: bool = False
    diapositivas: List[DiapositivaResponse] = []
    
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


# ==========================================
# DTOs DE PROGRESO
# ==========================================

class ProgresoResponse(BaseModel):
    id_usuario: str
    id_curso: int
    diapositiva_alcanzada: int 
    completado: bool 
    progreso_pct: float = Field(..., description="Calculado al vuelo (0-100)")
    
    model_config = ConfigDict(from_attributes=True)

class ProgresoDiapositivaRequest(BaseModel):
    diapositiva_numero: int = Field(..., ge=1)
