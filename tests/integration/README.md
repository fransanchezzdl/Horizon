# Integration Tests

## Objetivo

Validar flujos completos de API (request/response real con FastAPI `TestClient`) manteniendo aislamiento mediante mocks en servicios externos.

## Qué se testea

### 1) Flujo login -> auth/me
Archivo: `tests/integration/test_auth_profile_integration.py`

Cobertura:
- Login exitoso (`POST /login`) con respuesta JWT + perfil
- Reutilización del token en endpoint protegido (`GET /auth/me`)
- Caso sin token (`GET /auth/me` => 401)

### 2) Flujo avatar + portfolio
Archivo: `tests/integration/test_avatar_portfolio_integration.py`

Cobertura:
- Subida de avatar con multipart (`POST /usuarios/me/avatar`)
- Creación y lectura de portfolio autenticado (`POST /portfolios` + `GET /portfolios/{id}`)

## Cómo ejecutar

### Suite completa de integración

```bash
pytest tests/integration -q
```

### Ejecutar un archivo

```bash
pytest tests/integration/test_auth_profile_integration.py -q
```

### Ejecutar un test concreto

```bash
pytest tests/integration/test_avatar_portfolio_integration.py::test_upload_avatar_flow -q
```

## Relación con pre-commit

Hay un hook dedicado `pytest-integration` que se dispara cuando cambian archivos de:
- backend/daos
- backend/dtos
- backend/services
- backend/exceptions
- backend/main.py
- tests/integration

Esto permite detectar regresiones de flujo API antes del commit.
