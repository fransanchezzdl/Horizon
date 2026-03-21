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
    PORTFOLIO_STOCKS_TABLE = "portfolio_activo"
    
    # ==========================================
    # OPERACIONES CON PORTFOLIOS
    # ==========================================
    
    @staticmethod
    def crear(portfolio_data: Dict) -> Optional[int]:
        """
        Crea un nuevo portfolio usando INSERT y registra la relación en usuarios_portfolios.
        
        Args:
            portfolio_data: Dict con datos
                - id_usuario: str (UUID)
                - nombre_portfolio: str
                - descripcion: str (opcional)
                - riesgo: float (0-1)
        
        Returns:
            int: ID del portfolio creado o None
        """
        try:
            # Asegurar timestamps
            if "created_at" not in portfolio_data:
                portfolio_data["created_at"] = datetime.now().isoformat()
            if "updated_at" not in portfolio_data:
                portfolio_data["updated_at"] = datetime.now().isoformat()
            
            # INSERT para crear nuevo portfolio (no UPSERT, porque id_portfolio es autoincrement)
            response = (
                supabase.table(PortfolioDAO.PORTFOLIOS_TABLE)
                .insert(portfolio_data)
                .execute()
            )
            
            print(f"📤 INSERT Response: {response.data}")
            
            if response.data:
                portfolio_id = response.data[0].get('id_portfolio')
                id_usuario = response.data[0].get('id_usuario')
                
                # Guardar la relación en usuarios_portfolios
                try:
                    relacion = {
                        "id_usuario": id_usuario,
                        "id_portfolio": portfolio_id,
                        "created_at": datetime.now().isoformat()
                    }
                    
                    relacion_response = (
                        supabase.table("usuarios_portfolios")
                        .insert(relacion)
                        .execute()
                    )
                    
                    print(f"✅ Relación guardada en usuarios_portfolios: {relacion_response.data}")
                    
                except Exception as e:
                    print(f"⚠️  Advertencia: No se pudo guardar relación en usuarios_portfolios: {e}")
                    # No lanzamos error aquí, el portfolio ya se creó
                
                print(f"✅ Portfolio {portfolio_id} creado para usuario {id_usuario}")
                return portfolio_id
            return None
        
        except Exception as e:
            print(f"❌ Error creando portfolio: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def obtener_por_id(portfolio_id: int) -> Optional[Dict]:
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
                .eq("id_portfolio", portfolio_id)
                .execute()
            )
            
            print(f"🔍 SELECT portfolios WHERE id_portfolio={portfolio_id}")
            print(f"📥 Response: {response.data}")
            
            portfolio = response.data[0] if response.data else None
            
            if portfolio:
                print(f"✅ Portfolio encontrado: {portfolio}")
            else:
                print(f"❌ Portfolio {portfolio_id} no encontrado en BD")
            
            return portfolio
        
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
                .eq("id_usuario", usuario_id)
                .order("created_at", desc=True)
                .execute()
            )
            
            print(f"🔍 SELECT portfolios WHERE id_usuario='{usuario_id}'")
            print(f"📥 Response: Encontrados {len(response.data) if response.data else 0} portfolios")
            if response.data:
                print(f"   Datos: {response.data}")
            
            return response.data if response.data else []
        
        except Exception as e:
            print(f"❌ Error obteniendo portfolios del usuario: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def actualizar(portfolio_id: int, update_data: Dict) -> bool:
        """
        Actualiza un portfolio existente usando UPDATE.
        
        Args:
            portfolio_id: ID del portfolio
            update_data: Dict con campos a actualizar
        
        Returns:
            bool: True si exitoso
        """
        try:
            update_data['updated_at'] = datetime.now().isoformat()
            
            # UPDATE para modificar un portfolio existente
            response = (
                supabase.table(PortfolioDAO.PORTFOLIOS_TABLE)
                .update(update_data)
                .eq("id_portfolio", portfolio_id)
                .execute()
            )
            
            print(f"✅ Portfolio {portfolio_id} actualizado")
            return response.data and len(response.data) > 0
        
        except Exception as e:
            print(f"❌ Error actualizando portfolio: {e}")
            return False
    
    @staticmethod
    def eliminar(portfolio_id: int) -> bool:
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
                "id_portfolio", portfolio_id
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
    def crear_stock(stock_data: Dict) -> Optional[int]:
        """
        Añade una acción al portfolio usando INSERT.
        
        Args:
            stock_data: Dict con datos
                - id_portfolio: int
                - ticker: str
        
        Returns:
            int: ID de la posición o None
        """
        try:
            payload = {
                "id_portfolio": stock_data.get("id_portfolio") or stock_data.get("portfolio_id"),
                "ticker": stock_data.get("ticker"),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }

            # INSERT para crear nueva posición (no UPSERT, porque id_posicion es autoincrement)
            response = (
                supabase.table(PortfolioDAO.PORTFOLIO_STOCKS_TABLE)
                .insert(payload)
                .execute()
            )
            
            if response.data:
                stock_id = response.data[0].get('id_posicion')
                print(f"✅ Activo {payload['ticker']} añadido al portfolio {payload['id_portfolio']}")
                return stock_id
            return None
        
        except Exception as e:
            print(f"❌ Error creando acción: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def obtener_stocks(portfolio_id: int) -> List[Dict]:
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
                .eq("id_portfolio", portfolio_id)
                .execute()
            )
            return response.data if response.data else []
        
        except Exception as e:
            print(f"❌ Error obteniendo stocks: {e}")
            return []
    
    @staticmethod
    def obtener_stock(stock_id: int) -> Optional[Dict]:
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
                .eq("id_posicion", stock_id)
                .execute()
            )
            return response.data[0] if response.data else None
        
        except Exception as e:
            print(f"❌ Error obteniendo stock: {e}")
            return None
    
    @staticmethod
    def actualizar_stock(stock_id: int, update_data: Dict) -> bool:
        """
        Actualiza una acción.
        
        Args:
            stock_id: ID de la acción
            update_data: Dict con campos a actualizar
        
        Returns:
            bool: True si exitoso
        """
        try:
            if "portfolio_id" in update_data:
                update_data["id_portfolio"] = update_data.pop("portfolio_id")
            supabase.table(PortfolioDAO.PORTFOLIO_STOCKS_TABLE).update(
                update_data
            ).eq("id_posicion", stock_id).execute()
            
            print(f"✅ Acción {stock_id} actualizada")
            return True
        
        except Exception as e:
            print(f"❌ Error actualizando stock: {e}")
            return False
    
    @staticmethod
    def eliminar_stock(stock_id: int) -> bool:
        """
        Elimina una acción del portfolio.
        
        Args:
            stock_id: ID de la acción
        
        Returns:
            bool: True si exitoso
        """
        try:
            supabase.table(PortfolioDAO.PORTFOLIO_STOCKS_TABLE).delete().eq(
                "id_posicion", stock_id
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
    def obtener_stocks_por_ticker(portfolio_id: int, ticker: str) -> List[Dict]:
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
                .eq("id_portfolio", portfolio_id)
                .eq("ticker", ticker)
                .execute()
            )
            return response.data if response.data else []
        
        except Exception as e:
            print(f"❌ Error obteniendo stocks por ticker: {e}")
            return []
    
    @staticmethod
    def obtener_tickers_unicos(portfolio_id: int) -> List[str]:
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
