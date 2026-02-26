from pydantic import BaseModel, EmailStr
from typing import Optional
from .usuario_dto import UsuarioResponse  # Importación relativa

# DTO para el registro
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    nombre: Optional[str] = None
    apellidos: Optional[str] = None


class RegisterResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UsuarioResponse
