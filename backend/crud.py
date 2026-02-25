from .database import supabase
from fastapi import HTTPException
from supabase import Client
from typing import Any


class UsuarioDAO:
    def __init__(self, db_client: Client):
        self.db = db_client

    def obtener_todos(self) -> list[dict]:
        """
        Trae todos los usuarios desde la tabla `usuarios`.
        Se seleccionan los campos que existen según el esquema de la DB.
        """
        response = self.db.table("usuarios").select("id_usuario,nombre,apellidos,email,membresia").execute()
        data = getattr(response, "data", None) or (response.get("data") if isinstance(response, dict) else None)
        return data or []


# Instanciamos el DAO para usarlo en nuestras rutas
usuario_dao = UsuarioDAO(supabase)


class AuthCRUD:
    def __init__(self, db_client: Client):
        self.db = db_client

    def iniciar_sesion(self, email: str, password: str) -> tuple[str, dict]:
        try:
            # 1. Intentar iniciar sesión con Supabase Auth
            auth_response = self.db.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })

            # `auth_response` puede ser un objeto o un dict según la versión de la librería
            if isinstance(auth_response, dict):
                user = auth_response.get("user")
                session = auth_response.get("session")
            else:
                user = getattr(auth_response, "user", None)
                session = getattr(auth_response, "session", None)

            if not user or not session:
                raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

            # Obtener id del usuario (puede venir como dict o como objeto)
            user_id = user.get("id") if isinstance(user, dict) else getattr(user, "id", None)

            # 2. Verificar que el usuario exista en la tabla `usuarios` (campo id_usuario)
            perfil_response = self.db.table("usuarios").select("*").eq("id_usuario", user_id).execute()
            perfil_data = getattr(perfil_response, "data", None) or (perfil_response.get("data") if isinstance(perfil_response, dict) else None)

            if not perfil_data:
                # Si no tiene perfil, cerramos la sesión por seguridad (si es posible)
                try:
                    self.db.auth.sign_out()
                except Exception:
                    pass
                raise HTTPException(status_code=403, detail="Usuario no registrado en el sistema.")

            # Obtener access token del session
            access_token = session.get("access_token") if isinstance(session, dict) else getattr(session, "access_token", None)

            return access_token, perfil_data[0]

        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

    def registrar_usuario(self, email: str, password: str, nombre: str | None = None, apellidos: str | None = None) -> tuple[str | None, dict | None]:
        try:
            # 1. Registrar en Supabase Auth
            sign_response = self.db.auth.sign_up({
                "email": email,
                "password": password,
            })

            if isinstance(sign_response, dict):
                user = sign_response.get("user")
                session = sign_response.get("session")
            else:
                user = getattr(sign_response, "user", None)
                session = getattr(sign_response, "session", None)

            if not user:
                raise HTTPException(status_code=400, detail="No se pudo registrar el usuario")

            user_id = user.get("id") if isinstance(user, dict) else getattr(user, "id", None)

            # 2. Crear perfil en la tabla `usuarios`
            try:
                self.db.table("usuarios").insert({
                    "id_usuario": user_id,
                    "email": email,
                    "nombre": nombre,
                    "apellidos": apellidos,
                    "membresia": "Gratis",
                }).execute()
            except Exception:
                # Si la inserción falla, intentamos limpiar el usuario creado en Auth (si aplica)
                raise HTTPException(status_code=400, detail="Error al crear el perfil de usuario")

            # 3. Obtener perfil creado
            perfil_response = self.db.table("usuarios").select("*").eq("id_usuario", user_id).execute()
            perfil_data = getattr(perfil_response, "data", None) or (perfil_response.get("data") if isinstance(perfil_response, dict) else None)

            # 4. Obtener token de sesión: preferir session de sign_up, si no, intentar sign_in
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

            return access_token, (perfil_data[0] if perfil_data else None)

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


# Instanciamos el CRUD
auth_crud = AuthCRUD(supabase)