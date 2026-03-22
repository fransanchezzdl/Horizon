from fastapi import HTTPException
from ..daos.usuario_dao import usuario_dao
from ..dtos.usuario_dto import PerfilUpdateDTO

class UserService:
    """
    Servicio que contiene la lógica de negocio para la gestión de usuarios.
    Actúa como intermediario entre los endpoints (main.py) y el acceso a datos (DAO).
    """

    def actualizar_perfil(self, user_id: str, datos_actualizacion: PerfilUpdateDTO) -> dict:
        # 1. Convertir el DTO validado a un diccionario de Python.
        datos_dict = datos_actualizacion.model_dump(exclude_unset=True)

        # 2. Verificar si hay datos reales para actualizar
        if not datos_dict:
            return {"status": "sin_cambios", "mensaje": "No se enviaron datos nuevos para actualizar."}

        # 3. Extraer los datos y pasárselos a tu DAO existente
        try:
            # Intentamos guardar en la base de datos
            usuario_dao.actualizar_perfil(
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

# Instanciamos el servicio con su nuevo nombre
user_service = UserService()