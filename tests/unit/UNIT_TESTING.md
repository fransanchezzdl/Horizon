# UNIT_TESTING

## Objetivo

Este documento describe exactamente que validan los tests unitarios en tests/unit.

## Estructura

```
tests/unit/
├── conftest.py                      Fixtures compartidas y configuracion
├── test_auth_endpoints.py           Tests para login, register, cambiar contrasena
├── test_activos_endpoints.py        Tests para endpoints de activos
├── test_usuarios_endpoints.py       Tests para endpoints de usuarios
├── test_reflexion_endpoints.py      Tests para endpoints de reflexiones
└── UNIT_TESTING.md                  Este archivo
```

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

### Con cobertura de codigo

- pytest tests/unit --cov=backend --cov-report=html

## Patrones de testing

### 1) Estructura Arrange-Act-Assert

```python
def test_ejemplo(self, client, mock_activo_service):
    # Arrange: preparar datos y mocks
    activos_mock = [{"ticker": "AAPL"}]
    mock_activo_service.listar_activos.return_value = activos_mock

    with patch("backend.main.activo_service", mock_activo_service):
        # Act: ejecutar la accion
        response = client.get("/activos")

    # Assert: verificar resultados
    assert response.status_code == 200
    assert response.json() == activos_mock
```

### 2) Mocking de dependencias

Se usan fixtures de conftest.py para inyectar mocks:

```python
def test_algo(self, client, mock_usuario_dao):
    # mock_usuario_dao es inyectado
    mock_usuario_dao.obtener_todos.return_value = []
```

### 3) Parcheo de servicios

Reemplazamos los servicios en el modulo principal:

```python
with patch("backend.main.activo_service", mock_activo_service):
    response = client.get("/activos")
```

## Integracion con pre-commit

- El hook pytest-unit ejecuta siempre la suite completa tests/unit en cada commit.
- No depende de archivos modificados: se valida en todos los commits.
- Comando manual equivalente:
  - pre-commit run pytest-unit --all-files

## Nota sobre mocking

La suite es unitaria: se mockean servicios/DAO para aislar la logica del endpoint y validar:
- codigos HTTP
- estructura de respuesta
- validaciones de entrada
- llamadas esperadas a dependencias

## Limitaciones conocidas

1) Dependencias en endpoints protegidos

Los endpoints que usan Depends(auth_service.get_current_user) requieren montar especialmente el cliente. Ver ejemplos en test_usuarios_endpoints.py comentados.

2) UploadFile

Los tests de endpoints con UploadFile requieren preparacion especial del cliente.

3) Fixtures de conftest

Los mocks en conftest no estan conectados automaticamente. Se usan con patch().

## Mejoras futuras

1) Implementar TestClient overrides para endpoints protegidos
2) Agregar tests para endpoints de upload
3) Agregar tests de integracion
4) Implementar test de errores de base de datos
5) Agregar tests de validacion de Pydantic

## Referencias

- pytest: https://docs.pytest.org/
- FastAPI TestClient: https://fastapi.tiangolo.com/advanced/testing-dependencies/
- unittest.mock: https://docs.python.org/3/library/unittest.mock.html
