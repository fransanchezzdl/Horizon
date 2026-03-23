from fastapi import HTTPException
from ..dtos.usuario_dto import PerfilUpdateDTO
from ..database import supabase, get_supabase_admin

class UserService:
    """
    Servicio que contiene la lógica de negocio para la gestión de usuarios.
    Actúa como intermediario entre los endpoints (main.py) y el acceso a datos (DAO).
    """

    def __init__(self, usuario_dao_instance):
        self.usuario_dao = usuario_dao_instance

    def actualizar_perfil(self, user_id: str, datos_actualizacion: PerfilUpdateDTO) -> dict:
        # 1. Convertir el DTO validado a un diccionario de Python.
        datos_dict = datos_actualizacion.model_dump(exclude_unset=True)

        # 2. Verificar si hay datos reales para actualizar
        if not datos_dict:
            return {"status": "sin_cambios", "mensaje": "No se enviaron datos nuevos para actualizar."}

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
        1. Elimina de la tabla 'usuarios' (base de datos pública)
        2. Elimina de Supabase Auth (si está disponible el cliente admin)
        """
        try:
            # Primero eliminar de la tabla usuarios
            self.usuario_dao.eliminar_perfil(user_id)
            
            # Luego eliminar de Supabase Auth usando cliente admin
            supabase_admin = get_supabase_admin()
            if supabase_admin:
                try:
                    supabase_admin.auth.admin.delete_user(user_id)
                    print(f"[USER SERVICE] Usuario {user_id} eliminado de Supabase Auth")
                except Exception as auth_error:
                    print(f"[USER SERVICE] Advertencia al eliminar de Auth: {str(auth_error)}")
                    # Continuamos aunque falle Auth, ya eliminamos de la tabla
            else:
                print("[USER SERVICE] Cliente admin no disponible. Asegúrate de configurar SUPABASE_SERVICE_ROLE_KEY")
            
        except Exception as e:
            print(f"[USER SERVICE] Error al eliminar perfil: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Ocurrió un error al intentar eliminar el perfil."
            )
        
        return {
            "status": "exito",
            "mensaje": "Perfil eliminado correctamente. La cuenta no podrá ser recuperada."
        }
