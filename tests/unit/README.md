## Tests Unitarios - Endpoints del Backend

Tests unitarios para los endpoints de FastAPI usando pytest y unittest.mock.

### Estructura

```
tests/unit/
├── conftest.py                      Fixtures compartidas y configuración
├── test_auth_endpoints.py          Tests para login, register, cambiar contraseña
├── test_activos_endpoints.py       Tests para endpoints de activos
├── test_usuarios_endpoints.py      Tests para endpoints de usuarios
├── test_reflexion_endpoints.py     Tests para endpoints de reflexiones
└── README.md                        Este archivo
```

### Ejecutar los tests

**Todos los tests unitarios:**
```bash
pytest tests/unit/ -v
```

**Tests de un archivo específico:**
```bash
pytest tests/unit/test_activos_endpoints.py -v
```

**Tests de una clase específica:**
```bash
pytest tests/unit/test_activos_endpoints.py::TestListarActivos -v
```

**Tests de un caso específico:**
```bash
pytest tests/unit/test_activos_endpoints.py::TestListarActivos::test_listar_activos_sin_filtro -v
```

**Con cobertura de código:**
```bash
pytest tests/unit/ --cov=backend --cov-report=html
# Abre: htmlcov/index.html
```

### Patrones de Testing

#### 1. Estructura Arrange-Act-Assert

```python
def test_ejemplo(self, client, mock_activo_service):
    # Arrange: Preparar datos y mocks
    activos_mock = [{"ticker": "AAPL"}]
    mock_activo_service.listar_activos.return_value = activos_mock
    
    with patch("backend.main.activo_service", mock_activo_service):
        # Act: Ejecutar la acción
        response = client.get("/activos")
    
    # Assert: Verificar resultados
    assert response.status_code == 200
    assert response.json() == activos_mock
```

#### 2. Mocking de Dependencias

Se usan fixtures de conftest.py para inyectar mocks:

```python
def test_algo(self, client, mock_usuario_dao):
    # mock_usuario_dao es inyectado
    mock_usuario_dao.obtener_todos.return_value = []
```

#### 3. Parcheo de Servicios

Reemplazamos los servicios en el módulo principal:

```python
with patch("backend.main.activo_service", mock_activo_service):
    response = client.get("/activos")
```

### Cobertura Actual

Los tests cubren:
- GET /activos (listado con y sin filtro)
- GET /activos/{ticker} (obtención y 404)
- POST /login (exitoso y validaciones)
- POST /register (exitoso y errores)
- GET /usuarios
- GET /reflexion/{id}

Falta implementar:
- Endpoints protegidos (requieren inyección de Depends())
- Endpoints de upload de archivos
- Endpoints de portfolios

### Limitaciones Conocidas

1. **Dependencias en endpoints protegidos**
   
   Los endpoints que usan `Depends(auth_service.get_current_user)` requieren montar 
   especialmente el cliente. Ver ejemplos en test_usuarios_endpoints.py comentados.

2. **UploadFile**
   
   Los tests de endpoints con `UploadFile` requieren preparación especial del cliente.

3. **Fixtures de conftest**
   
   Los mocks en conftest no están conectados automáticamente. Se usan con `patch()`.

### Mejoras Futuras

1. Implementar TestClient overrides para endpoints protegidos
2. Agregar tests para endpoints de upload
3. Agregar tests de integración
4. Implementar test de errores de base de datos
5. Agregar tests de validación de Pydantic

### Referencias

- pytest: https://docs.pytest.org/
- FastAPI TestClient: https://fastapi.tiangolo.com/advanced/testing-dependencies/
- unittest.mock: https://docs.python.org/3/library/unittest.mock.html
