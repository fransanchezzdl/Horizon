from pydantic import BaseModel, EmailStr
from typing import Optional, Dict

# DTO de salida
class UsuarioResponse(BaseModel):
    id: str
    nombre: Optional[str] = None
    email: str
    
    # Añadimos aquí los demás campos

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
    user: Dict # Aquí enviaremos los datos del usuario