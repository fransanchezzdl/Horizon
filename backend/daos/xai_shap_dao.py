"""
DAO para obtener el último registro SHAP de xai_explicaciones.

Usado por el endpoint GET /activos/{ticker}/xai/latest-shap.
Devuelve los shap_values ordenados por impacto absoluto, máximo 12 features.
"""

import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class XaiShapDAO:

    @staticmethod
    def _get_supabase_client():
        import os
        from dotenv import load_dotenv
        from supabase import create_client

        load_dotenv()
        return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

    @staticmethod
    def obtener_latest_shap(ticker: str) -> Optional[Dict[str, Any]]:
        """
        Devuelve el último registro SHAP para el ticker.

        Selecciona la fila más reciente de xai_explicaciones, normaliza
        los shap_values al formato { feature, shap, value, abs } y los
        ordena por abs descendente, limitando a 12 features.

        Returns:
            Dict con keys: ticker, fecha, senal, confianza, correcta, shap_values
            None si no existe ningún registro o hay error.
        """
        try:
            supabase = XaiShapDAO._get_supabase_client()

            response = (
                supabase.table("xai_explicaciones")
                .select(
                    "ticker, fecha_prediccion, shap_valores, "
                    "senal_prediccion, confianza_prediccion, prediccion_correcta"
                )
                .eq("ticker", ticker)
                .order("fecha_prediccion", desc=True)
                .limit(1)
                .execute()
            )

            if not response.data:
                return None

            row = response.data[0]

            # shap_valores puede llegar como str (TEXT) o lista (JSONB auto-parseado)
            raw_shap = row.get("shap_valores", "[]")
            if isinstance(raw_shap, str):
                shap_list = json.loads(raw_shap)
            else:
                shap_list = raw_shap or []

            # Normalizar al formato de salida, tolerando variantes de nombres de campo
            normalized = []
            for item in shap_list:
                shap_val = float(
                    item.get("shap_value", item.get("shap", 0)) or 0
                )
                abs_val = float(
                    item.get("shap_abs", item.get("abs", abs(shap_val))) or abs(shap_val)
                )
                feat_val = item.get("feature_value", item.get("value"))
                if isinstance(feat_val, float):
                    feat_val = round(feat_val, 4)

                normalized.append({
                    "feature": item.get("feature_name", item.get("feature", "")),
                    "shap":    round(shap_val, 6),
                    "value":   feat_val,
                    "abs":     round(abs_val, 6),
                })

            # Ordenar por impacto absoluto desc, máximo 12 features
            normalized.sort(key=lambda x: x["abs"], reverse=True)
            normalized = normalized[:12]

            fecha_raw = row.get("fecha_prediccion", "")
            fecha = fecha_raw[:10] if fecha_raw else ""

            return {
                "ticker":      row.get("ticker", ticker),
                "fecha":       fecha,
                "senal":       row.get("senal_prediccion", ""),
                "confianza":   float(row.get("confianza_prediccion") or 0),
                "correcta":    row.get("prediccion_correcta"),
                "shap_values": normalized,
            }

        except Exception as e:
            logger.error(f"Error en XaiShapDAO.obtener_latest_shap({ticker}): {e}")
            return None

    @staticmethod
    def obtener_shap_temporal(ticker: str, limit: int = 30) -> Optional[Dict[str, Any]]:
        """
        Devuelve la evolución temporal de las top-3 features SHAP para el ticker.

        Trae los últimos `limit` registros, identifica las 3 features con mayor
        impacto absoluto promedio, y construye una serie temporal de sus valores SHAP.

        Returns:
            {
                "ticker": str,
                "top_features": [str, str, str],
                "series": [{"fecha": str, feature1: float, feature2: float, feature3: float}, ...]
            }
            None si no hay datos.
        """
        try:
            supabase = XaiShapDAO._get_supabase_client()

            response = (
                supabase.table("xai_explicaciones")
                .select("fecha_prediccion, shap_valores")
                .eq("ticker", ticker)
                .order("fecha_prediccion", desc=False)
                .limit(limit)
                .execute()
            )

            if not response.data:
                return None

            rows = response.data

            # Parsear shap_valores de cada fila
            parsed = []
            for row in rows:
                raw = row.get("shap_valores", "[]")
                shap_list = json.loads(raw) if isinstance(raw, str) else (raw or [])
                fecha = (row.get("fecha_prediccion") or "")[:10]
                parsed.append({"fecha": fecha, "shap_list": shap_list})

            # Calcular impacto absoluto promedio por feature en todas las entradas
            feature_abs_sum: Dict[str, float] = {}
            feature_count: Dict[str, int] = {}
            for entry in parsed:
                for item in entry["shap_list"]:
                    name = item.get("feature_name", item.get("feature", ""))
                    abs_val = float(item.get("shap_abs", item.get("abs", abs(item.get("shap_value", item.get("shap", 0))))) or 0)
                    feature_abs_sum[name] = feature_abs_sum.get(name, 0) + abs_val
                    feature_count[name] = feature_count.get(name, 0) + 1

            avg_abs = {
                f: feature_abs_sum[f] / feature_count[f]
                for f in feature_abs_sum
                if feature_count[f] > 0
            }
            top_features = sorted(avg_abs, key=lambda f: avg_abs[f], reverse=True)[:3]

            if not top_features:
                return None

            # Construir series temporales
            series = []
            for entry in parsed:
                shap_by_feature = {
                    item.get("feature_name", item.get("feature", "")): float(
                        item.get("shap_value", item.get("shap", 0)) or 0
                    )
                    for item in entry["shap_list"]
                }
                point = {"fecha": entry["fecha"]}
                for feat in top_features:
                    point[feat] = round(shap_by_feature.get(feat, 0), 6)
                series.append(point)

            return {
                "ticker": ticker,
                "top_features": top_features,
                "series": series,
            }

        except Exception as e:
            logger.error(f"Error en XaiShapDAO.obtener_shap_temporal({ticker}): {e}")
            return None
