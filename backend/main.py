from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

# Entidades
from .dtos import *
from .daos import *
from .services import *

# Exception handlers
from .exceptions import register_exception_handlers

app = FastAPI()

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En producción cambiamos "*" por el dominio real (ej: "https://miweb.com")
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar exception handlers globales
register_exception_handlers(app)


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


# ─── Endpoints de Activos ───────────────────────────────────────────

@app.get("/activos")
def listar_activos(q: str = ""):
    """
    Lista todos los activos. Si se pasa ?q=texto, filtra por ticker o nombre.
    """
    if q:
        return activo_service.buscar_activos(q)
    return activo_service.listar_activos()


@app.get("/activos/{ticker}")
def obtener_activo(ticker: str):
    """
    Devuelve un activo concreto por su ticker.
    """
    activo = activo_service.obtener_activo(ticker)
    if not activo:
        raise HTTPException(status_code=404, detail="Activo no encontrado")
    return activo


@app.post("/chat", response_model=ChatMessageResponse)
def chat(mensaje: ChatMessageRequest, user_id: str = Depends(auth_service.get_current_user)):
    """
    Endpoint para el chatbot con Gemini.
    
    Requiere autenticación con token JWT en el header Authorization.
    Recibe un mensaje del usuario y devuelve la respuesta del modelo IA.
    
    Header requerido:
    - Authorization: Bearer <JWT_TOKEN>
    
    Límites por membresía:
    - Gratis: 1 mensaje por minuto
    - PRO: 1 mensaje por minuto
    
    Restricciones:
    - Máximo 100 caracteres por mensaje
    
    Nota: Los errores se manejan automáticamente por exception handlers globales.
    """
    # El servicio lanza excepciones personalizadas que los handlers convierten en respuestas HTTP
    return chat_service.procesar_mensaje(
        id_usuario=user_id,
        mensaje=mensaje.message
    )


# ─── Endpoints de Reflexiones ──────────────────────────────────────────

@app.get("/reflexion/aleatoria", response_model=ReflexionArticuloResponse)
def reflexion_aleatoria(user_id: str = Depends(auth_service.get_current_user)):
    """
    Devuelve una reflexión financiera activa elegida aleatoriamente.

    Requiere autenticación con token JWT en el header Authorization.

    Errores posibles:
    - 401 si el token es inválido o no se incluye.
    - 404 si no hay reflexiones activas en la base de datos.
    """
    return reflexion_service.obtener_aleatoria()


@app.get("/reflexion/{id_reflexion}", response_model=ReflexionArticuloResponse)
def obtener_reflexion(id_reflexion: int, user_id: str = Depends(auth_service.get_current_user)):
    """
    Devuelve el artículo completo de una reflexión concreta por su ID.

    Requiere autenticación con token JWT en el header Authorization.

    Errores posibles:
    - 401 si el token es inválido o no se incluye.
    - 404 si no existe ninguna reflexión con ese ID.
    """
    return reflexion_service.obtener_por_id(id_reflexion)