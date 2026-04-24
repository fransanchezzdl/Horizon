"""
DAO para tabla explicaciones_xai
=================================

Operaciones CRUD para explicaciones XAI
"""

import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ExplicacionXAIDAO:
    """
    Data Access Object para explicaciones_xai.
    
    Métodos CRUD:
    - crear(explicacion_dict) -> bool
    - obtener_por_id(id_explicacion) -> dict
    - obtener_por_ticker(ticker, limit=1) -> list
    - obtener_historial(ticker, dias=30) -> list
    - actualizar(id_explicacion, campos_a_actualizar) -> bool
    - eliminar(id_explicacion) -> bool
    - obtener_estadisticas(ticker) -> dict
    """
    
    @staticmethod
    def _get_supabase_client():
        """Obtiene cliente Supabase."""
        import os
        from dotenv import load_dotenv
        from supabase import create_client
        
        load_dotenv()
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_KEY")
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    
    @staticmethod
    def crear(
        ticker: str,
        shap_valores: List[Dict],
        shap_grafico: str,
        features_top20: List[Dict],
        contribucion_features: Dict,
        senal_prediccion: str,
        confianza_prediccion: float,
        version_modelo: str = "Phase3",
        seed_modelo: int = 42,
        pesos_atencion: Optional[List[Dict]] = None,
        fecha_prediccion: Optional[str] = None,
    ) -> bool:
        """
        Crea nueva explicación XAI.

        Args:
            ticker: Ticker del activo
            shap_valores: Lista de {feature_name, shap_value, feature_value, shap_abs}
            shap_grafico: Base64 encoded PNG
            features_top20: Lista de {feature_name, importancia, valor}
            contribucion_features: Dict {feature_name: contribution_value}
            senal_prediccion: 'ALCISTA', 'BAJISTA' o 'LATERAL'
            confianza_prediccion: Float 0-1
            version_modelo: Versión del modelo
            seed_modelo: Seed usado en entrenamiento
            pesos_atencion: Ignorado (columna eliminada de BD)

        Returns:
            True si exitoso
        """
        try:
            supabase = ExplicacionXAIDAO._get_supabase_client()

            registro = {
                "ticker": ticker,
                "fecha_prediccion": fecha_prediccion or datetime.now().isoformat(),
                "shap_valores": json.dumps(shap_valores),
                "shap_grafico": shap_grafico,
                "features_top20": json.dumps(features_top20),
                "contribucion_features": json.dumps(contribucion_features),
                "senal_prediccion": senal_prediccion,
                "confianza_prediccion": float(confianza_prediccion),
                "version_modelo": version_modelo,
                "seed_modelo": seed_modelo,
                "prediccion_correcta": None,
            }
            
            response = supabase.table("xai_explicaciones").insert(registro).execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"✅ Explicación creada para {ticker}")
                return True
            else:
                logger.error(f"❌ Error al crear explicación para {ticker}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Error en ExplicacionXAIDAO.crear: {e}")
            return False
    
    @staticmethod
    def obtener_por_id(id_explicacion: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene explicación por ID.
        
        Args:
            id_explicacion: ID de explicación
        
        Returns:
            Dict con explicación, None si no existe
        """
        try:
            supabase = ExplicacionXAIDAO._get_supabase_client()
            
            response = supabase.table("xai_explicaciones")\
                .select("*")\
                .eq("id", id_explicacion)\
                .single()\
                .execute()
            
            if response.data:
                exp = response.data
                # Deserealizar JSON
                exp["shap_valores"] = json.loads(exp.get("shap_valores", "[]"))
                exp["features_top20"] = json.loads(exp.get("features_top20", "[]"))
                exp["contribucion_features"] = json.loads(exp.get("contribucion_features", "{}"))
                
                return exp
            else:
                return None
        
        except Exception as e:
            logger.error(f"❌ Error en ExplicacionXAIDAO.obtener_por_id: {e}")
            return None
    
    @staticmethod
    def obtener_por_ticker(
        ticker: str,
        limit: int = 1,
        dias: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtiene explicaciones por ticker.
        
        Args:
            ticker: Ticker del activo
            limit: Número máximo de resultados
            dias: Si especificado, solo últimos N días
        
        Returns:
            Lista de explicaciones
        """
        try:
            supabase = ExplicacionXAIDAO._get_supabase_client()
            
            query = supabase.table("xai_explicaciones")\
                .select("*")\
                .eq("ticker", ticker)
            
            # Filtrar por fecha si se especifica
            if dias:
                fecha_inicio = (datetime.now() - timedelta(days=dias)).isoformat()
                query = query.gte("fecha_prediccion", fecha_inicio)
            
            # Orden descendente (más recientes primero)
            query = query.order("fecha_prediccion", desc=True)
            
            # Limite
            if limit:
                query = query.limit(limit)
            
            response = query.execute()
            
            if response.data:
                # Deserealizar JSON en cada registro
                for exp in response.data:
                    exp["shap_valores"] = json.loads(exp.get("shap_valores", "[]"))
                    exp["features_top20"] = json.loads(exp.get("features_top20", "[]"))
                    exp["contribucion_features"] = json.loads(exp.get("contribucion_features", "{}"))
                
                logger.info(f"✓ Obtenidas {len(response.data)} explicaciones para {ticker}")
                return response.data
            else:
                return []
        
        except Exception as e:
            logger.error(f"❌ Error en ExplicacionXAIDAO.obtener_por_ticker: {e}")
            return []
    
    @staticmethod
    def obtener_historial(ticker: str, dias: int = 30) -> List[Dict[str, Any]]:
        """
        Alias para obtener_por_ticker con todos los registros de los últimos días.
        """
        return ExplicacionXAIDAO.obtener_por_ticker(ticker, limit=None, dias=dias)
    
    @staticmethod
    def actualizar(
        id_explicacion: int,
        prediccion_correcta: Optional[bool] = None,
        comentario_validacion: Optional[str] = None
    ) -> bool:
        """
        Actualiza explicación (principalmente para marcar si fué correcta).
        
        Args:
            id_explicacion: ID de explicación
            prediccion_correcta: TRUE/FALSE si la predicción fue correcta
            comentario_validacion: Comentario adicional
        
        Returns:
            True si exitoso
        """
        try:
            supabase = ExplicacionXAIDAO._get_supabase_client()
            
            update_data = {"updated_at": datetime.now().isoformat()}
            
            if prediccion_correcta is not None:
                update_data["prediccion_correcta"] = prediccion_correcta
            
            response = supabase.table("xai_explicaciones")\
                .update(update_data)\
                .eq("id", id_explicacion)\
                .execute()
            
            if response.data:
                logger.info(f"✅ Explicación {id_explicacion} actualizada")
                return True
            else:
                logger.error(f"❌ Error actualizando explicación {id_explicacion}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Error en ExplicacionXAIDAO.actualizar: {e}")
            return False
    
    @staticmethod
    def eliminar(id_explicacion: int) -> bool:
        """
        Elimina una explicación.
        
        Args:
            id_explicacion: ID de explicación
        
        Returns:
            True si exitoso
        """
        try:
            supabase = ExplicacionXAIDAO._get_supabase_client()
            
            response = supabase.table("xai_explicaciones")\
                .delete()\
                .eq("id", id_explicacion)\
                .execute()
            
            logger.info(f"✅ Explicación {id_explicacion} eliminada")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error en ExplicacionXAIDAO.eliminar: {e}")
            return False
    
    @staticmethod
    def obtener_estadisticas(ticker: str, dias: int = 30) -> Dict[str, Any]:
        """
        Obtiene estadísticas de explicaciones para un ticker.
        
        Returns:
        {
            'total_explicaciones': int,
            'explicaciones_correctas': int,
            'tasa_acierto': float,
            'features_mas_frecuentes': [str],
            'senal_distribucion': {ALCISTA: int, ...},
            'confianza_promedio': float,
            'periodo': str
        }
        """
        try:
            explicaciones = ExplicacionXAIDAO.obtener_por_ticker(ticker, limit=None, dias=dias)
            
            if not explicaciones:
                return {
                    "total_explicaciones": 0,
                    "explicaciones_correctas": 0,
                    "tasa_acierto": 0.0,
                    "features_mas_frecuentes": [],
                    "senal_distribucion": {},
                    "confianza_promedio": 0.0
                }
            
            total = len(explicaciones)
            correctas = sum(1 for e in explicaciones if e.get("prediccion_correcta") == True)
            tasa_acierto = (correctas / total) if total > 0 else 0.0
            confianza_promedio = sum(e.get("confianza_prediccion", 0) for e in explicaciones) / total
            
            # Señal distribucion
            senal_dist = {}
            features_freq = {}
            
            for exp in explicaciones:
                senal = exp.get("senal_prediccion")
                senal_dist[senal] = senal_dist.get(senal, 0) + 1
                
                # Features top 5
                for feat in exp.get("features_top20", [])[:5]:
                    fname = feat.get("feature_name")
                    if fname:
                        features_freq[fname] = features_freq.get(fname, 0) + 1
            
            top_features = sorted(features_freq.items(), key=lambda x: x[1], reverse=True)
            top_features = [f[0] for f in top_features[:10]]
            
            return {
                "total_explicaciones": total,
                "explicaciones_correctas": correctas,
                "tasa_acierto": float(tasa_acierto),
                "features_mas_frecuentes": top_features,
                "senal_distribucion": senal_dist,
                "confianza_promedio": float(confianza_promedio),
                "periodo": f"últimos {dias} días"
            }
        
        except Exception as e:
            logger.error(f"❌ Error en ExplicacionXAIDAO.obtener_estadisticas: {e}")
            return {}
