# Asesor Horizon

Este documento describe el flujo actual del asistente conversacional del proyecto, incluyendo preprocesamiento del mensaje, construcción de contexto, composición del prompt y manejo de errores.

## Objetivo

El asistente responde a consultas relacionadas con finanzas, inversión, portfolios y el uso funcional de la plataforma.

El objetivo del diseño actual es mejorar la calidad de las respuestas sin cambiar el contrato principal del endpoint ni introducir persistencia conversacional.

## Componentes principales

- Backend:
  - `ChatService` para orquestar el flujo de negocio.
  - `GeminiService` para construir el prompt y llamar a Gemini.
  - `ChatDAO` para el control de rate limit en base de datos.
  - DAOs de usuario, portfolios, cursos y activos para construir contexto.
- API:
  - `POST /chat` como punto de entrada principal.
  - `ChatMessageRequest` como contrato de entrada.
  - `ChatMessageResponse` como contrato de salida.
- Frontend:
  - `frontend/js/academia.js` para enviar mensajes y renderizar respuestas.
  - `frontend/css/styles.css` para el estilo y ajuste visual de las burbujas.

## Flujo general

1. El frontend envía un `message` al endpoint `POST /chat`.
2. El backend valida autenticación con `auth_service.get_current_user`.
3. `ChatService` aplica preprocesamiento ligero al mensaje.
4. Se valida la longitud máxima permitida.
5. `ChatDAO` verifica e incrementa el rate limit mediante una operación atómica en base de datos.
6. `ChatService` construye un contexto compacto de aplicación y usuario.
7. `GeminiService` compone un prompt dinámico con el contexto.
8. Gemini genera la respuesta.
9. `ChatService` devuelve `ChatMessageResponse` con el mensaje normalizado y la respuesta.

## Preprocesamiento del mensaje

Antes de consultar el rate limit, el mensaje del usuario se normaliza para evitar variaciones triviales que no aportan contenido real.

### Reglas aplicadas

- Recorte de espacios al inicio y al final.
- Normalización de saltos de línea a un único espacio.
- Colapso de secuencias de espacios múltiples en un solo espacio.

### Motivo

Este paso evita que mensajes equivalentes pero con formato distinto consuman recursos de forma innecesaria o alteren el límite por simple ruido textual.

### Validación posterior

Tras el preprocesamiento, se mantiene la validación de longitud máxima de 100 caracteres y la verificación de mensaje vacío.

## Rate limit del chat

El control de tasa no se resuelve en memoria. Se delega a una función RPC en Supabase que ejecuta la comprobación y el incremento de forma atómica.

### Comportamiento

- Se calcula el límite según membresía.
- Se invoca la RPC `verificar_y_registrar_chat_rate_limit`.
- La función devuelve:
  - si el usuario puede enviar el mensaje,
  - cuántos mensajes lleva en la ventana actual,
  - el límite aplicado.

### Ventaja

Este diseño evita condiciones de carrera y mantiene el límite consistente entre varias peticiones concurrentes o varios workers de la aplicación.

## Construcción de contexto

`ChatService` compone un contexto compacto antes de llamar a Gemini.

El contexto se divide en dos bloques:

- Contexto de aplicación.
- Contexto de usuario.

### Contexto de aplicación

Incluye información agregada y no sensible:

- Secciones principales disponibles en la interfaz.
- Número total de cursos publicados.
- Muestra limitada de activos buscables.

### Contexto de usuario

Incluye información resumida del usuario autenticado:

- Nombre.
- Membresía.
- Cantidad de portfolios.
- Resumen limitado de portfolios con número de activos.
- Número de cursos completados.
- Títulos de cursos completados, con límite superior.
- Porcentaje global de progreso en cursos.

### Reglas de resiliencia

Si falla una fuente secundaria, el chat no debe romperse.

Ejemplos:

- Si falla la consulta de cursos, se omite ese bloque.
- Si falla la consulta de portfolios, se devuelve el resto del contexto.
- Si falla la consulta de activos, se conserva el contexto de usuario y cursos.

Este comportamiento permite degradación parcial en lugar de error total.

## Prompt de Gemini

`GeminiService` construye el prompt final por secciones.

### Secciones del prompt

1. Identidad del asistente.
2. Reglas de seguridad.
3. Contexto de aplicación y usuario.
4. Mensaje del usuario.
5. Estilo de respuesta esperado.

### Reglas principales

- Responder solo sobre temas financieros, de inversión o uso de la plataforma.
- No asumir beneficios ni recomendar inversiones reales.
- Usar únicamente el resumen de contexto proporcionado.
- No inferir datos sensibles que no estén presentes en el contexto.
- Mantener un tono breve, claro y educativo.

### Límite de tamaño

El contexto se recorta antes de serializarse al prompt final.

Se aplican límites para evitar exceso de tokens:

- Número máximo de portfolios incluidos.
- Número máximo de activos buscables incluidos.
- Número máximo de títulos de cursos completados.
- Truncado de strings largos.

## Fallback de modelos

La integración con Gemini admite una lista de modelos candidatos.

### Comportamiento

- Se intenta primero el modelo preferido.
- Si el modelo responde con saturación o indisponibilidad temporal, se prueba el siguiente.
- Si la lista se agota, se devuelve el error correspondiente.

### Configuración

La lista puede personalizarse con `GEMINI_MODEL_CANDIDATES` en el archivo de entorno. Por si acaso algún compañero no tiene esta variable de entorno, se incluye una lista de modelos.

## Contrato API

El contrato del endpoint principal no cambia.

### Request

```json
{
  "message": "texto del usuario"
}
```

### Response

```json
{
  "usuario_mensaje": "texto normalizado",
  "respuesta_ia": "respuesta generada"
}
```

## Manejo de errores

Se mantienen los códigos HTTP actuales del flujo del chat.

- `400` para mensaje vacío o demasiado largo.
- `401` para autenticación inválida.
- `404` para usuario no encontrado.
- `429` para rate limit alcanzado.
- `500` para errores de configuración o errores internos.
- `503` para indisponibilidad o saturación del servicio de Gemini.

## Ajuste visual del frontend

Las burbujas del chat están configuradas para adaptarse al contenido y evitar scroll horizontal.

### Regla visual

- El contenedor del chat no debe mostrar overflow horizontal.
- Las burbujas deben respetar el ancho disponible.
- Los textos largos deben partirse en varias líneas.

## Consideraciones operativas

- No hay persistencia conversacional entre sesiones.
- No se expone información sensible completa en el prompt.
- El contexto debe mantenerse compacto y estable.
- El rate limit debe seguir resolviéndose en base de datos.

## Extensión futura

Si en el futuro se amplía el asistente, el orden recomendado es:

1. Añadir nuevos resúmenes en `ChatService`.
2. Mantener el prompt compacto.
3. Evitar introducir nuevas dependencias de transporte o persistencia sin necesidad.
4. Conservar el contrato de `/chat` salvo que exista una razón funcional clara para cambiarlo.