"""Servicio para interactuar con la API de Google Gemini."""

import os
import json
from typing import Any
from dotenv import load_dotenv
from google.genai import Client
from ..exceptions import (
    GeminiAPIKeyMissingError,
    GeminiQuotaExceededError,
    GeminiAPIConfigError,
    GeminiAPIError
)


# Primero intentamos cargar el .env que está junto a database.py (backend/.env)
base_dir = os.path.dirname(os.path.dirname(__file__))  # Subimos desde services/ a backend/
local_env = os.path.join(base_dir, ".env")
load_dotenv(local_env)
# Si no existe, intentar cargar un .env en el cwd por compatibilidad
load_dotenv()


class GeminiService:
    CONTEXTO_MAX_CHARS = 2500

    def __init__(self):
        """Inicializa el servicio de Gemini con la API key del .env"""
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            # No lanzar error aquí, dejar que falle cuando se intente usar
            self.client = None
            self.api_key_missing = True
        else:
            try:
                self.client = Client(api_key=api_key)
                self.api_key_missing = False
                # Se puede ajustar desde .env con GEMINI_MODEL_CANDIDATES="gemini-2.5-flash,gemini-2.0-flash"
                modelos_env = os.getenv("GEMINI_MODEL_CANDIDATES", "")
                self.model_candidates = [
                    m.strip() for m in modelos_env.split(",") if m.strip()
                ] or [
                    "gemini-2.5-flash",
                    "gemini-2.0-flash",
                ]
            except Exception as e:
                self.client = None
                self.api_key_missing = True
                print(f"[GEMINI] Error al inicializar cliente: {e}")

    def generar_respuesta(self, mensaje: str, contexto: dict | None = None) -> str:
        """
        Genera una respuesta usando la API de Google Gemini.
        
        Args:
            mensaje: Mensaje del usuario a procesar
            contexto: Resumen opcional de contexto de app y usuario
            
        Returns:
            str: Respuesta generada por Gemini
            
        Raises:
            Exception: Si hay error al conectar con Gemini
        """
        # Verificar si hay API key configurada
        if self.api_key_missing or not self.client:
            raise GeminiAPIKeyMissingError()
        
        try:
            prompt = self._construir_prompt(mensaje=mensaje, contexto=contexto)

            response = self._generar_con_fallback(prompt)
            
            return response.text if response.text else "No se pudo generar una respuesta."
            
        except Exception as e:
            error_str = str(e)
            
            # Detección específica de error de cuota agotada
            if "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                raise GeminiQuotaExceededError()
            
            # Otros errores de API
            elif "API" in error_str or "key" in error_str.lower():
                raise GeminiAPIConfigError(error_str)
            
            # Error genérico
            else:
                raise GeminiAPIError(error_str)

    def _generar_con_fallback(self, prompt: str):
        """Intenta generar respuesta con modelos alternativos ante UNAVAILABLE."""
        ultimo_error = "Error desconocido"

        for model_name in self.model_candidates:
            try:
                print(f"[GEMINI] Intentando modelo: {model_name}")
                return self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
            except Exception as exc:
                error_str = str(exc)
                ultimo_error = error_str

                if self._es_error_reintentable(error_str):
                    print(f"[GEMINI] Modelo saturado/unavailable ({model_name}), probando fallback...")
                    continue

                # Errores no transitorios: cortar para preservar semantica actual de handlers
                raise

        # Si agotamos candidatos y todos estaban saturados, mantenemos status 503 del handler.
        if self._es_error_not_found(ultimo_error):
            raise GeminiAPIConfigError(ultimo_error)

        raise GeminiQuotaExceededError()

    def _es_error_reintentable(self, error_str: str) -> bool:
        texto = error_str.lower()
        return (
            "unavailable" in texto
            or "high demand" in texto
            or "resource_exhausted" in texto
            or "quota" in texto
            or "503" in texto
            or self._es_error_not_found(error_str)
        )

    def _es_error_not_found(self, error_str: str) -> bool:
        texto = error_str.lower()
        return (
            "not found" in texto
            or "404" in texto
            or "is not found for api version" in texto
            or "not supported for generatecontent" in texto
        )

    def _construir_prompt(self, mensaje: str, contexto: dict | None) -> str:
        """Compone un prompt por secciones y agrega contexto acotado."""
        contexto_serializado = self._serializar_contexto(contexto)

        return f"""
[IDENTIDAD]
Eres un asesor financiero experto llamado 'Asesor Horizon'. Te encuentras en una aplicacion llamada Horizon,
en la seccion AcademIA. Horizon permite probar portfolios ficticios, revisar analisis de activos y realizar
cursos de educacion financiera.

[REGLAS DE SEGURIDAD]
- Ayuda con finanzas, inversion y gestion de portfolios de forma educativa.
- Si el mensaje esta fuera de dominio, redirige amablemente a temas financieros y de aprendizaje.
- Nunca asegures beneficios ni recomiendes inversiones reales.
- Usa solo el resumen de contexto provisto abajo; no inventes ni infieras datos sensibles no presentes.

[CONTEXTO DE APP Y USUARIO]
{contexto_serializado}

[MENSAJE DEL USUARIO]
{mensaje}

[ESTILO DE RESPUESTA]
- Respuesta util, clara y concisa.
- No te presentes en cada mensaje.
- Usa markdown con **doble asterisco** para conceptos clave.
- Separa en parrafos y evita respuestas demasiado extensas.
""".strip()

    def _serializar_contexto(self, contexto: dict | None) -> str:
        """Normaliza y recorta el contexto para controlar coste de tokens."""
        if not contexto:
            return "No disponible"

        contexto_limpio = {
            "app": {
                "secciones": self._limitar_lista(
                    contexto.get("app", {}).get("secciones", []),
                    max_items=7,
                    max_chars_item=35,
                ),
                "total_cursos_publicados": contexto.get("app", {}).get("total_cursos_publicados", 0),
                "activos_buscables": self._limitar_lista_dicts(
                    contexto.get("app", {}).get("activos_buscables", []),
                    max_items=8,
                    campos=("ticker", "nombre"),
                    max_chars_campo=40,
                ),
            },
            "usuario": {
                "nombre": self._truncate(contexto.get("usuario", {}).get("nombre", ""), 40),
                "membresia": self._truncate(contexto.get("usuario", {}).get("membresia", ""), 20),
                "cantidad_portfolios": contexto.get("usuario", {}).get("cantidad_portfolios", 0),
                "portfolios": self._limitar_lista_dicts(
                    contexto.get("usuario", {}).get("portfolios", []),
                    max_items=3,
                    campos=("nombre", "num_activos"),
                    max_chars_campo=45,
                ),
                "cursos_completados": contexto.get("usuario", {}).get("cursos_completados", 0),
                "cursos_completados_titulos": self._limitar_lista(
                    contexto.get("usuario", {}).get("cursos_completados_titulos", []),
                    max_items=5,
                    max_chars_item=45,
                ),
                "progreso_global_cursos_pct": contexto.get("usuario", {}).get("progreso_global_cursos_pct", 0),
            },
        }

        serializado = json.dumps(contexto_limpio, ensure_ascii=True)
        return self._truncate(serializado, self.CONTEXTO_MAX_CHARS)

    def _limitar_lista(self, items: list[Any], max_items: int, max_chars_item: int) -> list[str]:
        resultado = []
        for item in items[:max_items]:
            resultado.append(self._truncate(str(item), max_chars_item))
        return resultado

    def _limitar_lista_dicts(
        self,
        items: list[dict],
        max_items: int,
        campos: tuple[str, ...],
        max_chars_campo: int,
    ) -> list[dict]:
        resultado = []
        for item in items[:max_items]:
            fila = {}
            for campo in campos:
                valor = item.get(campo, "")
                if isinstance(valor, str):
                    fila[campo] = self._truncate(valor, max_chars_campo)
                else:
                    fila[campo] = valor
            resultado.append(fila)
        return resultado

    def _truncate(self, valor: str, max_chars: int) -> str:
        texto = str(valor or "")
        if len(texto) <= max_chars:
            return texto
        return texto[: max_chars - 3] + "..."


# Instancia global del servicio
gemini_service = GeminiService()
