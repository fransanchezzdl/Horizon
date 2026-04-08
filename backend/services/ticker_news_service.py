"""Servicio de noticias recientes por ticker para la vista de analisis."""

from __future__ import annotations

import logging
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any

import requests

logger = logging.getLogger(__name__)


class TickerNewsService:
    """Obtiene noticias recientes y clasifica su sentimiento con IA."""

    ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"
    TRANSLATION_MODEL_NAME = "Helsinki-NLP/opus-mt-en-es"
    CACHE_TTL_MINUTES = 5
    CACHE_STALE_FALLBACK_MINUTES = 60

    PREFERRED_SOURCES = {
        "reuters",
        "cnbc",
        "bloomberg",
        "the wall street journal",
        "financial times",
        "forbes",
        "ap news",
        "marketwatch",
        "yahoo finance",
    }
    TECHNICAL_SOURCES = {
        "tradingkey",
        "benzinga",
    }
    TECHNICAL_KEYWORDS = {
        "whale activity",
        "options activity",
        "put option",
        "call option",
        "price target",
        "technical analysis",
        "moved up",
        "moved down",
        "signal does it send",
        "analyst ratings",
    }
    SIMPLE_NEWS_KEYWORDS = {
        "announces",
        "launch",
        "unveils",
        "iphone",
        "earnings",
        "revenue",
        "profit",
        "lawsuit",
        "acquisition",
        "partnership",
        "drops",
        "falls",
        "jumps",
        "surges",
        "guidance",
    }

    def __init__(self) -> None:
        self.alpha_vantage_api_key = (
            os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()
            or os.getenv("ALPHAVANTAGE_API_KEY", "").strip()
        )
        self._translator_pipeline = None
        self._translator_init_attempted = False
        self._news_cache: dict[str, dict[str, Any]] = {}

    def obtener_noticias_ticker(self, ticker: str, limit: int = 3, days_back: int = 7) -> dict[str, Any]:
        """Devuelve noticias recientes con sentimiento para un ticker."""
        ticker_normalized = (ticker or "").strip().upper()
        safe_limit = max(1, min(limit, 3))

        if not ticker_normalized:
            return {"ticker": "", "noticias": []}

        cached_fresh = self._get_cached_news(ticker_normalized, max_age_minutes=self.CACHE_TTL_MINUTES)
        if cached_fresh is not None:
            return {"ticker": ticker_normalized, "noticias": cached_fresh[:safe_limit]}

        feed, fetch_status = self._fetch_alpha_vantage_feed(
            ticker=ticker_normalized,
            days_back=days_back,
            fetch_limit=max(20, safe_limit * 6),
        )
        noticias = self._build_news_payload(feed, limit=safe_limit)

        if noticias:
            self._set_cached_news(ticker_normalized, noticias)
            return {
                "ticker": ticker_normalized,
                "noticias": noticias,
            }

        # Fallback: si API falla/rate-limit, devolver cache reciente para no romper UX.
        cached_stale = self._get_cached_news(
            ticker_normalized,
            max_age_minutes=self.CACHE_STALE_FALLBACK_MINUTES,
        )
        if cached_stale is not None:
            logger.info("Usando cache de noticias para %s (status=%s)", ticker_normalized, fetch_status)
            return {"ticker": ticker_normalized, "noticias": cached_stale[:safe_limit]}

        return {
            "ticker": ticker_normalized,
            "noticias": [],
        }

    def _fetch_alpha_vantage_feed(self, ticker: str, days_back: int, fetch_limit: int) -> tuple[list[dict[str, Any]], str]:
        if not self.alpha_vantage_api_key:
            logger.warning("ALPHA_VANTAGE_API_KEY no configurada. Noticias vacias para %s", ticker)
            return [], "missing_api_key"

        end_dt = date.today()
        start_dt = end_dt - timedelta(days=max(days_back, 1))

        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": ticker,
            "time_from": start_dt.strftime("%Y%m%d") + "T0000",
            "time_to": end_dt.strftime("%Y%m%d") + "T2359",
            "limit": min(max(fetch_limit, 1), 50),
            "apikey": self.alpha_vantage_api_key,
        }

        try:
            response = requests.get(self.ALPHA_VANTAGE_URL, params=params, timeout=15)
            response.raise_for_status()
            payload = response.json()

            if "Error Message" in payload:
                logger.warning("Alpha Vantage error para %s: %s", ticker, payload.get("Error Message"))
                return [], "api_error"

            if "Note" in payload:
                logger.warning("Alpha Vantage limit/note para %s: %s", ticker, payload.get("Note"))
                return [], "rate_limited"

            feed = payload.get("feed", [])
            if not isinstance(feed, list):
                return [], "empty"
            return feed, "ok"
        except Exception as exc:
            logger.warning("Error consultando Alpha Vantage para %s: %s", ticker, exc)
            return [], "request_error"

    def _build_news_payload(self, feed: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for item in feed:
            title = (item.get("title") or "").strip()
            summary = (item.get("summary") or "").strip()
            url = (item.get("url") or "").strip()
            source = (item.get("source") or "").strip() or "Unknown"
            fecha_iso = self._parse_time_published(item.get("time_published"))

            if not title or not url:
                continue

            titulo_es = self._translate_to_spanish(title)
            resumen_es = self._translate_to_spanish(summary)

            normalized.append(
                {
                    "titulo": titulo_es,
                    "resumen": self._short_summary(resumen_es),
                    "url": url,
                    "fuente": source,
                    "fecha": fecha_iso,
                    "_ranking": self._news_relevance_score(title, summary, source),
                }
            )

        normalized.sort(key=lambda n: (n.get("_ranking", 0), n.get("fecha", "")), reverse=True)

        simple_candidates = [n for n in normalized if n.get("_ranking", 0) > 0]
        selected = (simple_candidates or normalized)[:limit]

        for item in selected:
            item.pop("_ranking", None)
        return selected

    def _news_relevance_score(self, title: str, summary: str, source: str) -> int:
        combined = f"{title} {summary}".lower()
        source_lower = (source or "").lower()
        score = 0

        if any(term in combined for term in self.SIMPLE_NEWS_KEYWORDS):
            score += 3

        if any(term in source_lower for term in self.PREFERRED_SOURCES):
            score += 2

        if any(term in combined for term in self.TECHNICAL_KEYWORDS):
            score -= 3

        if any(term in source_lower for term in self.TECHNICAL_SOURCES):
            score -= 2

        return score

    def _get_cached_news(self, ticker: str, max_age_minutes: int) -> list[dict[str, Any]] | None:
        cached = self._news_cache.get(ticker)
        if not cached:
            return None

        saved_at = cached.get("saved_at")
        if not isinstance(saved_at, datetime):
            return None

        age = datetime.now(timezone.utc) - saved_at
        if age > timedelta(minutes=max_age_minutes):
            return None

        noticias = cached.get("noticias")
        return noticias if isinstance(noticias, list) else None

    def _set_cached_news(self, ticker: str, noticias: list[dict[str, Any]]) -> None:
        self._news_cache[ticker] = {
            "saved_at": datetime.now(timezone.utc),
            "noticias": noticias,
        }

    def _short_summary(self, text: str, max_chars: int = 200) -> str:
        cleaned = (text or "").strip()
        if not cleaned:
            return "Sin descripcion disponible."
        if len(cleaned) <= max_chars:
            return cleaned

        cut = cleaned[:max_chars].rsplit(" ", 1)[0].strip()
        if not cut:
            cut = cleaned[:max_chars].strip()
        return f"{cut}..."

    def _translate_to_spanish(self, text: str) -> str:
        raw = (text or "").strip()
        if not raw:
            return ""

        if self._looks_spanish(raw):
            return raw

        translated_http = self._translate_with_http(raw)
        if translated_http:
            return translated_http

        translator = self._get_translator()
        if translator is None:
            return raw

        try:
            result = translator(raw[:900], max_length=512)
            if isinstance(result, list) and result:
                translated = str(result[0].get("translation_text", "")).strip()
                return translated or raw
            return raw
        except Exception as exc:
            logger.warning("No se pudo traducir texto al espanol: %s", exc)
            return raw

    def _translate_with_http(self, text: str) -> str:
        try:
            response = requests.get(
                "https://translate.googleapis.com/translate_a/single",
                params={
                    "client": "gtx",
                    "sl": "en",
                    "tl": "es",
                    "dt": "t",
                    "q": text[:1200],
                },
                timeout=8,
            )
            response.raise_for_status()
            payload = response.json()

            if not isinstance(payload, list) or not payload:
                return ""

            chunks = payload[0]
            if not isinstance(chunks, list):
                return ""

            translated = "".join(
                part[0] for part in chunks
                if isinstance(part, list) and part and isinstance(part[0], str)
            ).strip()
            return translated
        except Exception:
            return ""

    def _looks_spanish(self, text: str) -> bool:
        sample = text.lower()
        spanish_markers = (" el ", " la ", " los ", " las ", " de ", " para ", " en ", " y ", " con ")
        return any(marker in f" {sample} " for marker in spanish_markers)

    def _get_translator(self):
        if self._translator_pipeline is not None:
            return self._translator_pipeline

        if self._translator_init_attempted:
            return None

        self._translator_init_attempted = True
        try:
            from transformers import pipeline

            self._translator_pipeline = pipeline(
                "translation",
                model=self.TRANSLATION_MODEL_NAME,
                tokenizer=self.TRANSLATION_MODEL_NAME,
                device=-1,
            )
            return self._translator_pipeline
        except Exception as exc:
            logger.warning("No se pudo inicializar traductor en-es: %s", exc)
            return None

    def _parse_time_published(self, time_published: Any) -> str:
        if isinstance(time_published, str) and len(time_published) >= 15:
            try:
                parsed = datetime.strptime(time_published[:15], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
                return parsed.isoformat()
            except ValueError:
                pass

        return datetime.now(timezone.utc).isoformat()

