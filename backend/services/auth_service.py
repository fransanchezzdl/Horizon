from ..database import supabase
from ..daos import usuario_dao, UsuarioDAO
from ..dtos import UsuarioResponse
from fastapi import HTTPException, Header
from supabase import Client
from .storage_service import StorageService, storage_service


class AuthService:
    """Servicio que contiene la lógica de negocio para login/registro.

    Orquesta llamadas al cliente de Auth (supabase) y al DAO de usuarios.
    """

    def __init__(self, db_client: Client, usuario_dao_instance: UsuarioDAO, storage_service_instance: StorageService = storage_service):
        self.db = db_client
        self.usuario_dao = usuario_dao_instance
        self.storage_service = storage_service_instance

    def iniciar_sesion(self, email: str, password: str) -> tuple[str, UsuarioResponse]:
        try:
            auth_response = self.db.auth.sign_in_with_password({"email": email, "password": password})

            if isinstance(auth_response, dict):
                user = auth_response.get("user")
                session = auth_response.get("session")
            else:
                user = getattr(auth_response, "user", None)
                session = getattr(auth_response, "session", None)

            if not user or not session:
                raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

            user_id = user.get("id") if isinstance(user, dict) else getattr(user, "id", None)

            perfil = self.usuario_dao.obtener_por_id(user_id)
            if not perfil:
                try:
                    self.db.auth.sign_out()
                except Exception:
                    pass
                raise HTTPException(status_code=403, detail="Usuario no registrado en el sistema.")

            self.storage_service.hydrate_user_avatar_safe(perfil, "[AUTH]")

            access_token = session.get("access_token") if isinstance(session, dict) else getattr(session, "access_token", None)
            return access_token, perfil

        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

    def registrar_usuario(self, email: str, password: str, nombre: str | None = None, apellidos: str | None = None, foto_perfil: str | None = None) -> tuple[str | None, UsuarioResponse | None]:
        try:
            sign_response = self.db.auth.sign_up({"email": email, "password": password})

            if isinstance(sign_response, dict):
                user = sign_response.get("user")
                session = sign_response.get("session")
            else:
                user = getattr(sign_response, "user", None)
                session = getattr(sign_response, "session", None)

            if not user:
                raise HTTPException(status_code=400, detail="No se pudo registrar el usuario")

            user_id = user.get("id") if isinstance(user, dict) else getattr(user, "id", None)

            try:
                self.usuario_dao.crear_perfil(user_id=user_id, email=email, nombre=nombre, apellidos=apellidos, foto_perfil=foto_perfil)
            except Exception:
                raise HTTPException(status_code=400, detail="Error al crear el perfil de usuario")

            perfil = self.usuario_dao.obtener_por_id(user_id)
            if perfil:
                self.storage_service.hydrate_user_avatar_safe(perfil, "[AUTH]")

            access_token = None
            if session:
                access_token = session.get("access_token") if isinstance(session, dict) else getattr(session, "access_token", None)
            else:
                try:
                    auth_resp = self.db.auth.sign_in_with_password({"email": email, "password": password})
                    if isinstance(auth_resp, dict):
                        s = auth_resp.get("session")
                    else:
                        s = getattr(auth_resp, "session", None)
                    access_token = s.get("access_token") if isinstance(s, dict) else getattr(s, "access_token", None)
                except Exception:
                    access_token = None

            return access_token, perfil

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    def validar_token(self, token: str) -> str:
        """
        Valida un token JWT de Supabase y extrae el user_id.
        
        Verifica el token contra Supabase Auth para asegurar que:
        - El token fue emitido por Supabase (validación de firma)
        - No ha expirado
        - No ha sido revocado
        
        Args:
            token: Token JWT sin el prefijo "Bearer "
            
        Returns:
            str: El user_id del usuario autenticado
            
        Raises:
            HTTPException: Si el token es inválido, expirado o revocado
        """
        try:
            # Validar el token contra Supabase Auth
            # Esto verifica: firma criptográfica, expiración y revocación
            user_response = self.db.auth.get_user(token)
            
            # Extraer el objeto user (la estructura puede variar según la versión de supabase-py)
            if hasattr(user_response, 'user'):
                user = user_response.user
            elif isinstance(user_response, dict):
                user = user_response.get('user')
            else:
                user = user_response
            
            # Extraer el user_id
            if isinstance(user, dict):
                user_id = user.get('id')
            else:
                user_id = getattr(user, 'id', None)
            
            if not user_id:
                raise HTTPException(status_code=401, detail="Token inválido: no se pudo extraer el user_id")
            
            return user_id
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"[AUTH] Error validando token: {str(e)}")
            raise HTTPException(status_code=401, detail="Token inválido o expirado")
    
    def get_current_user(self, authorization: str = Header(None)) -> str:
        """
        Dependency para validar autenticación JWT en endpoints protegidos.
        
        Extrae y valida el token JWT del header Authorization.
        
        Args:
            authorization: Header Authorization con formato 'Bearer <token>'
            
        Returns:
            str: user_id del usuario autenticado
            
        Raises:
            HTTPException(401): Si el token es inválido, falta o está mal formateado
            
        Uso en endpoints:
            from fastapi import Depends
            from backend.services.auth_service import auth_service
            
            @app.post("/endpoint")
            def endpoint(user_id: str = Depends(auth_service.get_current_user)):
                # user_id contiene el ID del usuario autenticado
                ...
        """
        print(f"\n🔐 AUTH: Validando token")
        print(f"   Authorization header recibido: {bool(authorization)}")
        
        if not authorization or not authorization.startswith("Bearer "):
            print(f"❌ AUTH: Token falta o formato incorrecto")
            raise HTTPException(
                status_code=401, 
                detail="Token de autenticación requerido. Usa el formato 'Bearer <token>'"
            )
        
        token = authorization.replace("Bearer ", "")
        print(f"   Token extraído: {token[:20]}...")
        
        try:
            user_id = self.validar_token(token)  # Lanza HTTPException(401) si es inválido
            print(f"✅ AUTH: Token válido, user_id: {user_id}")
            return user_id
        except HTTPException as e:
            print(f"❌ AUTH: Error en validar_token: {e.status_code} - {e.detail}")
            raise
        except Exception as e:
            print(f"❌ AUTH: Error inesperado: {e}")
            raise HTTPException(status_code=401, detail="Error validando token")


# Instanciamos el servicio listo para inyectar en controladores
auth_service = AuthService(supabase, usuario_dao, storage_service)
