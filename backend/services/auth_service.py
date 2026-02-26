from ..database import supabase
from ..daos import usuario_dao
from ..dtos import UsuarioResponse
from fastapi import HTTPException
from supabase import Client


class AuthService:
    """Servicio que contiene la lógica de negocio para login/registro.

    Orquesta llamadas al cliente de Auth (supabase) y al DAO de usuarios.
    """

    def __init__(self, db_client: Client, usuario_dao_instance: usuario_dao.__class__):
        self.db = db_client
        self.usuario_dao = usuario_dao_instance

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

            access_token = session.get("access_token") if isinstance(session, dict) else getattr(session, "access_token", None)
            return access_token, perfil

        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

    def registrar_usuario(self, email: str, password: str, nombre: str | None = None, apellidos: str | None = None) -> tuple[str | None, UsuarioResponse | None]:
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
                self.usuario_dao.crear_perfil(user_id=user_id, email=email, nombre=nombre, apellidos=apellidos)
            except Exception:
                raise HTTPException(status_code=400, detail="Error al crear el perfil de usuario")

            perfil = self.usuario_dao.obtener_por_id(user_id)

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


# Instanciamos el servicio listo para inyectar en controladores
auth_service = AuthService(supabase, usuario_dao)
