from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from .database import supabase

# Entidades
from .dtos import *
from .daos import usuario_dao, ActivoDAO, ReflexionDAO, ChatDAO, PortfolioDAO
from .services import (
    AuthService,
    GeminiService,
    ChatService,
    ActivoService,
    ReflexionService,
    PortfolioService,
    UserService,
)

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


# Wiring explícito de dependencias (evita singletons innecesarios)
auth_service = AuthService(supabase, usuario_dao)
gemini_service = GeminiService()
chat_dao = ChatDAO()
chat_service = ChatService(usuario_dao, chat_dao, gemini_service)
activo_service = ActivoService(ActivoDAO)
reflexion_service = ReflexionService(ReflexionDAO)
portfolio_service = PortfolioService(portfolio_dao=PortfolioDAO)
user_service = UserService(usuario_dao)


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
        foto_perfil=datos.foto_perfil,
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


# ─── Endpoint de Autenticación ──────────────────────────────────────

@app.get("/auth/me", response_model=UsuarioResponse)
def get_current_user_info(user_id: str = Depends(auth_service.get_current_user)):
    """
    Endpoint para validar la autenticación del usuario.
    
    El frontend llama a este endpoint para:
    1. Validar que el token es auténtico contra Supabase Auth
    2. Obtener los datos actualizados del usuario autenticado
    
    Reutiliza auth_service.get_current_user() que:
    - Extrae el token del header Authorization
    - Valida el token contra Supabase Auth
    - Verifica firma criptográfica, expiración y revocación
    - Extrae y devuelve el user_id
    
    Header requerido:
    - Authorization: Bearer <JWT_TOKEN>
    
    Returns:
    - 200 OK: {UsuarioResponse} - Token válido y auténtico
    - 401 Unauthorized: Token inválido, expirado o revocado
    - 401 Unauthorized: Header Authorization falta o está mal formateado
    """
    user = usuario_dao.obtener_por_id(user_id)
    if not user:
        # Caso raro: token válido pero usuario no existe
        # Podría ocurrir si se eliminó el usuario después de login
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    
    return user

# ─── Endpoint de Editar Perfil ─────────────────────────────────────────
@app.patch("/usuarios/me")
def editar_mi_perfil(datos: PerfilUpdateDTO, user_id: str = Depends(auth_service.get_current_user)):
    """
    Actualiza los datos del perfil del usuario autenticado (Actualización parcial).
    """
    return user_service.actualizar_perfil(user_id, datos)

# ─── Endpoints de Portfolios ─────────────────────────────────────────

@app.get("/portfolios", response_model=list[PortfolioListResponse])
def listar_portfolios(user_id: str = Depends(auth_service.get_current_user)):
    return portfolio_service.listar_portfolios_usuario(user_id)


@app.post("/portfolios", response_model=PortfolioResponse)
def crear_portfolio(datos: PortfolioCreateRequest, user_id: str = Depends(auth_service.get_current_user)):
    return portfolio_service.crear_portfolio_usuario(user_id, datos)


@app.get("/portfolios/{id_portfolio}", response_model=PortfolioResponse)
def obtener_portfolio(id_portfolio: int, user_id: str = Depends(auth_service.get_current_user)):
    return portfolio_service.obtener_portfolio_usuario(user_id, id_portfolio)


@app.put("/portfolios/{id_portfolio}", response_model=PortfolioResponse)
def actualizar_portfolio(id_portfolio: int, datos: PortfolioUpdateRequest, user_id: str = Depends(auth_service.get_current_user)):
    return portfolio_service.actualizar_portfolio_usuario(user_id, id_portfolio, datos)


@app.delete("/portfolios/{id_portfolio}")
def eliminar_portfolio(id_portfolio: int, user_id: str = Depends(auth_service.get_current_user)):
    return portfolio_service.eliminar_portfolio_usuario(user_id, id_portfolio)


@app.get("/portfolios/{id_portfolio}/activos", response_model=list[StockInPortfolioResponse])
def listar_activos_portfolio(id_portfolio: int, user_id: str = Depends(auth_service.get_current_user)):
    return portfolio_service.listar_activos_portfolio_usuario(user_id, id_portfolio)


@app.post("/portfolios/{id_portfolio}/activos", response_model=StockInPortfolioResponse)
def agregar_activo_portfolio(id_portfolio: int, datos: StockInPortfolioRequest, user_id: str = Depends(auth_service.get_current_user)):
    return portfolio_service.agregar_activo_portfolio_usuario(user_id, id_portfolio, datos)


@app.delete("/portfolios/{id_portfolio}/activos/{id_posicion}")
def eliminar_activo_portfolio(id_portfolio: int, id_posicion: int, user_id: str = Depends(auth_service.get_current_user)):
    return portfolio_service.eliminar_activo_portfolio_usuario(user_id, id_portfolio, id_posicion)
