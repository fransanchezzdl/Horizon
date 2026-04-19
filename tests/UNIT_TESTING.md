# UNIT_TESTING

## Objetivo

Este documento describe exactamente que validan los tests unitarios en tests/unit.

## Que se testea

### 1) Endpoints de autenticacion
Archivo: tests/unit/test_auth_endpoints.py

Cobertura actual:
- POST /login
  - respuesta exitosa con access_token y user
  - validacion de email invalido (422)
  - validacion de campos requeridos (422)
- POST /register
  - registro exitoso
  - registro con campos opcionales
  - error controlado de negocio (400)
  - caso de perfil no creado (500)
- POST /auth/change-password
  - exito con Authorization Bearer token mockeado
  - rechazo sin autenticacion (401)

### 2) Endpoints de activos
Archivo: tests/unit/test_activos_endpoints.py

Cobertura actual:
- GET /activos
  - listado completo
  - listado con filtro q
- GET /activos/{ticker}
  - activo existente
  - activo no encontrado (404)
- GET /activos/{ticker}/noticias
  - activo existente y limit parametrizable
  - activo inexistente (404)
  - limit por defecto
- GET /activos/{ticker}/reliability
  - activo inexistente (404)
  - respuesta correcta con payload mockeado
- GET /activos/{ticker}/price-history
  - activo inexistente (404)
  - respuesta correcta con payload mockeado

### 3) Endpoints de usuarios
Archivo: tests/unit/test_usuarios_endpoints.py

Cobertura actual:
- GET /usuarios
  - lista con usuarios validos para response_model
  - lista vacia
  - error de capa DAO (>=500)
- GET /auth/me
  - autenticacion valida + usuario encontrado
  - autenticacion valida + usuario no encontrado (401)
  - sin token (401)

### 4) Endpoints de reflexiones
Archivo: tests/unit/test_reflexion_endpoints.py

Cobertura actual:
- GET /reflexion/aleatoria
  - autenticado y respuesta valida
  - sin autenticacion (401)
- GET /reflexion/{id_reflexion}
  - autenticado y respuesta valida
  - id invalido con auth (422)
  - sin autenticacion (401)

## Como ejecutar

### Con entorno virtual activado

- pytest tests/unit -q

### Con runner con fallback y spinner

- python tests/unit/run_pytest.py

El runner usa venv del proyecto si existe. Si no existe, usa Python del sistema.

## Integracion con pre-commit

- El hook `pytest-unit` ejecuta siempre la suite completa `tests/unit` en cada commit.
- No depende de archivos modificados: se valida en todos los commits.
- Comando manual equivalente:
  - `pre-commit run pytest-unit --all-files`

## Nota sobre mocking

La suite es unitaria: se mockean servicios/DAO para aislar la logica del endpoint y validar:
- codigos HTTP
- estructura de respuesta
- validaciones de entrada
- llamadas esperadas a dependencias
