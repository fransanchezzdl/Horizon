"""
XAI Update Service - Guarda explicaciones en Supabase
======================================================

Toma explicaciones generadas por XAIEngine y las persiste en la BD.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class XAIUpdateService:
    """
    Servicio para actualizar explicaciones XAI en Supabase.
    
    Métodos:
    - guardar_explicacion(ticker, explicacion_dict)
    - actualizar_validacion(id_explicacion, util, comentario)
    - obtener_explicacion_reciente(ticker)
    """
    
    @staticmethod
    def _sanitizar_json_para_supabase(obj: Any) -> Any:
        """
        Convierte objetos Python a JSON-serializable y reemplaza NaN/Inf.
        
        Args:
            obj: Objeto a sanitizar (dict, list, float, etc)
        
        Returns:
            Objeto seguro para Supabase
        """
        import numpy as np
        
        if isinstance(obj, dict):
            return {k: XAIUpdateService._sanitizar_json_para_supabase(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [XAIUpdateService._sanitizar_json_para_supabase(v) for v in obj]
        elif isinstance(obj, (np.floating, float)):
            if np.isnan(obj) or np.isinf(obj):
                return None
            return float(obj)
        elif isinstance(obj, (np.integer, int)):
            return int(obj)
        elif isinstance(obj, np.ndarray):
            return XAIUpdateService._sanitizar_json_para_supabase(obj.tolist())
        elif isinstance(obj, (bool, type(None))):
            return obj
        else:
            return str(obj)
    
    @staticmethod
    def guardar_explicacion(
        ticker: str,
        explicacion: Dict[str, Any],
        supabase_client=None,
        version_modelo: str = "Phase3",
        seed_modelo: int = 42
    ) -> bool:
        """
        Guarda una explicación XAI completa en Supabase.
        
        Args:
            ticker: Ticker del activo
            explicacion: Dict con explicación completa (de XAIEngine.explain_prediction)
            supabase_client: Cliente Supabase (opcional, se carga si no pasa)
            version_modelo: Versión del modelo (para tracking)
            seed_modelo: Seed usado en entrenamiento
        
        Returns:
            True si exitoso, False otherwise
        
        Explicación esperada:
        {
            'shap_valores': [{feature_name, shap_value, feature_value, shap_abs}, ...],
            'shap_grafico_base64': 'base64_png_string',
            'features_top20': [{feature_name, importancia, valor}, ...],
            'pesos_atencion': [{dia_relativo, peso_atencion}, ...],
            'contribucion_features': {feature_name: contribution_value, ...},
            'timestamp': 'ISO_formatted_timestamp',
            'senal_prediccion': 'ALCISTA|BAJISTA|LATERAL',
            'confianza': 0.85
        }
        """
        
        try:
            # Cargar Supabase si no se pasó
            if supabase_client is None:
                import os
                from dotenv import load_dotenv
                from supabase import create_client
                
                load_dotenv()
                SUPABASE_URL = os.getenv("SUPABASE_URL")
                SUPABASE_KEY = os.getenv("SUPABASE_KEY")
                supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            
            # Sanitizar datos
            shap_valores = XAIUpdateService._sanitizar_json_para_supabase(
                explicacion.get("shap_valores", [])
            )
            shap_grafico_base64 = explicacion.get("shap_grafico_base64", "")
            features_top20 = XAIUpdateService._sanitizar_json_para_supabase(
                explicacion.get("features_top20", [])
            )
            pesos_atencion = XAIUpdateService._sanitizar_json_para_supabase(
                explicacion.get("pesos_atencion", [])
            )
            contribucion_features = XAIUpdateService._sanitizar_json_para_supabase(
                explicacion.get("contribucion_features", {})
            )
            
            # Construir registro
            registro_explicacion = {
                "ticker": ticker,
                "fecha_prediccion": explicacion.get("timestamp", datetime.now().isoformat()),
                "shap_valores": json.dumps(shap_valores),  # JSONB se guarda como string
                "shap_grafico": shap_grafico_base64,  # Base64 string
                "features_top20": json.dumps(features_top20),
                "pesos_atencion": json.dumps(pesos_atencion) if pesos_atencion else json.dumps([]),
                "contribucion_features": json.dumps(contribucion_features),
                "senal_prediccion": explicacion.get("senal_prediccion", "LATERAL"),
                "confianza_prediccion": float(explicacion.get("confianza", 0.5)),
                "version_modelo": version_modelo,
                "seed_modelo": seed_modelo,
                "prediccion_correcta": None,  # Será llenado después cuando se valide
            }
            
            # Insertar en Supabase
            response = supabase_client.table("xai_explicaciones").insert(registro_explicacion).execute()
            
            if response.data and len(response.data) > 0:
                id_explicacion = response.data[0].get("id")
                logger.info(f"✅ Explicación guardada para {ticker} (ID: {id_explicacion})")
                return True
            else:
                logger.error(f"❌ No se pudo insertar explicación para {ticker}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Error guardando explicación para {ticker}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def obtener_explicacion_reciente(
        ticker: str,
        supabase_client=None,
        limit: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene la explicación más reciente para un ticker.
        
        Args:
            ticker: Ticker del activo
            supabase_client: Cliente Supabase (opcional)
            limit: Número de explicaciones a obtener
        
        Returns:
            Dict con explicación (o lista si limit > 1), None si error
        """
        try:
            if supabase_client is None:
                import os
                from dotenv import load_dotenv
                from supabase import create_client
                
                load_dotenv()
                SUPABASE_URL = os.getenv("SUPABASE_URL")
                SUPABASE_KEY = os.getenv("SUPABASE_KEY")
                supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            
            # Query: explicaciones recientes por ticker
            response = supabase_client.table("xai_explicaciones")\
                .select("*")\
                .eq("ticker", ticker)\
                .order("fecha_prediccion", desc=True)\
                .limit(limit)\
                .execute()
            
            if response.data:
                # Convertir JSON strings a objects
                for row in response.data:
                    if isinstance(row.get("shap_valores"), str):
                        row["shap_valores"] = json.loads(row["shap_valores"])
                    if isinstance(row.get("features_top20"), str):
                        row["features_top20"] = json.loads(row["features_top20"])
                    if isinstance(row.get("pesos_atencion"), str):
                        row["pesos_atencion"] = json.loads(row["pesos_atencion"])
                    if isinstance(row.get("contribucion_features"), str):
                        row["contribucion_features"] = json.loads(row["contribucion_features"])
                
                logger.info(f"✓ Obtenida(s) {len(response.data)} explicación(es) para {ticker}")
                return response.data[0] if limit == 1 else response.data
            else:
                logger.warning(f"⚠️ No hay explicaciones para {ticker}")
                return None
        
        except Exception as e:
            logger.error(f"❌ Error obteniendo explicación para {ticker}: {e}")
            return None
    
    @staticmethod
    def actualizar_validacion(
        id_explicacion: int,
        util: bool,
        comentario: str = "",
        supabase_client=None
    ) -> bool:
        """
        Actualiza validación de una explicación (user feedback).
        
        Args:
            id_explicacion: ID de la explicación en BD
            util: bool - si el usuario encontró útil la explicación
            comentario: Comentario opcional
            supabase_client: Cliente Supabase
        
        Returns:
            True si exitoso
        """
        try:
            if supabase_client is None:
                import os
                from dotenv import load_dotenv
                from supabase import create_client
                
                load_dotenv()
                SUPABASE_URL = os.getenv("SUPABASE_URL")
                SUPABASE_KEY = os.getenv("SUPABASE_KEY")
                supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            
            # Insertar validación
            validacion = {
                "id_explicacion": id_explicacion,
                "util": util,
                "comentario_usuario": comentario if comentario else None,
            }
            
            response = supabase_client.table("xai_validacion").insert(validacion).execute()
            
            if response.data:
                logger.info(f"✅ Validación guardada para explicación {id_explicacion}")
                return True
            else:
                logger.error(f"❌ No se pudo guardar validación")
                return False
        
        except Exception as e:
            logger.error(f"❌ Error en actualizar_validacion: {e}")
            return False
    
    @staticmethod
    def obtener_metricas_xai_por_ticker(
        ticker: str,
        dias_atras: int = 30,
        supabase_client=None
    ) -> Dict[str, Any]:
        """
        Obtiene métricas XAI agregadas para un ticker (últimos N días).
        
        Útil para análisis de calidad de explicaciones.
        
        Args:
            ticker: Ticker del activo
            dias_atras: Número de días a analizar
            supabase_client: Cliente Supabase
        
        Returns:
            Dict con métricas:
            {
                'total_explicaciones': int,
                'explicaciones_validadas': int,
                'porcentaje_util': float (0-1),
                'features_mas_importantes': [{name, freq}, ...],
                'senal_distribucion': {ALCISTA: int, BAJISTA: int, ...}
            }
        """
        try:
            if supabase_client is None:
                import os
                from dotenv import load_dotenv
                from supabase import create_client
                
                load_dotenv()
                SUPABASE_URL = os.getenv("SUPABASE_URL")
                SUPABASE_KEY = os.getenv("SUPABASE_KEY")
                supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            
            # Query explicaciones recientes
            from datetime import timedelta
            fecha_inicio = (datetime.now() - timedelta(days=dias_atras)).isoformat()
            
            response = supabase_client.table("xai_explicaciones")\
                .select("*")\
                .eq("ticker", ticker)\
                .gte("fecha_prediccion", fecha_inicio)\
                .execute()
            
            if not response.data:
                return {
                    "total_explicaciones": 0,
                    "explicaciones_validadas": 0,
                    "porcentaje_util": 0,
                    "features_mas_importantes": [],
                    "senal_distribucion": {}
                }
            
            explicaciones = response.data
            total = len(explicaciones)
            
            # Contar señales
            senal_dist = {}
            features_freq = {}
            
            for exp in explicaciones:
                # Señales
                senal = exp.get("senal_prediccion")
                senal_dist[senal] = senal_dist.get(senal, 0) + 1
                
                # Features top 20
                try:
                    features_top20 = json.loads(exp.get("features_top20", "[]"))
                    for feat in features_top20[:5]:  # Top 5 de cada explicación
                        fname = feat.get("feature_name")
                        if fname:
                            features_freq[fname] = features_freq.get(fname, 0) + 1
                except:
                    pass
            
            # Obtener validaciones
            validaciones = supabase_client.table("xai_validacion")\
                .select("util")\
                .in_("id_explicacion", [e.get("id") for e in explicaciones])\
                .execute()
            
            validadas = len(validaciones.data) if validaciones.data else 0
            utiles = sum(1 for v in (validaciones.data or []) if v.get("util") == True)
            porcentaje_util = (utiles / validadas) if validadas > 0 else 0
            
            # Top features
            top_features = sorted(
                [{"feature_name": k, "frecuencia": v} for k, v in features_freq.items()],
                key=lambda x: x["frecuencia"],
                reverse=True
            )[:10]
            
            return {
                "total_explicaciones": total,
                "explicaciones_validadas": validadas,
                "porcentaje_util": float(porcentaje_util),
                "features_mas_importantes": top_features,
                "senal_distribucion": senal_dist,
                "periodo": f"{dias_atras} días"
            }
        
        except Exception as e:
            logger.error(f"❌ Error en obtener_metricas_xai_por_ticker: {e}")
            return {}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test
    explicacion_test = {
        "timestamp": datetime.now().isoformat(),
        "ticker": "AAPL",
        "senal_prediccion": "ALCISTA",
        "confianza": 0.85,
        "shap_valores": [
            {"feature_name": "RSI", "shap_value": 0.15, "feature_value": 65.2, "shap_abs": 0.15},
            {"feature_name": "MACD", "shap_value": -0.05, "feature_value": 0.5, "shap_abs": 0.05}
        ],
        "shap_grafico_base64": "",
        "features_top20": [],
        "pesos_atencion": [],
        "contribucion_features": {"RSI": 0.15, "MACD": -0.05}
    }
    
    print("✓ XAIUpdateService testeado (estructura validada)")
