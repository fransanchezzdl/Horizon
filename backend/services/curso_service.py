"""
Servicio de cursos — lógica de negocio.
"""

from typing import Dict, Optional
from fastapi import HTTPException

from ..daos.curso_dao import CursoDAO
from ..dtos.curso_dto import (
    CursoListResponse,
    CursoDetailResponse,
    DiapositivaResponse,
    ProgresoResponse,
)

class CursoService:
    def __init__(self, curso_dao_cls=CursoDAO):
        self.curso_dao = curso_dao_cls

    def listar_cursos_disponibles(self) -> list[CursoListResponse]:
        try:
            cursos = self.curso_dao.listar_cursos()
            if cursos is None:
                raise HTTPException(status_code=500, detail="Error obteniendo cursos")
            return [CursoListResponse(**curso) for curso in cursos]
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail="Error listando cursos")

    def obtener_curso_con_diapositivas(self, id_curso: str) -> CursoDetailResponse:
        try:
            id_curso_int = int(id_curso) # Aseguramos que sea entero
            curso = self.curso_dao.obtener_curso(id_curso_int)
            
            if not curso:
                raise HTTPException(status_code=404, detail="Curso no encontrado")
            
            # ¡Solución aquí! Pydantic parsea las diapositivas anidadas automáticamente
            return CursoDetailResponse(**curso)
            
        except ValueError:
            raise HTTPException(status_code=400, detail="ID de curso inválido")
        except HTTPException:
            raise
        except Exception as e:
            # Ponemos un print para que, si vuelve a fallar, nos diga el motivo exacto
            print(f"[ERROR CRÍTICO] Parseando curso: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail="Error obteniendo curso")

    def obtener_o_crear_progreso(self, user_id: str, id_curso: str) -> ProgresoResponse:
        try:
            id_curso_int = int(id_curso)
            curso = self.curso_dao.obtener_curso(id_curso_int)
            if not curso:
                raise HTTPException(status_code=404, detail="Curso no encontrado")
            
            progreso = self.curso_dao.obtener_progreso(user_id, id_curso_int)
            if not progreso:
                progreso = self.curso_dao.crear_progreso(user_id, id_curso_int)
                if not progreso:
                    raise HTTPException(status_code=500, detail="No se pudo crear progreso")
            
            # Cálculo dinámico del porcentaje de progreso
            diapositivas = curso.get('diapositivas', [])
            total_diapositivas = len(diapositivas) if len(diapositivas) > 0 else 1
            diapositiva_actual = progreso.get("diapositiva_alcanzada", 1)
            
            progreso_porcentaje = (diapositiva_actual / total_diapositivas) * 100
            
            return ProgresoResponse(
                id_usuario=user_id,
                id_curso=id_curso_int,
                diapositiva_alcanzada=diapositiva_actual,
                completado=progreso.get("completado", False),
                progreso_pct=min(progreso_porcentaje, 100.0),
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="ID de curso inválido")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail="Error procesando progreso")

    def avanzar_diapositiva(
        self, user_id: str, id_curso: str, numero_diapositiva: int
    ) -> ProgresoResponse:
        try:
            id_curso_int = int(id_curso)
            curso = self.curso_dao.obtener_curso(id_curso_int)
            if not curso:
                raise HTTPException(status_code=404, detail="Curso no encontrado")
            
            diapositivas = curso.get('diapositivas', [])
            total_diapositivas = len(diapositivas) if len(diapositivas) > 0 else 1
            
            if numero_diapositiva < 1 or numero_diapositiva > total_diapositivas:
                raise HTTPException(status_code=400, detail=f"Diapositiva fuera de rango")
            
            completado = (numero_diapositiva == total_diapositivas)
            
            progreso_actualizado = self.curso_dao.actualizar_progreso(
                id_usuario=user_id,
                id_curso=id_curso_int,
                diapositiva_alcanzada=numero_diapositiva,
                completado=completado,
            )
            
            if not progreso_actualizado:
                raise HTTPException(status_code=500, detail="Fallo al guardar progreso")
            
            progreso_porcentaje = (numero_diapositiva / total_diapositivas) * 100
            
            return ProgresoResponse(
                id_usuario=user_id,
                id_curso=id_curso_int,
                diapositiva_alcanzada=numero_diapositiva,
                completado=completado,
                progreso_pct=min(progreso_porcentaje, 100.0),
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="ID de curso inválido")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail="Error actualizando progreso")
        
    def obtener_resumen_usuario(self, user_id: str) -> dict:
        """Devuelve un resumen general de la academia para el dashboard."""
        try:
            progresos = self.curso_dao.obtener_progresos_usuario(user_id)
            # Sumamos 1 por cada registro que tenga completado == True
            completados = sum(1 for p in progresos if p.get("completado") == True)
            return {"cursos_completados": completados}
            
        except Exception as e:
            print(f"[ERROR] Error en resumen de usuario: {e}")
            return {"cursos_completados": 0}