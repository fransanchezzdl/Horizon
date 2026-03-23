from typing import Any
from datetime import datetime
from ..database import supabase
from ..dtos import UsuarioResponse


class UsuarioDAO:
    def __init__(self, db_client: Any):
        self.db = db_client

    def obtener_todos(self) -> list[UsuarioResponse]:
        """
        Trae todos los usuarios desde la tabla `usuarios`.
        Se seleccionan los campos que existen según el esquema de la DB.
        """
        response = self.db.table("usuarios").select("id_usuario,nombre,apellidos,email,membresia,foto_perfil,created_at").execute()
        data = getattr(response, "data", None) or (response.get("data") if isinstance(response, dict) else None)
        # Convertir cada dict a UsuarioResponse
        items = data or []
        return [UsuarioResponse(**item) for item in items]

    def obtener_por_id(self, user_id: str) -> UsuarioResponse | None:
        """Devuelve el perfil del usuario por su id (id_usuario) o None."""
        resp = self.db.table("usuarios").select("id_usuario,nombre,apellidos,email,membresia,foto_perfil,created_at").eq("id_usuario", user_id).execute()
        data = getattr(resp, "data", None) or (resp.get("data") if isinstance(resp, dict) else None)
        if data and len(data) > 0:
            return UsuarioResponse(**data[0])
        return None

    def crear_perfil(self, user_id: str, email: str, nombre: str | None = None, apellidos: str | None = None, foto_perfil: str | None = None) -> None:
        """Inserta un nuevo registro en la tabla `usuarios` para el perfil del usuario."""
        self.db.table("usuarios").insert({
            "id_usuario": user_id,
            "email": email,
            "nombre": nombre,
            "apellidos": apellidos,
            "membresia": "Gratis",
            "foto_perfil": foto_perfil,
        }).execute()

    # Función para actualizar el perfil del usuario
    def actualizar_perfil(self, user_id: str, nombre: str | None = None, apellidos: str | None = None, foto_perfil: str | None = None, email: str | None = None) -> None:
        """Actualiza el perfil del usuario con los campos proporcionados."""
        update_data = {}
        if nombre is not None:
            update_data["nombre"] = nombre
        if apellidos is not None:
            update_data["apellidos"] = apellidos
        if foto_perfil is not None:
            update_data["foto_perfil"] = foto_perfil
        if email is not None: 
            update_data["email"] = email

        if update_data:
            self.db.table("usuarios").update(update_data).eq("id_usuario", user_id).execute()

    def actualizar_foto_perfil(self, user_id: str, foto_perfil: str | None) -> None:
        """Actualiza el campo foto_perfil incluso cuando el valor es None."""
        self.db.table("usuarios").update({"foto_perfil": foto_perfil}).eq("id_usuario", user_id).execute()

    def restaurar_perfil(self, perfil: UsuarioResponse) -> None:
        """Restaura una fila de usuario (usado en rollback lógico)."""
        payload = {
            "id_usuario": perfil.id_usuario,
            "email": str(perfil.email),
            "nombre": perfil.nombre,
            "apellidos": perfil.apellidos,
            "membresia": perfil.membresia,
            "foto_perfil": perfil.foto_perfil,
        }
        if isinstance(perfil.created_at, datetime):
            payload["created_at"] = perfil.created_at.isoformat()

        self.db.table("usuarios").insert(payload).execute()
    
    # Función para eliminar el perfil del usuario
    def eliminar_perfil(self, user_id: str) -> None:
        """
        Elimina físicamente el registro del usuario de la tabla pública `usuarios`.
        """
        # Ejecutar el comando DELETE donde el id_usuario coincida
        self.db.table("usuarios").delete().eq("id_usuario", user_id).execute()


# Instanciamos el DAO para usarlo en nuestras rutas
usuario_dao = UsuarioDAO(supabase)
