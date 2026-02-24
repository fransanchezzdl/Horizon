from supabase import Client
from database import supabase
from fastapi import HTTPException

class UsuarioDAO:
    def __init__(self, db_client: Client):
        self.db = db_client

    def obtener_todos(self):
        # Traer todos los datos de la tabla 'profiles'
        response = self.db.table("profiles").select("*").execute()
        return response.data

# Instanciamos el DAO para usarlo en nuestras rutas
usuario_dao = UsuarioDAO(supabase)

class AuthCRUD:
    def __init__(self, db_client: Client):
        self.db = db_client

    def iniciar_sesion(self, email: str, password: str):
        try:
            # 1. Intentar iniciar sesión con Supabase Auth
            auth_response = self.db.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            user = auth_response.user
            
            # 2. (Opcional pero recomendado según tu código viejo) 
            # Verificar que el usuario exista en tu tabla 'profiles' o 'usuarios'
            perfil_response = self.db.table("profiles").select("*").eq("id", user.id).execute()
            
            if not perfil_response.data:
                # Si no tiene perfil, cerramos la sesión por seguridad
                self.db.auth.sign_out()
                raise HTTPException(status_code=403, detail="Usuario no registrado en el sistema.")

            # Devolvemos tanto los datos de Auth como el perfil de tu tabla
            return auth_response.session.access_token, perfil_response.data[0]

        except Exception as e:
            # Si el error es una HTTPException nuestra (como la del perfil), la dejamos pasar
            if isinstance(e, HTTPException):
                raise e
            # Cualquier otro error (ej: contraseña mala), devolvemos un 401 (No Autorizado)
            raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

# Instanciamos el CRUD
auth_crud = AuthCRUD(supabase)