from pydantic import BaseModel, EmailStr
from typing import Optional


# DTO de salida que refleja la tabla `usuarios`
class UsuarioResponse(BaseModel):
    id_usuario: str
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    email: EmailStr
    membresia: Optional[str] = None


# DTO para los datos que RECIBIMOS del frontend
class LoginRequest(BaseModel):
    # Usar EmailStr valida automáticamente que tenga formato de correo (@, .com, etc.)
    # Nota: requiere instalar el paquete: pip install "pydantic[email]"
    email: EmailStr
    password: str


# DTO para los datos que ENVIAMOS al frontend
class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UsuarioResponse


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