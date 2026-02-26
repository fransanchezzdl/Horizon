from pydantic import BaseModel, EmailStr
from typing import Optional

# DTO de salida que refleja la tabla `usuarios`
class UsuarioResponse(BaseModel):
    id_usuario: str
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    email: EmailStr
    membresia: Optional[str] = None