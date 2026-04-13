"""
DAO para el registro de predicciones con resolución de outcomes.

Tabla: prediction_log
Columnas en español (consistente con el resto del schema):
  fecha_prediccion, fecha_objetivo, tendencia_predicha,
  confianza_ensemble, precio_entrada, dias_horizonte,
  resuelta, tendencia_real, precio_salida, correcta, fecha_resolucion
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
from ..database import supabase

TABLE = "prediction_log"


class PredictionLogDAO:

    @staticmethod
    def crear(record: Dict) -> Optional[Dict]:
        """
        Inserta una predicción nueva.

        Args:
            record: {
                ticker, fecha_prediccion (date|str), fecha_objetivo (date|str),
                tendencia_predicha, confianza_ensemble, precio_entrada, dias_horizonte
            }

        Returns:
            Fila insertada o None si ya existe (UNIQUE ticker+fecha_prediccion).
        """
        try:
            for key in ("fecha_prediccion", "fecha_objetivo"):
                if key in record and isinstance(record[key], date):
                    record[key] = record[key].isoformat()

            result = (
                supabase.table(TABLE)
                .insert(record)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            # Violación UNIQUE (predicción del día ya existe) — no es un error real
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                return None
            print(f"[PredictionLogDAO] Error crear: {e}")
            return None

    @staticmethod
    def obtener_pendientes_de_resolver() -> List[Dict]:
        """
        Devuelve predicciones cuya fecha_objetivo ya pasó y aún no están resueltas.
        """
        try:
            hoy = date.today().isoformat()
            result = (
                supabase.table(TABLE)
                .select("*")
                .eq("resuelta", False)
                .lte("fecha_objetivo", hoy)
                .execute()
            )
            return result.data or []
        except Exception as e:
            print(f"[PredictionLogDAO] Error obtener_pendientes: {e}")
            return []

    @staticmethod
    def resolver(record_id: int, tendencia_real: str, precio_salida: float, correcta: bool) -> bool:
        """
        Marca una predicción como resuelta con el outcome real.

        Args:
            record_id:      ID del registro.
            tendencia_real: Tendencia real observada ('ALCISTA'|'BAJISTA'|'LATERAL').
            precio_salida:  Precio de cierre en fecha_objetivo.
            correcta:       True si tendencia_predicha == tendencia_real.
        """
        try:
            supabase.table(TABLE).update({
                "resuelta":         True,
                "tendencia_real":   tendencia_real,
                "precio_salida":    precio_salida,
                "correcta":         correcta,
                "fecha_resolucion": datetime.utcnow().isoformat(),
            }).eq("id", record_id).execute()
            return True
        except Exception as e:
            print(f"[PredictionLogDAO] Error resolver id={record_id}: {e}")
            return False

    @staticmethod
    def obtener_por_ticker(ticker: str, solo_resueltas: bool = False, limit: int = 60) -> List[Dict]:
        """
        Devuelve el historial de predicciones de un ticker, ordenado por fecha desc.
        """
        try:
            q = (
                supabase.table(TABLE)
                .select("*")
                .eq("ticker", ticker)
                .order("fecha_prediccion", desc=True)
                .limit(limit)
            )
            if solo_resueltas:
                q = q.eq("resuelta", True)
            return q.execute().data or []
        except Exception as e:
            print(f"[PredictionLogDAO] Error obtener_por_ticker {ticker}: {e}")
            return []

    @staticmethod
    def stats_ticker(ticker: str) -> Dict:
        """
        Calcula métricas de fiabilidad para un ticker a partir de predicciones resueltas.

        Returns: {
            total_predicciones, resueltas, correctas,
            live_accuracy (% sobre resueltas),
            baseline (33.33),
            por_clase: {ALCISTA: {predicciones, correctas}, ...}
        }
        """
        try:
            resueltas = PredictionLogDAO.obtener_por_ticker(ticker, solo_resueltas=True, limit=200)

            if not resueltas:
                return {
                    "ticker":             ticker,
                    "total_predicciones": PredictionLogDAO._contar_total(ticker),
                    "resueltas":          0,
                    "correctas":          0,
                    "live_accuracy":      None,
                    "baseline":           33.33,
                    "por_clase":          {},
                }

            n_correctas = sum(1 for r in resueltas if r.get("correcta"))
            live_accuracy = round(n_correctas / len(resueltas) * 100, 1)

            por_clase: Dict[str, Dict] = {}
            for r in resueltas:
                trend = r.get("tendencia_predicha", "?")
                if trend not in por_clase:
                    por_clase[trend] = {"predicciones": 0, "correctas": 0}
                por_clase[trend]["predicciones"] += 1
                if r.get("correcta"):
                    por_clase[trend]["correctas"] += 1

            return {
                "ticker":             ticker,
                "total_predicciones": PredictionLogDAO._contar_total(ticker),
                "resueltas":          len(resueltas),
                "correctas":          n_correctas,
                "live_accuracy":      live_accuracy,
                "baseline":           33.33,
                "por_clase":          por_clase,
            }

        except Exception as e:
            print(f"[PredictionLogDAO] Error stats_ticker {ticker}: {e}")
            return {"ticker": ticker, "error": str(e)}

    @staticmethod
    def _contar_total(ticker: str) -> int:
        try:
            result = (
                supabase.table(TABLE)
                .select("id", count="exact")
                .eq("ticker", ticker)
                .execute()
            )
            return result.count or 0
        except Exception:
            return 0
