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
        Devuelve velas OHLC + señales IA + cotización en vivo para el rango solicitado.

        Returns:
            {
                "candles": [...],
                "signals": [...],
                "quote": {"price": float|None, "previous_close": float|None,
                          "change_percent": float|None}
            }
        """
        if days not in (7, 30, 90):
            logger.warning(f"[PriceHistoryService] days={days} no válido, usando 30")
            days = 30

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        candles = PriceHistoryService._fetch_ohlc(ticker, start_date, end_date)
        signals = PriceHistoryService._fetch_signals(ticker, start_date)
        quote = PriceHistoryService.get_quote(ticker)

        return {"candles": candles, "signals": signals, "quote": quote}

    @staticmethod
    def get_quote(ticker: str) -> Dict[str, Optional[float]]:
        """
        Cotización en vivo alineada con Google: usa precio intradía y previous_close
        oficial (sin auto_adjust), de modo que change_percent = (last - prev)/prev * 100
        coincide con el "% hoy" mostrado en Google Finance.

        Returns: {"price", "previous_close", "change_percent"}
        """
        empty = {"price": None, "previous_close": None, "change_percent": None}
        try:
            t = yf.Ticker(ticker)
            last = None
            prev = None

            # 1) fast_info: rápido, sin scraping. Probar varias claves/atributos.
            try:
                fi = t.fast_info
                # Preferir regularMarket* (sin ajustar por dividendos/splits) para
                # alinear con Google. fast_info["previous_close"] aplica auto-ajuste
                # en versiones recientes de yfinance y desvía el % cuando hay ex-div.
                last = PriceHistoryService._read_field(fi, ["regular_market_price", "regularMarketPrice", "last_price", "lastPrice"])
                prev = PriceHistoryService._read_field(fi, ["regular_market_previous_close", "regularMarketPreviousClose", "previous_close", "previousClose"])
            except Exception as e:
                logger.warning(f"[PriceHistoryService] fast_info {ticker}: {e}")

            # 2) Fallback a .info si fast_info no entrega datos.
            if last is None or prev is None:
                try:
                    info = t.info or {}
                    if last is None:
                        last = PriceHistoryService._safe_float(
                            info.get("currentPrice") or info.get("regularMarketPrice")
                        )
                    if prev is None:
                        prev = PriceHistoryService._safe_float(
                            info.get("regularMarketPreviousClose") or info.get("previousClose")
                        )
                except Exception as e:
                    logger.warning(f"[PriceHistoryService] info {ticker}: {e}")

            if last is None or prev is None or prev <= 0:
                logger.warning(f"[PriceHistoryService] quote {ticker}: last={last} prev={prev}")
                return empty

            return {
                "price": last,
                "previous_close": prev,
                "change_percent": ((last - prev) / prev) * 100,
            }
        except Exception as e:
            logger.warning(f"[PriceHistoryService] quote {ticker}: {e}")
            return empty

    @staticmethod
    def _read_field(obj, keys):
        """Lee un campo de un objeto que puede ser dict-like u objeto con atributos."""
        for k in keys:
            try:
                v = obj[k]
                f = PriceHistoryService._safe_float(v)
                if f is not None:
                    return f
            except (KeyError, TypeError, IndexError):
                pass
            v = getattr(obj, k, None)
            f = PriceHistoryService._safe_float(v)
            if f is not None:
                return f
        return None

    @staticmethod
    def _safe_float(value) -> Optional[float]:
        try:
            if value is None:
                return None
            f = float(value)
            return f if f == f else None  # descartar NaN
        except (TypeError, ValueError):
            return None

    @staticmethod
    def get_daily_variations(tickers: List[str]) -> Dict[str, Optional[float]]:
        """
        Variación diaria (%) por ticker, alineada con Google y con get_quote():
            (last_price - previous_close) / previous_close * 100

        Usa fast_info en lugar de un download histórico para que el numerador sea
        el precio intradía actual (no el cierre de ayer) y el denominador sea el
        previous_close oficial sin auto_adjust.

        Returns: {ticker: variacion_pct | None}
        """
        result: Dict[str, Optional[float]] = {t: None for t in tickers}
        if not tickers:
            return result

        for ticker in tickers:
            quote = PriceHistoryService.get_quote(ticker)
            result[ticker] = quote.get("change_percent")
        return result

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
