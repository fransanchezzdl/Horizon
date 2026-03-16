"""
DAO (Data Access Object) para histórico de activos.

Responsabilidades:
- CRUD de registros históricos de activos
- Búsqueda de históricos por ticker y fecha
- Consultas de series históricas para análisis
"""

from typing import Dict, List, Optional
from datetime import date, datetime, timedelta
from ..database import supabase
from ..dtos import HistoricoActivoResponse


class HistoricoActivoDAO:
    """Acceso a datos del histórico de activos."""
    
    TABLE = "historico_activos"
    
    # ==========================================
    # OPERACIONES CRUD
    # ==========================================
    
    @staticmethod
    def crear(historico_data: Dict) -> Optional[int]:
        """
        Crea un nuevo registro histórico.
        
        Args:
            historico_data: Dict con datos
                - ticker: str (FK a activos)
                - fecha: date
                - precio_cierre: float
                - prediccion_ia: float (opcional)
        
        Returns:
            int: ID del histórico creado o None
        """
        try:
            if "ticker" not in historico_data or "fecha" not in historico_data or "precio_cierre" not in historico_data:
                print("❌ Error: ticker, fecha y precio_cierre son requeridos")
                return None
            
            # Convertir date a string si es necesario
            if isinstance(historico_data.get("fecha"), date):
                historico_data["fecha"] = historico_data["fecha"].isoformat()
            
            response = (
                supabase.table(HistoricoActivoDAO.TABLE)
                .insert(historico_data)
                .execute()
            )
            
            if response.data:
                id_historico = response.data[0].get("id_historico")
                print(f"✅ Histórico {id_historico} creado para {historico_data.get('ticker')}")
                return id_historico
            return None
        
        except Exception as e:
            print(f"❌ Error creando histórico: {e}")
            return None
    
    @staticmethod
    def obtener_por_id(id_historico: int) -> Optional[HistoricoActivoResponse]:
        """
        Obtiene un registro histórico por ID.
        
        Args:
            id_historico: ID del histórico
        
        Returns:
            HistoricoActivoResponse o None
        """
        try:
            response = (
                supabase.table(HistoricoActivoDAO.TABLE)
                .select("*")
                .eq("id_historico", id_historico)
                .execute()
            )
            
            if response.data and len(response.data) > 0:
                return HistoricoActivoResponse(**response.data[0])
            return None
        
        except Exception as e:
            print(f"❌ Error obteniendo histórico {id_historico}: {e}")
            return None
    
    @staticmethod
    def obtener_por_ticker(ticker: str, limit: int = None, offset: int = 0) -> List[HistoricoActivoResponse]:
        """
        Obtiene todos los registros históricos de un ticker.
        
        Args:
            ticker: Símbolo del ticker
            limit: Máximo número de resultados (None = sin límite)
            offset: Número de registros a saltar
        
        Returns:
            Lista de HistoricoActivoResponse
        """
        try:
            query = (
                supabase.table(HistoricoActivoDAO.TABLE)
                .select("*")
                .eq("ticker", ticker)
                .order("fecha", desc=True)
            )
            
            if limit:
                query = query.limit(limit).offset(offset)
            
            response = query.execute()
            
            if response.data:
                return [HistoricoActivoResponse(**item) for item in response.data]
            return []
        
        except Exception as e:
            print(f"❌ Error obteniendo histórico de {ticker}: {e}")
            return []
    
    @staticmethod
    def obtener_por_ticker_y_fecha(ticker: str, fecha_inicio: date, fecha_fin: date) -> List[HistoricoActivoResponse]:
        """
        Obtiene registros históricos de un ticker en un rango de fechas.
        
        Args:
            ticker: Símbolo del ticker
            fecha_inicio: Fecha de inicio (inclusive)
            fecha_fin: Fecha de fin (inclusive)
        
        Returns:
            Lista de HistoricoActivoResponse
        """
        try:
            response = (
                supabase.table(HistoricoActivoDAO.TABLE)
                .select("*")
                .eq("ticker", ticker)
                .gte("fecha", fecha_inicio.isoformat())
                .lte("fecha", fecha_fin.isoformat())
                .order("fecha", desc=True)
                .execute()
            )
            
            if response.data:
                return [HistoricoActivoResponse(**item) for item in response.data]
            return []
        
        except Exception as e:
            print(f"❌ Error obteniendo histórico de {ticker} en rango: {e}")
            return []
    
    @staticmethod
    def obtener_ultimos_dias(ticker: str, dias: int = 30) -> List[HistoricoActivoResponse]:
        """
        Obtiene los últimos N días de datos históricos.
        
        Args:
            ticker: Símbolo del ticker
            dias: Número de días atrás (default 30)
        
        Returns:
            Lista de HistoricoActivoResponse
        """
        try:
            fecha_inicio = date.today() - timedelta(days=dias)
            
            response = (
                supabase.table(HistoricoActivoDAO.TABLE)
                .select("*")
                .eq("ticker", ticker)
                .gte("fecha", fecha_inicio.isoformat())
                .order("fecha", desc=True)
                .execute()
            )
            
            if response.data:
                return [HistoricoActivoResponse(**item) for item in response.data]
            return []
        
        except Exception as e:
            print(f"❌ Error obteniendo últimos {dias} días de {ticker}: {e}")
            return []
    
    @staticmethod
    def actualizar(id_historico: int, update_data: Dict) -> bool:
        """
        Actualiza un registro histórico.
        
        Args:
            id_historico: ID del histórico
            update_data: Dict con campos a actualizar
        
        Returns:
            bool: True si exitoso
        """
        try:
            response = (
                supabase.table(HistoricoActivoDAO.TABLE)
                .update(update_data)
                .eq("id_historico", id_historico)
                .execute()
            )
            
            if response.data:
                print(f"✅ Histórico {id_historico} actualizado")
                return True
            return False
        
        except Exception as e:
            print(f"❌ Error actualizando histórico {id_historico}: {e}")
            return False
    
    @staticmethod
    def eliminar(id_historico: int) -> bool:
        """
        Elimina un registro histórico.
        
        Args:
            id_historico: ID del histórico
        
        Returns:
            bool: True si exitoso
        """
        try:
            response = (
                supabase.table(HistoricoActivoDAO.TABLE)
                .delete()
                .eq("id_historico", id_historico)
                .execute()
            )
            
            if response.data or response.status_code == 204:
                print(f"✅ Histórico {id_historico} eliminado")
                return True
            return False
        
        except Exception as e:
            print(f"❌ Error eliminando histórico {id_historico}: {e}")
            return False
    
    @staticmethod
    def eliminar_por_ticker(ticker: str) -> bool:
        """
        Elimina todos los registros históricos de un ticker.
        
        Nota: Útil al eliminar un activo.
        
        Args:
            ticker: Símbolo del ticker
        
        Returns:
            bool: True si exitoso
        """
        try:
            response = (
                supabase.table(HistoricoActivoDAO.TABLE)
                .delete()
                .eq("ticker", ticker)
                .execute()
            )
            
            print(f"✅ Históricos de {ticker} eliminados")
            return True
        
        except Exception as e:
            print(f"❌ Error eliminando históricos de {ticker}: {e}")
            return False
    
    # ==========================================
    # CONSULTAS ANALÍTICAS
    # ==========================================
    
    @staticmethod
    def obtener_precio_promedio(ticker: str, dias: int = 30) -> Optional[float]:
        """
        Calcula el precio promedio de cierre de los últimos N días.
        
        Args:
            ticker: Símbolo del ticker
            dias: Número de días a considerar
        
        Returns:
            float: Precio promedio o None
        """
        try:
            historicos = HistoricoActivoDAO.obtener_ultimos_dias(ticker, dias)
            
            if not historicos:
                return None
            
            precios = [h.precio_cierre for h in historicos]
            promedio = sum(precios) / len(precios)
            
            return round(promedio, 2)
        
        except Exception as e:
            print(f"❌ Error calculando precio promedio de {ticker}: {e}")
            return None
    
    @staticmethod
    def obtener_minimo_maximo(ticker: str, dias: int = 30) -> Optional[Dict]:
        """
        Obtiene el precio mínimo y máximo de los últimos N días.
        
        Args:
            ticker: Símbolo del ticker
            dias: Número de días a considerar
        
        Returns:
            Dict con claves 'minimo' y 'maximo' o None
        """
        try:
            historicos = HistoricoActivoDAO.obtener_ultimos_dias(ticker, dias)
            
            if not historicos:
                return None
            
            precios = [h.precio_cierre for h in historicos]
            
            return {
                "minimo": min(precios),
                "maximo": max(precios),
                "rango": max(precios) - min(precios)
            }
        
        except Exception as e:
            print(f"❌ Error calculando mín/máx de {ticker}: {e}")
            return None
    
    @staticmethod
    def contar_por_ticker(ticker: str) -> int:
        """
        Cuenta el total de registros históricos de un ticker.
        
        Args:
            ticker: Símbolo del ticker
        
        Returns:
            int: Total de registros
        """
        try:
            response = (
                supabase.table(HistoricoActivoDAO.TABLE)
                .select("id_historico", count="exact")
                .eq("ticker", ticker)
                .execute()
            )
            
            return response.count if hasattr(response, "count") else 0
        
        except Exception as e:
            print(f"❌ Error contando históricos de {ticker}: {e}")
            return 0


# Instancia global del DAO para uso en servicios y rutas
historico_dao = HistoricoActivoDAO()
