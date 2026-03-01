"""
DAO (Data Access Object) para portfolios.

Responsabilidades:
- CRUD de portfolios
- CRUD de acciones en portfolios
- Consultas de portfolios por usuario
"""

from typing import Dict, List, Optional
from datetime import datetime
from ..database import supabase


class PortfolioDAO:
    """Acceso a datos de portfolios."""
    
    PORTFOLIOS_TABLE = "portfolios"
    PORTFOLIO_STOCKS_TABLE = "portfolio_stocks"
    
    # ==========================================
    # OPERACIONES CON PORTFOLIOS
    # ==========================================
    
    @staticmethod
    def crear(portfolio_data: Dict) -> Optional[str]:
        """
        Crea un nuevo portfolio.
        
        Args:
            portfolio_data: Dict con datos
                - usuario_id: str (UUID)
                - nombre: str
                - descripcion: str (opcional)
                - aversion_riesgo: float (0-1)
                - capital_inicial: float
        
        Returns:
            str: ID del portfolio creado o None
        """
        try:
            response = (
                supabase.table(PortfolioDAO.PORTFOLIOS_TABLE)
                .insert(portfolio_data)
                .execute()
            )
            
            if response.data:
                portfolio_id = response.data[0].get('id')
                print(f"✅ Portfolio {portfolio_id} creado")
                return portfolio_id
            return None
        
        except Exception as e:
            print(f"❌ Error creando portfolio: {e}")
            return None
    
    @staticmethod
    def obtener_por_id(portfolio_id: str) -> Optional[Dict]:
        """
        Obtiene un portfolio por ID.
        
        Args:
            portfolio_id: ID del portfolio
        
        Returns:
            Dict con datos del portfolio o None
        """
        try:
            response = (
                supabase.table(PortfolioDAO.PORTFOLIOS_TABLE)
                .select("*")
                .eq("id", portfolio_id)
                .execute()
            )
            return response.data[0] if response.data else None
        
        except Exception as e:
            print(f"❌ Error obteniendo portfolio: {e}")
            return None
    
    @staticmethod
    def obtener_por_usuario(usuario_id: str) -> Optional[List[Dict]]:
        """
        Obtiene todos los portfolios de un usuario.
        
        Args:
            usuario_id: ID del usuario
        
        Returns:
            Lista de portfolios o None
        """
        try:
            response = (
                supabase.table(PortfolioDAO.PORTFOLIOS_TABLE)
                .select("*")
                .eq("usuario_id", usuario_id)
                .order("created_at", desc=True)
                .execute()
            )
            return response.data if response.data else []
        
        except Exception as e:
            print(f"❌ Error obteniendo portfolios del usuario: {e}")
            return None
    
    @staticmethod
    def actualizar(portfolio_id: str, update_data: Dict) -> bool:
        """
        Actualiza un portfolio existente.
        
        Args:
            portfolio_id: ID del portfolio
            update_data: Dict con campos a actualizar
        
        Returns:
            bool: True si exitoso
        """
        try:
            update_data['updated_at'] = datetime.now().isoformat()
            
            supabase.table(PortfolioDAO.PORTFOLIOS_TABLE).update(
                update_data
            ).eq("id", portfolio_id).execute()
            
            print(f"✅ Portfolio {portfolio_id} actualizado")
            return True
        
        except Exception as e:
            print(f"❌ Error actualizando portfolio: {e}")
            return False
    
    @staticmethod
    def eliminar(portfolio_id: str) -> bool:
        """
        Elimina un portfolio y todas sus acciones.
        
        Nota: Las acciones se eliminan automáticamente por cascade.
        
        Args:
            portfolio_id: ID del portfolio
        
        Returns:
            bool: True si exitoso
        """
        try:
            supabase.table(PortfolioDAO.PORTFOLIOS_TABLE).delete().eq(
                "id", portfolio_id
            ).execute()
            
            print(f"✅ Portfolio {portfolio_id} eliminado")
            return True
        
        except Exception as e:
            print(f"❌ Error eliminando portfolio: {e}")
            return False
    
    # ==========================================
    # OPERACIONES CON ACCIONES EN PORTFOLIO
    # ==========================================
    
    @staticmethod
    def crear_stock(stock_data: Dict) -> Optional[str]:
        """
        Añade una acción al portfolio.
        
        Args:
            stock_data: Dict con datos
                - portfolio_id: str (UUID)
                - ticker: str
                - shares: float
                - buy_price: float
                - buy_date: str (YYYY-MM-DD)
        
        Returns:
            str: ID de la acción o None
        """
        try:
            response = (
                supabase.table(PortfolioDAO.PORTFOLIO_STOCKS_TABLE)
                .insert(stock_data)
                .execute()
            )
            
            if response.data:
                stock_id = response.data[0].get('id')
                print(f"✅ Acción {stock_data['ticker']} añadida al portfolio")
                return stock_id
            return None
        
        except Exception as e:
            print(f"❌ Error creando acción: {e}")
            return None
    
    @staticmethod
    def obtener_stocks(portfolio_id: str) -> List[Dict]:
        """
        Obtiene todas las acciones de un portfolio.
        
        Args:
            portfolio_id: ID del portfolio
        
        Returns:
            Lista de acciones
        """
        try:
            response = (
                supabase.table(PortfolioDAO.PORTFOLIO_STOCKS_TABLE)
                .select("*")
                .eq("portfolio_id", portfolio_id)
                .execute()
            )
            return response.data if response.data else []
        
        except Exception as e:
            print(f"❌ Error obteniendo stocks: {e}")
            return []
    
    @staticmethod
    def obtener_stock(stock_id: str) -> Optional[Dict]:
        """
        Obtiene una acción específica.
        
        Args:
            stock_id: ID de la acción
        
        Returns:
            Dict con datos del stock o None
        """
        try:
            response = (
                supabase.table(PortfolioDAO.PORTFOLIO_STOCKS_TABLE)
                .select("*")
                .eq("id", stock_id)
                .execute()
            )
            return response.data[0] if response.data else None
        
        except Exception as e:
            print(f"❌ Error obteniendo stock: {e}")
            return None
    
    @staticmethod
    def actualizar_stock(stock_id: str, update_data: Dict) -> bool:
        """
        Actualiza una acción.
        
        Args:
            stock_id: ID de la acción
            update_data: Dict con campos a actualizar
        
        Returns:
            bool: True si exitoso
        """
        try:
            supabase.table(PortfolioDAO.PORTFOLIO_STOCKS_TABLE).update(
                update_data
            ).eq("id", stock_id).execute()
            
            print(f"✅ Acción {stock_id} actualizada")
            return True
        
        except Exception as e:
            print(f"❌ Error actualizando stock: {e}")
            return False
    
    @staticmethod
    def eliminar_stock(stock_id: str) -> bool:
        """
        Elimina una acción del portfolio.
        
        Args:
            stock_id: ID de la acción
        
        Returns:
            bool: True si exitoso
        """
        try:
            supabase.table(PortfolioDAO.PORTFOLIO_STOCKS_TABLE).delete().eq(
                "id", stock_id
            ).execute()
            
            print(f"✅ Acción {stock_id} eliminada")
            return True
        
        except Exception as e:
            print(f"❌ Error eliminando stock: {e}")
            return False
    
    # ==========================================
    # MÉTODOS DE UTILIDAD
    # ==========================================
    
    @staticmethod
    def obtener_stocks_por_ticker(portfolio_id: str, ticker: str) -> List[Dict]:
        """
        Obtiene todas las posiciones de un ticker en un portfolio.
        
        (Un usuario podría haber comprado el mismo ticker en diferentes fechas)
        
        Args:
            portfolio_id: ID del portfolio
            ticker: Símbolo
        
        Returns:
            Lista de posiciones
        """
        try:
            response = (
                supabase.table(PortfolioDAO.PORTFOLIO_STOCKS_TABLE)
                .select("*")
                .eq("portfolio_id", portfolio_id)
                .eq("ticker", ticker)
                .execute()
            )
            return response.data if response.data else []
        
        except Exception as e:
            print(f"❌ Error obteniendo stocks por ticker: {e}")
            return []
    
    @staticmethod
    def obtener_tickers_unicos(portfolio_id: str) -> List[str]:
        """
        Obtiene lista de tickers únicos en el portfolio.
        
        Args:
            portfolio_id: ID del portfolio
        
        Returns:
            Lista de tickers
        """
        try:
            stocks = PortfolioDAO.obtener_stocks(portfolio_id)
            tickers = sorted(set(s['ticker'] for s in stocks))
            return tickers
        
        except Exception as e:
            print(f"❌ Error obteniendo tickers únicos: {e}")
            return []


# Instancia global
portfolio_dao = PortfolioDAO()
