# INTEGRATION_TESTING

## Objetivo

Validar flujos completos entre capas (API, servicios y DAOs) sin depender de servicios externos reales en tiempo de test.

## Cobertura actual

La carpeta tests/integration/ cubre:
- Flujos API de autenticacion y perfil
- Flujos API de avatar y portfolio
- Integracion ligera de AuthService simulando respuestas de Supabase (db.auth.*) con mocks
- Rendimiento basico de endpoints criticos con umbrales conservadores para detectar regresiones claras

## Estructura

- tests/integration/conftest.py: fixtures compartidas y cliente de pruebas
- tests/integration/test_auth_profile_integration.py: flujo auth + profile
- tests/integration/test_avatar_portfolio_integration.py: flujo avatar + portfolio
- tests/integration/test_supabase_light_integration.py: integracion ligera de AuthService con mocks de Supabase
- tests/integration/test_performance_basic_integration.py: checks de latencia basica
- tests/integration/run_integration.py: runner con animacion ASCII (usa scripts/run_tool_with_fallback.py)
- tests/integration/INTEGRATION_TESTING.md: este archivo

## Que se testea

### 1) Flujo login -> auth/me
Archivo: tests/integration/test_auth_profile_integration.py

Cobertura:
- Login exitoso (POST /login) con respuesta JWT + perfil
- Reutilizacion del token en endpoint protegido (GET /auth/me)
- Caso sin token (GET /auth/me => 401)

### 2) Flujo avatar + portfolio
Archivo: tests/integration/test_avatar_portfolio_integration.py

Cobertura:
- Subida de avatar con multipart (POST /usuarios/me/avatar)
- Creacion y lectura de portfolio autenticado (POST /portfolios + GET /portfolios/{id})

## Ejecucion local

Ejecutar toda la suite de integracion:

```bash
python tests/integration/run_integration.py
```

Ejecutar via pytest directamente:

```bash
pytest tests/integration -q --disable-warnings -ra
```

Ejecutar un archivo concreto:

```bash
pytest tests/integration/test_supabase_light_integration.py -q
```

Ejecutar un test concreto:

```bash
pytest tests/integration/test_performance_basic_integration.py::test_endpoint_activos_basic_performance -q
```

## Integracion con pre-commit

El hook pytest-integration ejecuta siempre la suite completa de tests/integration antes de permitir el commit.

Comando manual equivalente:

```bash
pre-commit run pytest-integration --all-files
```

## Notas de estabilidad

- Los tests de rendimiento usan limites amplios (1.5s) para minimizar falsos positivos.
- No se realizan llamadas reales a Supabase, por lo que los resultados no dependen de red ni credenciales.
- El objetivo es detectar regresiones funcionales y de performance evidentes, no benchmarking fino.
