"""
DAO (Data Access Object) para activos.

Responsabilidades:
- CRUD de activos
- Búsqueda de activos por criterios
- Actualización de datos de activos (precio, señal IA, etc.)
- Consultas de activos activos y su estado
"""

from typing import Dict, List, Optional
from datetime import datetime
from ..database import supabase
from ..dtos import ActivoResponse


class ActivoDAO:
    """Acceso a datos de activos."""
    
    TABLE = "activos"
    
    # ==========================================
    # OPERACIONES CRUD
    # ==========================================
    
    @staticmethod
    def crear(activo_data: Dict) -> Optional[str]:
        """
        Crea un nuevo activo.
        
        Args:
            activo_data: Dict con datos
                - ticker: str (PK)
                - nombre_completo: str
                - estabilidad: bool (opcional)
                - logo_activo: str (opcional)
                - precio: float (opcional)
                - confianza_bygru: float (opcional, 0-1)
                - senal_ia: str (opcional, ALCISTA/BAJISTA/LATERAL)
                - grafico_prediccion: dict (opcional)
                - noticias: dict (opcional)
        
        Returns:
            str: Ticker del activo creado o None
        """
        try:
            # Asegurar que tiene campos obligatorios
            if "ticker" not in activo_data or "nombre_completo" not in activo_data:
                print("❌ Error: ticker y nombre_completo son requeridos")
                return None
            
            response = (
                supabase.table(ActivoDAO.TABLE)
                .insert(activo_data)
                .execute()
            )
            
            if response.data:
                ticker = activo_data.get("ticker")
                print(f"✅ Activo {ticker} creado")
                return ticker
            return None
        
        except Exception as e:
            print(f"❌ Error creando activo: {e}")
            return None
    
    @staticmethod
    def obtener_por_ticker(ticker: str) -> Optional[ActivoResponse]:
        """
        Obtiene un activo por su ticker.
        
        Args:
            ticker: Símbolo del ticker
        
        Returns:
            ActivoResponse o None
        """
        try:
            response = (
                supabase.table(ActivoDAO.TABLE)
                .select("*")
                .eq("ticker", ticker)
                .execute()
            )
            
            if response.data and len(response.data) > 0:
                return ActivoResponse(**response.data[0])
            return None
        
        except Exception as e:
            print(f"❌ Error obteniendo activo {ticker}: {e}")
            return None
    
    @staticmethod
    def obtener_todos(limit: int = None, offset: int = 0) -> List[ActivoResponse]:
        """
        Obtiene todos los activos.
        
        Args:
            limit: Máximo número de resultados (None = sin límite)
            offset: Número de registros a saltar
        
        Returns:
            Lista de ActivoResponse
        """
        try:
            query = supabase.table(ActivoDAO.TABLE).select("*").order("updated_at", desc=True)
            
            if limit:
                query = query.limit(limit).offset(offset)
            
            response = query.execute()
            
            if response.data:
                return [ActivoResponse(**item) for item in response.data]
            return []
        
        except Exception as e:
            print(f"❌ Error obteniendo activos: {e}")
            return []
    
    @staticmethod
    def buscar_por_nombre(nombre: str) -> List[ActivoResponse]:
        """
        Busca activos por nombre (búsqueda parcial, case-insensitive).
        
        Args:
            nombre: Parte del nombre a buscar
        
        Returns:
            Lista de ActivoResponse
        """
        try:
            # Usar ilike para búsqueda case-insensitive con patrones
            response = (
                supabase.table(ActivoDAO.TABLE)
                .select("*")
                .ilike("nombre_completo", f"%{nombre}%")
                .order("nombre_completo", desc=False)
                .execute()
            )
            
            if response.data:
                return [ActivoResponse(**item) for item in response.data]
            return []
        
        except Exception as e:
            print(f"❌ Error buscando activos por nombre: {e}")
            return []
    
    @staticmethod
    def obtener_con_senal_ia() -> List[ActivoResponse]:
        """
        Obtiene todos los activos que tienen señal de IA.
        
        Returns:
            Lista de ActivoResponse
        """
        try:
            response = (
                supabase.table(ActivoDAO.TABLE)
                .select("*")
                .not_.is_("senal_ia", None)
                .order("updated_at", desc=True)
                .execute()
            )
            
            if response.data:
                return [ActivoResponse(**item) for item in response.data]
            return []
        
        except Exception as e:
            print(f"❌ Error obteniendo activos con señal IA: {e}")
            return []
    
    @staticmethod
    def obtener_por_senal(senal: str) -> List[ActivoResponse]:
        """
        Obtiene activos filtrados por señal de IA.
        
        Args:
            senal: ALCISTA, BAJISTA o LATERAL
        
        Returns:
            Lista de ActivoResponse
        """
        try:
            if senal not in ["ALCISTA", "BAJISTA", "LATERAL"]:
                print(f"❌ Señal inválida: {senal}")
                return []
            
            response = (
                supabase.table(ActivoDAO.TABLE)
                .select("*")
                .eq("senal_ia", senal)
                .order("confianza_bygru", desc=True)
                .execute()
            )
            
            if response.data:
                return [ActivoResponse(**item) for item in response.data]
            return []
        
        except Exception as e:
            print(f"❌ Error obteniendo activos por señal: {e}")
            return []
    
    @staticmethod
    def actualizar(ticker: str, update_data: Dict) -> bool:
        """
        Actualiza un activo existente.
        
        Args:
            ticker: Símbolo del ticker
            update_data: Dict con campos a actualizar
        
        Returns:
            bool: True si exitoso
        """
        try:
            # Siempre actualizar el timestamp
            update_data["updated_at"] = datetime.now().isoformat()
            
            response = (
                supabase.table(ActivoDAO.TABLE)
                .update(update_data)
                .eq("ticker", ticker)
                .execute()
            )
            
            if response.data:
                print(f"✅ Activo {ticker} actualizado")
                return True
            return False
        
        except Exception as e:
            print(f"❌ Error actualizando activo {ticker}: {e}")
            return False
    
    @staticmethod
    def actualizar_precio(ticker: str, precio: float) -> bool:
        """
        Actualiza el precio de un activo.
        
        Args:
            ticker: Símbolo del ticker
            precio: Nuevo precio
        
        Returns:
            bool: True si exitoso
        """
        try:
            return ActivoDAO.actualizar(ticker, {"precio": precio})
        
        except Exception as e:
            print(f"❌ Error actualizando precio de {ticker}: {e}")
            return False
    
    @staticmethod
    def actualizar_senal_ia(ticker: str, senal: str, confianza: float = None) -> bool:
        """
        Actualiza la señal de IA y confianza de un activo.
        
        Args:
            ticker: Símbolo del ticker
            senal: ALCISTA, BAJISTA o LATERAL
            confianza: Valor de confianza (0-1)
        
        Returns:
            bool: True si exitoso
        """
        try:
            if senal not in [None, "ALCISTA", "BAJISTA", "LATERAL"]:
                print(f"❌ Señal inválida: {senal}")
                return False
            
            update_data = {"senal_ia": senal}
            if confianza is not None:
                update_data["confianza_bygru"] = confianza
            
            return ActivoDAO.actualizar(ticker, update_data)
        
        except Exception as e:
            print(f"❌ Error actualizando señal IA de {ticker}: {e}")
            return False
    
    @staticmethod
    def actualizar_noticias(ticker: str, noticias: dict) -> bool:
        """
        Actualiza las noticias de un activo.
        
        Args:
            ticker: Símbolo del ticker
            noticias: Dict con datos de noticias
        
        Returns:
            bool: True si exitoso
        """
        try:
            return ActivoDAO.actualizar(ticker, {"noticias": noticias})
        
        except Exception as e:
            print(f"❌ Error actualizando noticias de {ticker}: {e}")
            return False
    
    @staticmethod
    def actualizar_grafico(ticker: str, grafico_data: dict) -> bool:
        """
        Actualiza el gráfico de predicción de un activo.
        
        Args:
            ticker: Símbolo del ticker
            grafico_data: Dict con datos del gráfico
        
        Returns:
            bool: True si exitoso
        """
        try:
            return ActivoDAO.actualizar(ticker, {"grafico_prediccion": grafico_data})
        
        except Exception as e:
            print(f"❌ Error actualizando gráfico de {ticker}: {e}")
            return False
    
    @staticmethod
    def eliminar(ticker: str) -> bool:
        """
        Elimina un activo.
        
        Nota: Esto también eliminará referencias en historico_activos y 
        portfolio_activo (si hay foreign keys con ON DELETE CASCADE).
        
        Args:
            ticker: Símbolo del ticker
        
        Returns:
            bool: True si exitoso
        """
        try:
            response = (
                supabase.table(ActivoDAO.TABLE)
                .delete()
                .eq("ticker", ticker)
                .execute()
            )
            
            if response.data or response.status_code == 204:
                print(f"✅ Activo {ticker} eliminado")
                return True
            return False
        
        except Exception as e:
            print(f"❌ Error eliminando activo {ticker}: {e}")
            return False
    
    # ==========================================
    # CONSULTAS ESPECIALES
    # ==========================================
    
    @staticmethod
    def obtener_mas_confiables(limit: int = 10) -> List[ActivoResponse]:
        """
        Obtiene los activos más confiables según confianza_bygru.
        
        Args:
            limit: Número de resultados (default 10)
        
        Returns:
            Lista de ActivoResponse ordenados por confianza descendente
        """
        try:
            response = (
                supabase.table(ActivoDAO.TABLE)
                .select("*")
                .not_.is_("confianza_bygru", None)
                .order("confianza_bygru", desc=True)
                .limit(limit)
                .execute()
            )
            
            if response.data:
                return [ActivoResponse(**item) for item in response.data]
            return []
        
        except Exception as e:
            print(f"❌ Error obteniendo activos más confiables: {e}")
            return []
    
    @staticmethod
    def contar_total() -> int:
        """
        Cuenta el total de activos en la base de datos.
        
        Returns:
            int: Total de activos
        """
        try:
            response = (
                supabase.table(ActivoDAO.TABLE)
                .select("ticker", count="exact")
                .execute()
            )
            
            return response.count if hasattr(response, "count") else 0
        
        except Exception as e:
            print(f"❌ Error contando activos: {e}")
            return 0


# Instancia global del DAO para uso en servicios y rutas
activo_dao = ActivoDAO()
