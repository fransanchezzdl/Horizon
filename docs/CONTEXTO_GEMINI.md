## Plan: Contexto Enriquecido Para Chat Gemini

Extender el flujo actual del chat sin rediseños: mantener endpoint y contrato principal, añadir preprocesamiento ligero del mensaje, construir contexto de app y usuario en ChatService, e inyectarlo en GeminiService mediante un prompt dinámico y acotado. Reutilizar DAOs/servicios ya existentes para minimizar riesgo y cambios.

**Steps**
1. Fase 1 - Diagnóstico técnico y límites de diseño (base de continuidad)
2. Confirmar restricciones no funcionales actuales del chat: límite de 100 caracteres, rate limit en memoria y respuesta síncrona de Gemini. Marcar explícitamente que no se toca persistencia ni arquitectura de transporte en esta iteración.
3. Definir alcance de preprocesamiento mínimo: trim, normalización de espacios repetidos y sanitización ligera de saltos de línea, preservando la validación de longitud existente. Este preprocesamiento debe correr antes de rate limit para evitar variaciones triviales de texto.
4. Fase 2 - Construcción de contexto (backend, punto único)
5. En ChatService, introducir un constructor de contexto interno (ej. método privado) que retorne un resumen compacto con:
6. Datos de app: secciones principales disponibles en la UI (Dashboard, Análisis de Ticker, Portfolio, AcademIA, Ajustes, Ayuda, Perfil), total de cursos publicados, y muestra de activos buscables (todos los activos de la tabla activos).
7. Datos de usuario: nombre, membresía, cantidad de portfolios, resumen de portfolios (nombre y número de activos por portfolio, limitado a N), cursos completados y progreso global de cursos.
8. Para mantener continuidad, obtener datos desde componentes ya existentes: UsuarioDAO, PortfolioDAO/PortfolioService, CursoDAO/CursoService, ActivoDAO/ActivoService. Evitar nuevos endpoints y evitar cambios de esquema de BD.
9. Agregar manejo resiliente: si falla alguna fuente secundaria (por ejemplo activos o cursos), no romper el chat; degradar el contexto parcial y continuar.
10. Fase 3 - Integración con Gemini (sin romper contrato público)
11. Extender GeminiService para aceptar un segundo parámetro opcional de contexto (dict serializable) y generar prompt dinámico por secciones: identidad del asistente, reglas de seguridad, contexto de app, contexto de usuario, y pregunta del usuario.
12. Eliminar del prompt la instrucción que hoy dice que el modelo no recibe datos del usuario (pasará a ser falsa), y reemplazarla por una regla de privacidad: usar solo el resumen provisto, sin inferencias sensibles.
13. Limitar tamaño del contexto (top N + recorte de strings) para controlar tokens/coste; mantener estilo de respuesta actual.
14. Fase 4 - Encaje con frontend y contrato API
15. Mantener sin cambios el contrato principal de POST /chat (message en body). No se requiere tocar frontend para esta iteración.
16. Como opción futura no bloqueante, valorar flags opcionales en ChatMessageRequest (por ejemplo include_app_context/include_user_context), pero dejarlo fuera del alcance mínimo para evitar dispersión.
17. Fase 5 - Verificación y regresión
18. Validar manualmente casos clave: mensaje financiero normal, mensaje fuera de dominio, usuario sin portfolios, usuario sin progreso, fallo parcial de datos secundarios.
19. Confirmar que no cambia el shape de ChatMessageResponse y que se mantienen códigos de error actuales (400/401/429/500/503).
20. Revisar logs para asegurar que no se expone información sensible completa (solo agregados y resúmenes).

**Relevant files**
- d:/Visual Studio/Proyectos/Horizon/backend/services/chat_service.py — punto principal para preprocesar mensaje y componer contexto de app/usuario antes de invocar Gemini.
- d:/Visual Studio/Proyectos/Horizon/backend/services/gemini_service.py — prompt dinámico, reglas de uso de contexto y límite de tamaño del contexto.
- d:/Visual Studio/Proyectos/Horizon/backend/main.py — wiring de dependencias; inyectar servicios/DAO adicionales en ChatService si se decide por constructor.
- d:/Visual Studio/Proyectos/Horizon/backend/dtos/chat_dto.py — solo si se añaden flags opcionales de contexto (no requerido en alcance mínimo).
- d:/Visual Studio/Proyectos/Horizon/backend/services/curso_service.py — reutilizar obtener_resumen_usuario para cursos completados.
- d:/Visual Studio/Proyectos/Horizon/backend/daos/curso_dao.py — listar cursos y progresos para resumen global.
- d:/Visual Studio/Proyectos/Horizon/backend/services/portfolio_service.py — listar portfolios por usuario y detalle agregado.
- d:/Visual Studio/Proyectos/Horizon/backend/daos/portfolio_dao.py — fuente de portfolios y posiciones.
- d:/Visual Studio/Proyectos/Horizon/backend/services/activo_service.py — listado/búsqueda de activos para muestra contextual.
- d:/Visual Studio/Proyectos/Horizon/backend/daos/activo_dao.py — fuente de activos disponibles.
- d:/Visual Studio/Proyectos/Horizon/frontend/js/academia.js — referencia de flujo actual del chat; sin cambios obligatorios en alcance mínimo.
- d:/Visual Studio/Proyectos/Horizon/frontend/js/layout.js — fuente de secciones navegables para contexto de app.

**Verification**
1. Ejecutar validación de errores de backend completo tras cambios para detectar wiring/imports rotos.
2. Probar POST /chat autenticado con usuario con portfolios y cursos completados; verificar respuesta contextualizada sin romper límite de 100 caracteres de entrada.
3. Probar POST /chat con usuario recién creado (sin portfolios/progreso); validar fallback de contexto vacío sin excepciones.
4. Probar escenarios de error de Gemini (sin API key/cuota) y asegurar que se conservan excepciones y códigos HTTP existentes.
5. Medir rápidamente latencia de /chat antes/después con 5-10 requests para confirmar impacto aceptable del contexto adicional.

**Decisions**
- Confirmado: secciones de app desde catálogo fijo en backend (no derivación dinámica desde frontend).
- Confirmado: incluir cursos completados como conteo + títulos completados (además de progreso agregado).
- Confirmado: activos buscables como top N recientes por updated_at.
- Excluido en esta iteración: memoria conversacional persistente, nuevos esquemas BD, cambios de UX/chat frontend, rediseño de rate limit.
- Supuesto operativo: mejorar personalización con contexto en tiempo real sin exponer datos sensibles detallados.
