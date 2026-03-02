from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Entidades
from .dtos import *
from .daos import *
from .services import *

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
    # 1. Llamamos a nuestro service. 
    # FastAPI ya validó automáticamente que el email sea válido gracias a Pydantic.
    token, perfil_usuario = auth_service.iniciar_sesion(
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
    token, perfil_usuario = auth_service.registrar_usuario(
        email=datos.email,
        password=datos.password,
        nombre=datos.nombre,
        apellidos=datos.apellidos,
    )

    # Si no hay perfil o fallo, lanzamos error
    if not perfil_usuario:
        raise HTTPException(status_code= 500, detail="Error al crear el usuario")

    return RegisterResponse(
        access_token=token or "",
        user=perfil_usuario
    )


@app.post("/chat", response_model=ChatMessageResponse)
def chat(mensaje: ChatMessageRequest):
    """
    Endpoint para el chatbot con Gemini.
    
    Recibe un mensaje del usuario con su id_usuario y devuelve la respuesta del modelo IA.
    
    Límites por membresía:
    - Gratis: 1 mensajes por minuto
    - PRO: 5 mensajes por minuto
    
    Restricciones:
    - Máximo 100 caracteres por mensaje
    """
    try:
        respuesta = chat_dao.procesar_mensaje(
            id_usuario=mensaje.id_usuario,
            usuario_mensaje=mensaje.message
        )
        return respuesta
    except Exception as e:
        error_msg = str(e)
        # Si es error de límite, devolver 429 (Too Many Requests)
        if "límite" in error_msg.lower() or "limit" in error_msg.lower():
            raise HTTPException(status_code=429, detail=error_msg)
        # Si es error de validación (longitud, vacío, usuario no encontrado)
        elif any(keyword in error_msg.lower() for keyword in ["demasiado largo", "vacío", "no encontrado"]):
            raise HTTPException(status_code=400, detail=error_msg)
        # Otros errores
        raise HTTPException(status_code=500, detail=error_msg)