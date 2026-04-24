# backend/services/price_history_service.py
"""
Servicio para obtener OHLC histórico + señales de predicción por ticker.
Combina yfinance (precios) con prediction_log (señales IA).
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import yfinance as yf
import logging
import pandas as pd

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
    def get_daily_variations(tickers: List[str]) -> Dict[str, Optional[float]]:
        """
        Devuelve la variación diaria (%) para múltiples tickers con la misma
        lógica temporal que usa la vista de análisis (últimos 7 días, auto_adjust),
        calculada como ((close_ultimo - close_previo) / close_previo) * 100.

        Returns: {ticker: variacion_pct | None}
        """
        result: Dict[str, Optional[float]] = {t: None for t in tickers}
        if not tickers:
            return result

        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)

            data = yf.download(
                tickers=" ".join(tickers),
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                interval="1d",
                progress=False,
                auto_adjust=True,
                group_by="ticker",
                threads=False,
            )

            if data is None or data.empty:
                logger.warning(f"[PriceHistoryService] Sin datos batch para {tickers}")
                return result

            for ticker in tickers:
                try:
                    closes = PriceHistoryService._extract_close_series(data, ticker, len(tickers) > 1)
                    if closes is None:
                        logger.warning(f"[PriceHistoryService] {ticker}: columna Close no encontrada")
                        continue
                    closes = closes.dropna()

                    if len(closes) < 2:
                        logger.warning(f"[PriceHistoryService] {ticker}: <2 closes válidos")
                        continue

                    prev_close = float(closes.iloc[-2])
                    last_close = float(closes.iloc[-1])
                    if prev_close <= 0:
                        continue

                    variacion = ((last_close - prev_close) / prev_close) * 100
                    # Sin redondeo prematuro: el frontend redondea al mostrar.
                    result[ticker] = variacion
                except (KeyError, IndexError, ValueError) as e:
                    logger.warning(f"[PriceHistoryService] {ticker}: {e}")
                    continue

            return result

        except Exception as e:
            logger.error(f"[PriceHistoryService] Error batch variations: {e}")
            return result

    @staticmethod
    def _extract_close_series(data: pd.DataFrame, ticker: str, is_multi: bool):
        """Extrae la serie de cierre para ticker manejando layouts distintos de yfinance."""
        try:
            if not is_multi:
                if "Close" in data.columns:
                    return data["Close"]

                if isinstance(data.columns, pd.MultiIndex):
                    if "Close" in data.columns.get_level_values(0):
                        close_df = data["Close"]
                        if isinstance(close_df, pd.DataFrame):
                            return close_df.iloc[:, 0]
                        return close_df
                    if "Close" in data.columns.get_level_values(1):
                        cols = [col for col in data.columns if len(col) > 1 and col[1] == "Close"]
                        if cols:
                            return data[cols[0]]
                return None

            if isinstance(data.columns, pd.MultiIndex):
                lvl0 = set(data.columns.get_level_values(0))
                lvl1 = set(data.columns.get_level_values(1))

                # group_by="ticker": (ticker, campo)
                if ticker in lvl0 and "Close" in lvl1:
                    ticker_df = data[ticker]
                    if "Close" in ticker_df.columns:
                        return ticker_df["Close"]

                # layout alternativo: (campo, ticker)
                if "Close" in lvl0 and ticker in lvl1:
                    close_df = data["Close"]
                    if isinstance(close_df, pd.DataFrame) and ticker in close_df.columns:
                        return close_df[ticker]

            return None
        except Exception:
            return None

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
