# Autenticación en Horizon

Este documento resume el flujo de autenticación actual del proyecto y define el patrón que debe mantenerse al crear nuevas páginas, endpoints o servicios.

## Objetivo

La autenticación está centralizada en backend. El frontend nunca decide por sí solo si una sesión es válida; siempre consulta al backend, que valida el token contra Supabase Auth.

## Componentes principales

- Backend:
  - `AuthService.iniciar_sesion(email, password)` para login.
  - `AuthService.registrar_usuario(...)` para registro.
  - `AuthService.get_current_user(...)` como dependencia para endpoints protegidos.
  - `GET /auth/me` para validar token y obtener datos de usuario.
- Frontend:
  - `window.validateAuthToken()` para validar sesión al cargar páginas protegidas.
  - `window.fetchWithAuth(url, options)` para llamadas autenticadas.
  - `window.getAccessToken()`, `window.setAccessToken(token)` y `window.clearAuthSession()` para sesión local.

## Flujo 1: login y registro

### Login

1. El frontend envía credenciales a `POST /login`.
2. El backend valida credenciales con Supabase Auth.
3. Si son correctas, devuelve `access_token` y perfil de usuario.
4. El frontend guarda el token y ejecuta `validateAuthToken()`.
5. Solo si la validación es correcta se permite continuar a una página protegida.

### Registro

1. El frontend envía datos a `POST /register`.
2. El backend crea usuario en Supabase Auth y perfil en base de datos.
3. El backend devuelve token y datos de usuario.
4. El frontend guarda token y valida con `validateAuthToken()` antes de redirigir.

## Flujo 2: carga de páginas protegidas

Cada página protegida debe validar sesión al inicio.

Patrón recomendado:

1. Ejecutar `validateAuthToken()` en la inicialización de la página.
2. Si no es válido:
   - limpiar sesión con `clearAuthSession()`
   - redirigir a `login.html`
3. Si es válido:
   - guardar datos del usuario en caché local (`setCurrentUserData`)
   - continuar con la carga de datos y renderizado.

Con este enfoque, un token expirado o revocado no permite acceder a la interfaz protegida.

## Flujo 3: llamadas API autenticadas

Todas las llamadas a endpoints protegidos deben usar `fetchWithAuth`.

Comportamiento de `fetchWithAuth`:

1. Obtiene el token desde almacenamiento local.
2. Agrega el header `Authorization: Bearer <token>`.
3. Ejecuta la solicitud.
4. Si recibe `401`:
   - limpia sesión local
   - redirige a login
   - corta el flujo actual.

Esto evita duplicar lógica de autenticación en cada archivo JS.

## Validación en backend

El backend protege endpoints con la dependencia `Depends(auth_service.get_current_user)`.

Esa dependencia:

1. Lee el header `Authorization`.
2. Verifica formato `Bearer <token>`.
3. Valida token con Supabase (`auth.get_user(token)`).
4. Extrae `user_id` autenticado.
5. Devuelve `401` si el token no es válido.

## Regla para nuevos endpoints y servicios

Si un endpoint requiere identidad de usuario:

1. Debe incluir `user_id: str = Depends(auth_service.get_current_user)`.
2. Debe usar ese `user_id` para filtrar y operar datos del usuario autenticado.
3. No debe confiar en `id_usuario` enviado por cliente para control de acceso.

Si un endpoint es público, documentarlo explícitamente como público.

## Regla para nuevas páginas frontend

Si una página consume datos privados o acciones de usuario:

1. Validar sesión en carga con `validateAuthToken()`.
2. Realizar llamadas API con `fetchWithAuth()`.
3. No leer ni validar token manualmente en cada función.

## Manejo de sesión

- `access_token` se almacena en `localStorage`.
- El perfil de usuario puede cachearse en `localStorage` para UI.
- Ante cierre de sesión o token inválido, se eliminan ambos.

## Resultado esperado del sistema

- Una sesión solo se considera válida si backend la valida.
- Cualquier endpoint protegido aplica la misma verificación.
- Cualquier página protegida aplica la misma verificación al entrar.
- El patrón escala sin cambios estructurales al añadir nuevas funcionalidades.