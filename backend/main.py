from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from .database import supabase

# Entidades
from .dtos import *
from .daos import usuario_dao, ActivoDAO, ReflexionDAO, ChatDAO, PortfolioDAO, CursoDAO
from .services import (
    AuthService,
    GeminiService,
    ChatService,
    ActivoService,
    TickerNewsService,
    ReflexionService,
    PortfolioService,
    CursoService,
    UserService,
    storage_service,
    PriceHistoryService,
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
auth_service = AuthService(supabase, usuario_dao, storage_service)
gemini_service = GeminiService()
chat_dao = ChatDAO()
chat_service = ChatService(
    usuario_dao_instance=usuario_dao,
    chat_dao_instance=chat_dao,
    gemini_service_instance=gemini_service,
    portfolio_dao_cls=PortfolioDAO,
    curso_dao_cls=CursoDAO,
    activo_dao_cls=ActivoDAO,
)
activo_service = ActivoService(ActivoDAO)
ticker_news_service = TickerNewsService()
reflexion_service = ReflexionService(ReflexionDAO)
portfolio_service = PortfolioService(portfolio_dao=PortfolioDAO)
curso_service = CursoService(CursoDAO)
user_service = UserService(usuario_dao, storage_service)


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


@app.post("/auth/change-password")
def cambiar_contrasena(
    datos: ChangePasswordRequest,
    user_id: str = Depends(auth_service.get_current_user)
):
    """
    Cambia la contraseña del usuario autenticado.
    
    Requiere autenticación (Bearer token en header Authorization).
    Valida la contraseña actual y si es correcta, la actualiza a la nueva.
    """
    return auth_service.cambiar_contrasena(
        id_usuario=user_id,
        password_actual=datos.password_actual,
        password_nueva=datos.password_nueva
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


@app.get("/activos/variaciones")
def obtener_variaciones_batch(tickers: str):
    """
    Devuelve la variación diaria (%) para varios tickers en una única llamada
    a yfinance, garantizando coherencia de fechas entre tickers.

    Nota: esta ruta debe declararse antes de /activos/{ticker} para evitar
    que "variaciones" se interprete como parámetro dinámico.

    tickers: lista separada por comas, ej: "AAPL,META,TSLA"
    Respuesta: {"AAPL": -0.5, "META": -2.31, "TSLA": null, ...}
    """
    lista = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if not lista:
        return {}
    return PriceHistoryService.get_daily_variations(lista)


@app.get("/activos/{ticker}")
def obtener_activo(ticker: str):
    """
    Devuelve un activo concreto por su ticker.
    """
    activo = activo_service.obtener_activo(ticker)
    if not activo:
        raise HTTPException(status_code=404, detail="Activo no encontrado")
    return activo


@app.get("/activos/{ticker}/noticias")
def obtener_noticias_activo(ticker: str, limit: int = 3):
    """Conector API -> service para noticias recientes del ticker con sentimiento IA."""
    activo = activo_service.obtener_activo(ticker)
    if not activo:
        raise HTTPException(status_code=404, detail="Activo no encontrado")

    return ticker_news_service.obtener_noticias_ticker(ticker=ticker, limit=limit)


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
    
    storage_service.hydrate_user_avatar_safe(user, "[AUTH/ME]")
    return user

# ─── Endpoint de Editar Perfil ─────────────────────────────────────────
@app.patch("/usuarios/me", response_model=UsuarioResponse)
def editar_mi_perfil(datos: PerfilUpdateDTO, user_id: str = Depends(auth_service.get_current_user)):
    """
    Actualiza los datos del perfil del usuario autenticado (Actualización parcial).
    """
    return user_service.actualizar_perfil(user_id, datos)

@app.delete("/usuarios/me")
def eliminar_usuario(user_id: str = Depends(auth_service.get_current_user)):
    """
    Elimina el perfil del usuario actual.
    """
    result = user_service.eliminar_perfil(user_id)
    return result

@app.post("/usuarios/me/avatar", response_model=UsuarioResponse)
def agregar_mi_avatar(file: UploadFile = File(...), user_id: str = Depends(auth_service.get_current_user)):
    """Sube un avatar para el usuario autenticado en /avatars/{id_usuario}/..."""
    return user_service.agregar_avatar(user_id, file)


@app.put("/usuarios/me/avatar", response_model=UsuarioResponse)
def actualizar_mi_avatar(file: UploadFile = File(...), user_id: str = Depends(auth_service.get_current_user)):
    """Reemplaza el avatar actual del usuario (elimina el anterior)."""
    return user_service.actualizar_avatar(user_id, file)


@app.delete("/usuarios/me/avatar")
def eliminar_mi_avatar(user_id: str = Depends(auth_service.get_current_user)):
    """Elimina el avatar actual del usuario y limpia foto_perfil en BD."""
    return user_service.eliminar_avatar(user_id)


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


# ── XAI Routes (Explicabilidad) ──────────────────────────────────────
# Importar y registrar rutas XAI
try:
    from .routes.xai_routes import router as xai_router
    app.include_router(xai_router)
except ImportError:
    print("⚠️ XAI routes no disponibles (SHAP no instalado)")
except Exception as e:
    print(f"⚠️ Error registrando XAI routes: {e}")


@app.get("/portfolios/{id_portfolio}/activos", response_model=list[StockInPortfolioResponse])
def listar_activos_portfolio(id_portfolio: int, user_id: str = Depends(auth_service.get_current_user)):
    return portfolio_service.listar_activos_portfolio_usuario(user_id, id_portfolio)


@app.post("/portfolios/{id_portfolio}/activos", response_model=StockInPortfolioResponse)
def agregar_activo_portfolio(id_portfolio: int, datos: StockInPortfolioRequest, user_id: str = Depends(auth_service.get_current_user)):
    return portfolio_service.agregar_activo_portfolio_usuario(user_id, id_portfolio, datos)


@app.delete("/portfolios/{id_portfolio}/activos/{id_posicion}")
def eliminar_activo_portfolio(id_portfolio: int, id_posicion: int, user_id: str = Depends(auth_service.get_current_user)):
    return portfolio_service.eliminar_activo_portfolio_usuario(user_id, id_portfolio, id_posicion)


@app.get("/portfolios/{id_portfolio}/analysis", response_model=PortfolioAnalysisResponse)
def get_portfolio_analysis(id_portfolio: int, user_id: str = Depends(auth_service.get_current_user)):
    portfolio_service._obtener_portfolio_si_es_propietario(user_id, id_portfolio)
    result = portfolio_service.get_portfolio_analysis(id_portfolio)
    if not result:
        raise HTTPException(status_code=404, detail="No se pudo analizar el portfolio")
    return result


# ─── Endpoints de Cursos ────────────────────────────────────────────

@app.get("/cursos", response_model=list[CursoListResponse])
def listar_cursos(user_id: str = Depends(auth_service.get_current_user)):
    """
    Lista todos los cursos disponibles para el usuario.
    """
    return curso_service.listar_cursos_disponibles()


@app.get("/cursos/resumen/progreso")
def obtener_resumen_progreso_academia(user_id: str = Depends(auth_service.get_current_user)):
    """
    Devuelve el número total de cursos completados por el usuario.
    """
    return curso_service.obtener_resumen_usuario(user_id)


@app.get("/cursos/{id_curso}", response_model=CursoDetailResponse)
def obtener_curso_detalle(id_curso: int, user_id: str = Depends(auth_service.get_current_user)):
    """
    Obtiene un curso específico con todas sus diapositivas reales.
    Automáticamente crea un registro de progreso si es la 1ª visita del usuario.
    """
    # Llama al service que obtiene el progreso o lo crea (1ª visita)
    _ = curso_service.obtener_o_crear_progreso(user_id, id_curso)
    
    # Retorna el detalle del curso con las diapositivas
    return curso_service.obtener_curso_con_diapositivas(id_curso)


# ─── Endpoints de Fiabilidad del Modelo ────────────────────────────

@app.get("/activos/{ticker}/reliability")
def obtener_fiabilidad_activo(ticker: str):
    """
    Devuelve las métricas de fiabilidad del modelo para un ticker.

    Combina:
    - Walk-forward offline (BA, F1, folds) desde walk_forward_results.json
    - Predicciones live registradas en prediction_log (Supabase)

    No requiere autenticación: es información pública del modelo.

    Ejemplo de respuesta:
    {
        "ticker": "KO",
        "walk_forward": {"ba_mean": 37.19, "ba_std": 4.95, "f1_mean": 35.91, "n_folds": 5},
        "live": {"total": 10, "resueltas": 5, "correctas": 3, "accuracy": 60.0, "por_clase": {...}},
        "baseline": 33.33,
        "señal": "MODERADA"
    }
    """
    from .services.prediction_log_service import get_reliability_stats
    activo = activo_service.obtener_activo(ticker)
    if not activo:
        raise HTTPException(status_code=404, detail="Activo no encontrado")
    return get_reliability_stats(ticker.upper())


@app.get("/activos/{ticker}/price-history")
def obtener_price_history(ticker: str, days: int = 30):
    """
    Devuelve OHLC histórico + señales IA para el ticker en los últimos N días.
    days: 7 | 30 | 90 (default 30)
    """
    activo = activo_service.obtener_activo(ticker)
    if not activo:
        raise HTTPException(status_code=404, detail="Activo no encontrado")

    return PriceHistoryService.get_price_and_signals(ticker=ticker, days=days)


@app.get("/activos/{ticker}/xai/shap-temporal")
def obtener_shap_temporal(ticker: str, limit: int = 30):
    """
    Devuelve la evolución temporal de las top-3 features SHAP para el ticker.
    Usado por el gráfico de líneas temporal en el frontend.
    """
    from .daos.xai_shap_dao import XaiShapDAO

    result = XaiShapDAO.obtener_shap_temporal(ticker.upper(), limit=limit)
    if not result:
        raise HTTPException(status_code=404, detail="Sin histórico SHAP para este ticker")
    return result


@app.get("/activos/{ticker}/xai/latest-shap")
def obtener_latest_shap(ticker: str):
    """
    Devuelve los SHAP values más recientes para el ticker.

    Busca la fila más reciente en xai_explicaciones y retorna:
    - ticker, fecha, senal, confianza, correcta
    - shap_values: lista de {feature, shap, value, abs} ordenada por abs desc, máx 12

    No requiere autenticación: información pública del modelo.
    """
    from .daos.xai_shap_dao import XaiShapDAO

    result = XaiShapDAO.obtener_latest_shap(ticker.upper())
    if not result:
        raise HTTPException(status_code=404, detail="Sin datos SHAP para este ticker")
    return result


@app.get("/cursos/{id_curso}/progreso", response_model=ProgresoResponse)
def obtener_progreso_curso(id_curso: int, user_id: str = Depends(auth_service.get_current_user)):
    """
    Obtiene el progreso actual del usuario en un curso específico.
    """
    return curso_service.obtener_o_crear_progreso(user_id, id_curso)


@app.post("/cursos/{id_curso}/progreso", response_model=ProgresoResponse)
def guardar_progreso_curso(
    id_curso: int,
    datos: ProgresoDiapositivaRequest,
    user_id: str = Depends(auth_service.get_current_user)
):
    """
    Registra que el usuario avanzó a una diapositiva específica.
    Auto-marca el curso como completado si llega a la última diapositiva.
    """
    return curso_service.avanzar_diapositiva(
        user_id=user_id,
        id_curso=id_curso,
        numero_diapositiva=datos.diapositiva_numero
    )