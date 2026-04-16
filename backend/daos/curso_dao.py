"""
DAO (Data Access Object) para cursos y progreso de usuarios.
"""

from typing import Dict, List, Optional
from ..database import supabase

class CursoDAO:
    
    CURSOS_TABLE = "cursos"
    PROGRESO_TABLE = "progreso_cursos"
    DIAPOSITIVAS_TABLE = "diapositivas"
    
    # ==========================================
    # OPERACIONES CON CURSOS Y DIAPOSITIVAS
    # ==========================================
    
    @staticmethod
    def listar_cursos() -> Optional[List[Dict]]:
        try:
            response = (
                supabase.table(CursoDAO.CURSOS_TABLE)
                .select("id, titulo, descripcion, plan_pro")
                .order("id") # Ordenamos por id por defecto
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            print(f"[ERROR] Error obteniendo cursos: {e}")
            return None
            
    @staticmethod
    def obtener_diapositivas(id_curso: int) -> Optional[List[Dict]]:
        try:
            response = (
                supabase.table(CursoDAO.DIAPOSITIVAS_TABLE)
                .select("*")
                .eq("id_curso", id_curso)
                .order("num_pag")
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            print(f"[ERROR] Error obteniendo diapositivas: {e}")
            return []

    @staticmethod
    def obtener_curso(id_curso: int) -> Optional[Dict]:
        try:
            response = (
                supabase.table(CursoDAO.CURSOS_TABLE)
                .select("id, titulo, descripcion, plan_pro")
                .eq("id", id_curso)
                .execute()
            )
            
            if not response.data:
                return None
                
            curso = response.data[0]
            # Extraemos las diapositivas reales
            curso['diapositivas'] = CursoDAO.obtener_diapositivas(id_curso)
            return curso
        except Exception as e:
            print(f"[ERROR] Error obteniendo curso {id_curso}: {e}")
            return None
    
    # ==========================================
    # OPERACIONES CON PROGRESO
    # ==========================================
    
    @staticmethod
    def obtener_progreso(id_usuario: str, id_curso: int) -> Optional[Dict]:
        try:
            response = (
                supabase.table(CursoDAO.PROGRESO_TABLE)
                .select("*")
                .eq("id_usuario", id_usuario)
                .eq("id_curso", id_curso)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"[ERROR] Error obteniendo progreso: {e}")
            return None
            
    @staticmethod
    def crear_progreso(id_usuario: str, id_curso: int) -> Optional[Dict]:
        try:
            progreso_data = {
                "id_usuario": id_usuario,
                "id_curso": id_curso,
                "diapositiva_alcanzada": 1,
                "completado": False
                # Puntuacion es nula por defecto
            }
            response = (
                supabase.table(CursoDAO.PROGRESO_TABLE)
                .insert(progreso_data)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"[ERROR] Error creando progreso: {e}")
            return None
            
    @staticmethod
    def actualizar_progreso(
        id_usuario: str,
        id_curso: int,
        diapositiva_alcanzada: int,
        completado: bool = False
    ) -> Optional[Dict]:
        try:
            update_data = {
                "diapositiva_alcanzada": diapositiva_alcanzada,
                "completado": completado
            }
            response = (
                supabase.table(CursoDAO.PROGRESO_TABLE)
                .update(update_data)
                .eq("id_usuario", id_usuario)
                .eq("id_curso", id_curso)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"[ERROR] Error actualizando progreso: {e}")
            return None
    
    @staticmethod
    def obtener_progresos_usuario(id_usuario: str) -> list:
        """Obtiene todos los registros de progreso de un usuario."""
        try:
            response = (
                supabase.table(CursoDAO.PROGRESO_TABLE)
                .select("*")
                .eq("id_usuario", id_usuario)
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            print(f"[ERROR] Error obteniendo progresos del usuario: {e}")
            return []