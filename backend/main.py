from fastapi import FastAPI, HTTPException, Header
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
def chat(mensaje: ChatMessageRequest, authorization: str = Header(None)):
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
    """
    # 1. Validar token y extraer user_id (lanzará HTTPException si hay error)
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token de autenticación requerido. Usa el formato 'Bearer <token>'")
    
    token = authorization.replace("Bearer ", "")
    user_id = auth_service.validar_token(token)  # Si falla, lanza HTTPException(401)
    
    # 2. Procesar el mensaje con el user_id validado
    try:
        respuesta = chat_service.procesar_mensaje(
            id_usuario=user_id,
            mensaje=mensaje.message
        )
        return respuesta
    except Exception as e:
        error_msg = str(e)
        
        # Si es error de límite de mensajes, devolver 429 (Too Many Requests)
        if "límite" in error_msg.lower() or "limit" in error_msg.lower():
            raise HTTPException(status_code=429, detail=error_msg)
        
        # Si es error de validación (longitud, vacío, usuario no encontrado)
        elif any(keyword in error_msg.lower() for keyword in ["demasiado largo", "vacío", "no encontrado"]):
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Si es error de API key de Gemini
        elif "api" in error_msg.lower() and ("key" in error_msg.lower() or "credential" in error_msg.lower()):
            raise HTTPException(
                status_code=500, 
                detail="Error de configuración: La API key de Gemini no está configurada correctamente. Contacta al administrador."
            )
        
        # Si es error de cuota agotada de Gemini
        elif "quota" in error_msg.lower() or "resource exhausted" in error_msg.lower() or "429" in error_msg:
            raise HTTPException(
                status_code=503,
                detail="El servicio de IA ha alcanzado su límite de uso. Por favor intenta de nuevo más tarde."
            )
        
        # Otros errores del servicio de IA
        raise HTTPException(status_code=500, detail=f"Error del servicio de IA: {error_msg}")