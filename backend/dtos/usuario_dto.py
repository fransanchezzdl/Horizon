from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# DTO de salida que refleja la tabla `usuarios`
class UsuarioResponse(BaseModel):
    id_usuario: str
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    email: EmailStr
    membresia: Optional[str] = None
    foto_perfil: Optional[str] = None
    created_at: Optional[datetime] = None

# DTO de entrada para actualizar el perfil (Seguridad: solo campos permitidos)
class PerfilUpdateDTO(BaseModel):
    email: Optional[str] = None
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    foto_perfil: Optional[str] = None

# DTO para cambio de contraseña
class ChangePasswordRequest(BaseModel):
    password_actual: str
    password_nueva: str