from fastapi import HTTPException, UploadFile
from ..dtos.usuario_dto import PerfilUpdateDTO
from ..database import get_supabase_admin
from .storage_service import StorageService

class UserService:
    """
    Servicio que contiene la lógica de negocio para la gestión de usuarios.
    Actúa como intermediario entre los endpoints (main.py) y el acceso a datos (DAO).
    """

    def __init__(self, usuario_dao_instance, storage_service: StorageService):
        self.usuario_dao = usuario_dao_instance
        self.storage_service = storage_service

    def _obtener_usuario_or_404(self, user_id: str):
        perfil = self.usuario_dao.obtener_por_id(user_id)
        if not perfil:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        return perfil

    def _obtener_usuario_hidratado_or_500(self, user_id: str):
        updated = self.usuario_dao.obtener_por_id(user_id)
        if not updated:
            raise HTTPException(status_code=500, detail="No se pudo recuperar el usuario actualizado")
        self.storage_service.hydrate_user_avatar_safe(updated, "[USER]")
        return updated

    def actualizar_perfil(self, user_id: str, datos_actualizacion: PerfilUpdateDTO) -> dict:
        # 1. Convertir el DTO validado a un diccionario de Python.
        datos_dict = datos_actualizacion.model_dump(exclude_unset=True)

        perfil_actual = self._obtener_usuario_or_404(user_id)

        foto = datos_dict.get("foto_perfil")
        if isinstance(foto, str) and foto.startswith("data:"):
            raise HTTPException(
                status_code=400,
                detail="No se admite foto_perfil en base64. Usa el endpoint /usuarios/me/avatar.",
            )

        # 2. Verificar si hay datos reales para actualizar
        if not datos_dict:
            return {"status": "sin_cambios", "mensaje": "No se enviaron datos nuevos para actualizar."}

        # Si cambia a foto pública/default desde una personalizada, primero limpiar la anterior.
        # Estricto: si falla limpieza, no se aplica ningún cambio del PATCH.
        nueva_foto = datos_dict.get("foto_perfil")
        foto_anterior = perfil_actual.foto_perfil
        switch_managed_to_public = (
            nueva_foto is not None
            and foto_anterior
            and foto_anterior != nueva_foto
            and self.storage_service.is_managed_avatar(foto_anterior)
            and not self.storage_service.is_managed_avatar(nueva_foto)
        )

        if switch_managed_to_public:
            try:
                self.storage_service.delete_avatar(user_id, foto_anterior)
            except Exception:
                raise HTTPException(
                    status_code=500,
                    detail="No se pudo eliminar el avatar anterior. Se abortó la actualización.",
                )

        # 3. Extraer los datos y pasárselos a tu DAO existente
        try:
            # Intentamos guardar en la base de datos
            self.usuario_dao.actualizar_perfil(
                user_id=user_id,
                nombre=datos_dict.get("nombre"),
                apellidos=datos_dict.get("apellidos"),
                foto_perfil=datos_dict.get("foto_perfil"),
                email=datos_dict.get("email")
            )
        except Exception as e:
            # Si el DAO o Supabase fallan, lanzamos la excepción que el main.py atrapará
            print(f"[USER SERVICE] Error al actualizar perfil: {str(e)}")

            # Si ya borramos avatar anterior y falla DB, evitamos puntero roto a archivo inexistente.
            if switch_managed_to_public:
                try:
                    self.usuario_dao.actualizar_foto_perfil(user_id, None)
                except Exception:
                    pass

            raise HTTPException(
                status_code=500, 
                detail="Ocurrió un error al intentar guardar los cambios en la base de datos."
            )
        
        return {
            "status": "exito", 
            "mensaje": "Perfil actualizado correctamente.",
            "datos_actualizados": datos_dict
        }

    def eliminar_perfil(self, user_id: str) -> dict:
        """
        Elimina el perfil del usuario completamente:
        0. Valida precondiciones para limpieza de avatar privado
        1. Elimina de la tabla 'usuarios' (base de datos pública)
        2. Elimina de Supabase Auth (obligatorio)
        3. Elimina avatar personalizado del bucket privado (si existía)
        Si Auth falla, restaura la fila en `usuarios`.
        """
        try:
            perfil = self._obtener_usuario_or_404(user_id)

            avatar_to_delete = None
            if perfil.foto_perfil and self.storage_service.is_managed_avatar(perfil.foto_perfil):
                # Precondición estricta: si hay avatar gestionado, debe existir cliente admin.
                if not self.storage_service.storage_client:
                    raise HTTPException(
                        status_code=500,
                        detail="No se puede eliminar la cuenta sin SUPABASE_SERVICE_ROLE_KEY (avatar privado).",
                    )
                avatar_to_delete = perfil.foto_perfil

            # Primero eliminar en tabla pública.
            self.usuario_dao.eliminar_perfil(user_id)

            # Después eliminar en Supabase Auth.
            supabase_admin = get_supabase_admin()
            if not supabase_admin:
                # Compensación: restaura fila si no hay cliente admin disponible.
                self.usuario_dao.restaurar_perfil(perfil)
                raise HTTPException(
                    status_code=500,
                    detail="Cliente admin no disponible. Configura SUPABASE_SERVICE_ROLE_KEY.",
                )

            try:
                supabase_admin.auth.admin.delete_user(user_id)
                print(f"[USER SERVICE] Usuario {user_id} eliminado de Supabase Auth")
            except Exception as auth_error:
                # Compensación: restaurar perfil si falla Auth para no dejar inconsistencia.
                try:
                    self.usuario_dao.restaurar_perfil(perfil)
                except Exception as rollback_error:
                    raise HTTPException(
                        status_code=500,
                        detail=(
                            "Error eliminando en Auth y no se pudo restaurar perfil en BD. "
                            f"auth_error={str(auth_error)}; rollback_error={str(rollback_error)}"
                        ),
                    )

                raise HTTPException(
                    status_code=500,
                    detail=f"No se pudo eliminar el usuario en Supabase Auth: {str(auth_error)}",
                )

            # Solo cuando DB + Auth están eliminados, limpiar archivo de avatar.
            if avatar_to_delete:
                self.storage_service.delete_avatar(user_id, avatar_to_delete)
            
        except Exception as e:
            print(f"[USER SERVICE] Error al eliminar perfil: {str(e)}")
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=500, detail="Ocurrió un error al intentar eliminar el perfil.")
        
        return {
            "status": "exito",
            "mensaje": "Perfil eliminado correctamente. La cuenta no podrá ser recuperada."
        }

    def agregar_avatar(self, user_id: str, file: UploadFile):
        perfil = self._obtener_usuario_or_404(user_id)

        if perfil.foto_perfil and self.storage_service.is_managed_avatar(perfil.foto_perfil):
            raise HTTPException(status_code=409, detail="El usuario ya tiene avatar. Usa PUT para reemplazar")

        avatar_ref = self.storage_service.upload_avatar(user_id, file)
        self.usuario_dao.actualizar_foto_perfil(user_id, avatar_ref)
        return self._obtener_usuario_hidratado_or_500(user_id)

    def actualizar_avatar(self, user_id: str, file: UploadFile):
        perfil = self._obtener_usuario_or_404(user_id)

        old_avatar = perfil.foto_perfil or ""
        new_avatar_ref = self.storage_service.upload_avatar(user_id, file)

        try:
            self.usuario_dao.actualizar_foto_perfil(user_id, new_avatar_ref)
        except Exception:
            # Rollback best-effort: si falla la DB, eliminar el archivo recién subido.
            try:
                self.storage_service.delete_avatar(user_id, new_avatar_ref)
            except Exception:
                pass
            raise HTTPException(status_code=500, detail="No se pudo actualizar el avatar en la base de datos")

        if old_avatar:
            # Eliminación diferida para evitar perder avatar si falla la subida.
            try:
                self.storage_service.delete_avatar(user_id, old_avatar)
            except Exception:
                pass

        return self._obtener_usuario_hidratado_or_500(user_id)

    def eliminar_avatar(self, user_id: str) -> dict:
        perfil = self._obtener_usuario_or_404(user_id)

        if perfil.foto_perfil:
            self.storage_service.delete_avatar(user_id, perfil.foto_perfil)

        self.usuario_dao.actualizar_foto_perfil(user_id, None)
        return {"status": "exito", "mensaje": "Avatar eliminado correctamente"}
