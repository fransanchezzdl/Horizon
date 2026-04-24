"""Servicio de chat que orquesta la lógica de negocio del chatbot."""

import re

from ..dtos.chat_dto import ChatMessageResponse
from ..exceptions import (
    RateLimitExceededError,
    MessageTooLongError,
    EmptyMessageError,
    UsuarioNoEncontradoError
)


class ChatService:
    """
    Servicio que maneja la lógica de negocio del chatbot.
    Orquesta los DAOs (usuario, chat) y servicios externos (Gemini).
    """
    
    APP_SECCIONES = [
        "Dashboard",
        "Analisis de Ticker",
        "Portfolio",
        "AcademIA",
        "Ajustes",
        "Ayuda",
        "Perfil",
    ]

    CONTEXTO_LIMITES = {
        "portfolios_resumen": 3,
        "activos_buscables": 10,
        "cursos_completados_titulos": 5,
    }

    def __init__(
        self,
        usuario_dao_instance,
        chat_dao_instance,
        gemini_service_instance,
        portfolio_dao_cls=None,
        curso_dao_cls=None,
        activo_dao_cls=None,
    ):
        self.usuario_dao = usuario_dao_instance
        self.chat_dao = chat_dao_instance
        self.gemini_service = gemini_service_instance
        self.portfolio_dao = portfolio_dao_cls
        self.curso_dao = curso_dao_cls
        self.activo_dao = activo_dao_cls
    
    def procesar_mensaje(self, id_usuario: str, mensaje: str) -> ChatMessageResponse:
        """
        Procesa un mensaje del usuario y obtiene respuesta de Gemini.
        
        Flujo:
        1. Valida longitud del mensaje
        2. Obtiene información del usuario (membresía)
        3. Verifica límite de rate limiting
        4. Registra el mensaje
        5. Llama a Gemini para obtener respuesta
        6. Devuelve la respuesta
        
        Args:
            id_usuario: ID del usuario autenticado
            mensaje: Mensaje del usuario
            
        Returns:
            ChatMessageResponse con el mensaje y la respuesta de la IA
            
        Raises:
            Exception: Si hay errores de validación, rate limiting, usuario no encontrado,
                      o problemas con el servicio de IA
        """
        # 1. Preprocesar y validar longitud del mensaje
        mensaje_preprocesado = self._preprocesar_mensaje(mensaje)
        self._validar_longitud_mensaje(mensaje_preprocesado)
        
        # 2. Obtener usuario (necesitamos su membresía para rate limiting)
        usuario = self.usuario_dao.obtener_por_id(id_usuario)
        if not usuario:
            raise UsuarioNoEncontradoError(id_usuario)
        
        # 3. Verificar e incrementar límite de mensajes en BD (operación atómica)
        puede_enviar, mensajes_enviados, limite = self.chat_dao.verificar_limite_mensajes(
            id_usuario=id_usuario,
            membresia=usuario.membresia
        )
        
        if not puede_enviar:
            raise RateLimitExceededError(mensajes_enviados, limite, usuario.membresia)

        # 4. Construir contexto compacto de app/usuario (con degradacion resiliente)
        contexto = self._construir_contexto_chat(id_usuario=id_usuario, usuario=usuario)

        # 5. Generar respuesta con Gemini
        respuesta_ia = self.gemini_service.generar_respuesta(
            mensaje=mensaje_preprocesado,
            contexto=contexto,
        )
        
        # 6. Devolver respuesta
        return ChatMessageResponse(
            usuario_mensaje=mensaje_preprocesado,
            respuesta_ia=respuesta_ia
        )

    def _preprocesar_mensaje(self, mensaje: str) -> str:
        """Aplica preprocesamiento ligero para evitar variaciones triviales."""
        if mensaje is None:
            return ""

        normalizado = mensaje.strip()
        normalizado = normalizado.replace("\r\n", "\n").replace("\r", "\n")
        normalizado = re.sub(r"\n+", " ", normalizado)
        normalizado = re.sub(r"\s{2,}", " ", normalizado)
        return normalizado.strip()

    def _construir_contexto_chat(self, id_usuario: str, usuario) -> dict:
        """Construye un contexto compacto de app y usuario para el prompt."""
        contexto = {
            "app": {
                "secciones": self.APP_SECCIONES,
                "total_cursos_publicados": 0,
                "activos_buscables": [],
            },
            "usuario": {
                "nombre": usuario.nombre,
                "membresia": usuario.membresia,
                "cantidad_portfolios": 0,
                "portfolios": [],
                "cursos_completados": 0,
                "cursos_completados_titulos": [],
                "progreso_global_cursos_pct": 0.0,
            },
        }

        cursos_publicados = []

        # Datos de cursos/app + resumen de progreso de usuario
        if self.curso_dao:
            try:
                cursos_publicados = self.curso_dao.listar_cursos() or []
                contexto["app"]["total_cursos_publicados"] = len(cursos_publicados)
            except Exception as exc:
                print(f"[CHAT] No se pudo obtener cursos publicados: {exc}")

            try:
                progresos = self.curso_dao.obtener_progresos_usuario(id_usuario) or []
                total_registros = len(progresos)
                completados = [p for p in progresos if p.get("completado") is True]

                contexto["usuario"]["cursos_completados"] = len(completados)
                if total_registros > 0:
                    contexto["usuario"]["progreso_global_cursos_pct"] = round(
                        (len(completados) / total_registros) * 100,
                        2,
                    )

                titulos_por_id = {
                    curso.get("id"): curso.get("titulo", "Curso sin titulo")
                    for curso in cursos_publicados
                }
                titulos_completados = []
                for progreso in completados:
                    id_curso = progreso.get("id_curso")
                    titulo = titulos_por_id.get(id_curso)
                    if titulo:
                        titulos_completados.append(titulo)

                limite_titulos = self.CONTEXTO_LIMITES["cursos_completados_titulos"]
                contexto["usuario"]["cursos_completados_titulos"] = titulos_completados[:limite_titulos]
            except Exception as exc:
                print(f"[CHAT] No se pudo obtener progreso de cursos del usuario: {exc}")

        # Datos de portfolios de usuario
        if self.portfolio_dao:
            try:
                portfolios = self.portfolio_dao.obtener_por_usuario(id_usuario) or []
                contexto["usuario"]["cantidad_portfolios"] = len(portfolios)

                limite_portfolios = self.CONTEXTO_LIMITES["portfolios_resumen"]
                resumen_portfolios = []
                for portfolio in portfolios[:limite_portfolios]:
                    id_portfolio = portfolio.get("id_portfolio")
                    activos_portfolio = []
                    try:
                        if id_portfolio is not None:
                            activos_portfolio = self.portfolio_dao.obtener_stocks(id_portfolio) or []
                    except Exception as exc:
                        print(f"[CHAT] No se pudieron obtener activos del portfolio {id_portfolio}: {exc}")

                    resumen_portfolios.append(
                        {
                            "nombre": portfolio.get("nombre_portfolio", "Portfolio sin nombre"),
                            "num_activos": len(activos_portfolio),
                        }
                    )

                contexto["usuario"]["portfolios"] = resumen_portfolios
            except Exception as exc:
                print(f"[CHAT] No se pudieron obtener portfolios del usuario: {exc}")

        # Muestra de activos buscables de la app
        if self.activo_dao:
            try:
                limite_activos = self.CONTEXTO_LIMITES["activos_buscables"]
                activos = self.activo_dao.obtener_todos(limit=limite_activos) or []
                contexto["app"]["activos_buscables"] = [
                    {
                        "ticker": activo.ticker,
                        "nombre": activo.nombre_completo,
                    }
                    for activo in activos
                ]
            except Exception as exc:
                print(f"[CHAT] No se pudieron obtener activos buscables: {exc}")

        return contexto
    
    def _validar_longitud_mensaje(self, mensaje: str) -> None:
        """
        Valida que el mensaje no exceda 100 caracteres.
        
        Args:
            mensaje: Mensaje del usuario
            
        Raises:
            Exception: Si el mensaje excede 100 caracteres o está vacío
        """
        longitud = len(mensaje.strip())
        if longitud > 100:
            raise MessageTooLongError(longitud)
        if longitud == 0:
            raise EmptyMessageError()

