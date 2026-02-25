import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict

# Entidades (imports relativos ahora que `backend` es un paquete)
from .schemas import UsuarioResponse
from .schemas import LoginRequest, LoginResponse
from .schemas import RegisterRequest, RegisterResponse
from .crud import usuario_dao
from .crud import auth_crud

app = FastAPI()

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En producción cambiamos "*" por el dominio real (ej: "https://miweb.com")
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/usuarios", response_model=list[UsuarioResponse])
def get_usuarios():
    # Llamamos al DAO en lugar de a la base de datos directamente
    usuarios = usuario_dao.obtener_todos()
    return usuarios

@app.post("/login", response_model=LoginResponse)
def login(credenciales: LoginRequest):
    """
    Recibe email y password, valida con Supabase y devuelve un token de acceso.
    """
    # 1. Llamamos a nuestro CRUD. 
    # FastAPI ya validó automáticamente que el email sea válido gracias a Pydantic.
    token, perfil_usuario = auth_crud.iniciar_sesion(
        email=credenciales.email, 
        password=credenciales.password
    )
    
    # 2. Devolvemos la respuesta formateada según nuestro Schema
    return LoginResponse(
        access_token=token,
        user=perfil_usuario
    )


@app.post("/register", response_model=RegisterResponse)
def register(datos: RegisterRequest):
    """
    Registra un nuevo usuario: crea cuenta en Auth y perfil en la tabla `usuarios`.
    """
    token, perfil_usuario = auth_crud.registrar_usuario(
        email=datos.email,
        password=datos.password,
        nombre=datos.nombre,
        apellidos=datos.apellidos,
    )

    # Si no hay perfil o fallo, lanzamos error
    if not perfil_usuario:
        raise Exception("Error al crear el usuario")

    return RegisterResponse(
        access_token=token or "",
        user=perfil_usuario
    )

'''
@app.post("/crear-item")
def create_item(nombre: str):
    # Ejemplo: Insertar un dato
    data, count = supabase.table("items").insert({"name": nombre}).execute()
    return {"status": "success", "data": data}
'''
