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

    def limpiar_dependencias_usuario(self, user_id: str) -> None:
        """
        Elimina dependencias de un usuario en tablas relacionadas para evitar
        bloqueos por claves foráneas cuando no hay ON DELETE CASCADE aplicado.

        Orden de limpieza:
        1) portfolio_activo de portfolios del usuario
        2) usuario_portfolio del usuario y por portfolios detectados
        3) portfolios del usuario
        """
        # Obtener portfolios del usuario
        portfolios_resp = (
            self.db.table("portfolios")
            .select("id_portfolio")
            .eq("id_usuario", user_id)
            .execute()
        )

        portfolio_rows = getattr(portfolios_resp, "data", None) or (
            portfolios_resp.get("data") if isinstance(portfolios_resp, dict) else []
        )
        portfolio_ids = [row.get("id_portfolio") for row in (portfolio_rows or []) if row.get("id_portfolio") is not None]

        # 1) Eliminar acciones de esos portfolios
        if portfolio_ids:
            (
                self.db.table("portfolio_activo")
                .delete()
                .in_("id_portfolio", portfolio_ids)
                .execute()
            )

        # 2a) Eliminar relaciones usuario_portfolio por usuario
        (
            self.db.table("usuario_portfolio")
            .delete()
            .eq("id_usuario", user_id)
            .execute()
        )

        # 2b) Eliminar posibles relaciones residuales por portfolio
        if portfolio_ids:
            (
                self.db.table("usuario_portfolio")
                .delete()
                .in_("id_portfolio", portfolio_ids)
                .execute()
            )

        # 3) Eliminar portfolios del usuario
        (
            self.db.table("portfolios")
            .delete()
            .eq("id_usuario", user_id)
            .execute()
        )
    
    # Función para eliminar el perfil del usuario
    def eliminar_perfil(self, user_id: str) -> None:
        """
        Elimina físicamente el registro del usuario de la tabla pública `usuarios`.
        """
        # Ejecutar el comando DELETE donde el id_usuario coincida
        self.db.table("usuarios").delete().eq("id_usuario", user_id).execute()


# Instanciamos el DAO para usarlo en nuestras rutas
usuario_dao = UsuarioDAO(supabase)
