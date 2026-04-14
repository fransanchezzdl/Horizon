# backend/services/price_history_service.py
"""
Servicio para obtener OHLC histórico + señales de predicción por ticker.
Combina yfinance (precios) con prediction_log (señales IA).
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import yfinance as yf
import logging

from ..daos.prediction_log_dao import PredictionLogDAO

logger = logging.getLogger(__name__)


class PriceHistoryService:

    @staticmethod
    def get_price_and_signals(ticker: str, days: int = 30) -> Dict:
        """
        Devuelve velas OHLC + señales IA para el rango solicitado.

        Args:
            ticker: Símbolo (ej: "AAPL")
            days:   Rango en días. Valores permitidos: 7, 30, 90.

        Returns:
            {
                "candles": [{"time": "YYYY-MM-DD", "open": float, "high": float,
                              "low": float, "close": float}],
                "signals": [{"time": "YYYY-MM-DD", "signal": str,
                              "confidence": float, "correct": bool|None}]
            }
        """
        if days not in (7, 30, 90):
            logger.warning(f"[PriceHistoryService] days={days} no válido, usando 30")
            days = 30

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        candles = PriceHistoryService._fetch_ohlc(ticker, start_date, end_date)
        signals = PriceHistoryService._fetch_signals(ticker, start_date)

        return {"candles": candles, "signals": signals}

    @staticmethod
    def _fetch_ohlc(ticker: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Descarga OHLC de yfinance y lo convierte al formato esperado por Lightweight Charts."""
        try:
            data = yf.download(
                ticker,
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                progress=False,
                auto_adjust=True
            )

            if data.empty:
                logger.warning(f"[PriceHistoryService] Sin datos OHLC para {ticker}")
                return []

            # Aplanar MultiIndex si existe
            if hasattr(data.columns, 'get_level_values'):
                data.columns = data.columns.get_level_values(0)

            candles = []
            for date_idx, row in data.iterrows():
                try:
                    candles.append({
                        "time": date_idx.strftime("%Y-%m-%d"),
                        "open": round(float(row["Open"]), 4),
                        "high": round(float(row["High"]), 4),
                        "low": round(float(row["Low"]), 4),
                        "close": round(float(row["Close"]), 4),
                    })
                except (KeyError, ValueError):
                    continue

            logger.info(f"[PriceHistoryService] {len(candles)} velas para {ticker}")
            return candles

        except Exception as e:
            logger.error(f"[PriceHistoryService] Error OHLC {ticker}: {e}")
            return []

    @staticmethod
    def _fetch_signals(ticker: str, start_date: datetime) -> List[Dict]:
        """Obtiene predicciones del prediction_log desde start_date."""
        try:
            all_preds = PredictionLogDAO.obtener_por_ticker(ticker, solo_resueltas=False, limit=200)

            signals = []
            for pred in all_preds:
                fecha_str = pred.get("fecha_prediccion")
                if not fecha_str:
                    continue

                # Filtrar por rango
                try:
                    fecha_dt = datetime.fromisoformat(str(fecha_str))
                except ValueError:
                    continue

                fecha_dt_naive = fecha_dt.replace(tzinfo=None)
                if fecha_dt_naive < start_date:
                    continue

                resuelta = pred.get("resuelta", False)
                correct: Optional[bool] = pred.get("correcta") if resuelta else None

                signals.append({
                    "time": fecha_dt_naive.strftime("%Y-%m-%d"),
                    "signal": pred.get("tendencia_predicha", ""),
                    "confidence": pred.get("confianza_ensemble") or 0.0,
                    "correct": correct,
                })

            logger.info(f"[PriceHistoryService] {len(signals)} señales para {ticker}")
            return signals

        except Exception as e:
            logger.error(f"[PriceHistoryService] Error señales {ticker}: {e}")
            return []
