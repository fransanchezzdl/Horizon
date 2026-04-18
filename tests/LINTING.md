# Guía de Testing de Linting

## Descripción general

Herramientas y procedimientos para verificación de calidad de código en componentes críticos del backend de Horizon. Incluye análisis estático con Pylint y automatización mediante hooks de pre-commit git.

### Alcance de verificación

Se verifican únicamente:
- `backend/daos/` – Capas de acceso a datos
- `backend/dtos/` – Objetos de transferencia de datos
- `backend/services/` – Lógica de negocio
- `backend/exceptions/` – Excepciones personalizadas
- `backend/main.py` – Archivo principal

Están excluidos: `routes/`, `models/`, `scripts/`, `tests/`

---

## Instalación inicial (una sola vez)

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

Instala: pylint, pre-commit, pytest

### 2. Instalar git hooks

```bash
pre-commit install
```

Resultado: Los hooks de pre-commit se ejecutarán automáticamente antes de cada commit, verificando cambios en los directorios especificados.

---

## Métodos de ejecución

### Opción 1: Script manual

Ideal para exploración interactiva y diagnóstico.

```bash
# Análisis básico
python tests/linting/run_pylint.py

# Con detalles (verbose)
python tests/linting/run_pylint.py --verbose

# Guardar reporte JSON
python tests/linting/run_pylint.py --reports
```

Salida típica:
```
Linting completado
Total de problemas: 12
Directorios verificados: daos, dtos, services, exceptions, main.py

Resumen por tipo:
   warning: 8
   refactor: 4

Primeros 10 problemas:
   1. [warning] backend/daos/usuario_dao.py: línea 42 - Unused variable 'temp'
```

### Opción 2: Tests con pytest

Para integración en CI/CD y resultados estructurados.

```bash
# Ejecutar todos los tests
pytest tests/linting/test_linting.py -v

# Ejecutar categoría específica
pytest tests/linting/test_linting.py::TestPylintSyntax -v

# Sin parar en primer error
pytest tests/linting/test_linting.py --tb=short
```

Tests disponibles:
- test_backend_structure: Verifica estructura requerida
- test_pylint_installed: Verifica disponibilidad de pylint
- test_no_critical_errors: Sin errores críticos
- test_imports_valid: Sin errores de importación
- test_undefined_variables: Sin variables indefinidas
- test_all_python_files_valid_syntax: Sintaxis Python válida

### Opción 3: Pre-commit hook (automático)

Se ejecuta automáticamente en cada commit:

```bash
git add backend/daos/
git commit -m "Mejora en usuario_dao"
```

Resultado exitoso:
```
Pylint....................................................................PASSED
Check Python syntax....................................................PASSED
```

Resultado con errores:
```
pylint....................................................................FAILED
- hook id: pylint
- exit code: 1
```

Para ver detalles:
```bash
pre-commit run pylint --all-files --verbose
```

---

## Configuración

### Archivo .pylintrc

Define reglas de linting para Pylint. Configuraciones principales:

```ini
[FORMAT]
max-line-length=120          # Máximo caracteres por línea

[DESIGN]
max-args=6                   # Máximo argumentos por función
max-attributes=10            # Máximo atributos por clase
max-locals=15                # Máximo variables locales

[BASIC]
good-names=i,j,k,ex,Run,_   # Nombres de variable permitidos simples
```

Reglas deshabilitadas:
- trailing-whitespace
- missing-final-newline
- wildcard-import
- wrong-import-order

Para personalizar: Edita `.pylintrc` en la raíz del proyecto.

### Archivo .pre-commit-config.yaml

Especifica qué archivos se verifican:

```yaml
files: ^backend/(daos|dtos|main\.py|services|exceptions)/
```

Solo se verifica contenido que coincida con este patrón.

---

## Interpretación de resultados

### Tipos de problemas

| Tipo | Severidad | Descripción |
|------|-----------|-------------|
| error | Alta | Errores reales que rompen el código |
| fatal | Alta | Fallos críticos del análisis |
| warning | Media | Código sospechoso |
| convention | Baja | Violaciones de PEP 8 |
| refactor | Baja | Sugerencias de mejora |

### Ejemplo de mensaje

```json
{
  "type": "warning",
  "module": "backend.daos.usuario_dao",
  "obj": "get_user_by_id",
  "line": 42,
  "column": 8,
  "symbol": "unused-variable",
  "message": "Unused variable 'temp_data'"
}
```

---

## Optimización de rendimiento

### Por qué es rápido ahora

1. Pre-commit solo verifica archivos modificados en directorios especificados
2. Se excluyen directorios innecesarios (routes, models, scripts)
3. Pylint ejecuta en paralelo (jobs=4)
4. Reglas no críticas deshabilitadas

### Ejecutar análisis específico

```bash
# Solo verificar un directorio
pylint backend/daos/

# Solo un archivo
pylint backend/main.py

# Generar solo estadísticas
pylint --exit-zero backend/daos/
```

---

## Resolución de problemas

### "pylint: command not found"

```bash
pip install --upgrade pylint
```

### Pre-commit hook no se ejecuta

```bash
pre-commit uninstall
pre-commit install
pre-commit run --all-files
```

### Omitir verificación

```bash
git commit --no-verify  # Solo cuando sea absolutamente necesario
```

### Generar reporte formal

```bash
python tests/linting/run_pylint.py --reports
# Reporte: tests/linting/pylint_report.json
```

### Ver qué se verifica en pre-commit

```bash
pre-commit run pylint --all-files --verbose
```

---

## Estructura de archivos

```
Horizon/
├── .pylintrc                    Configuración de pylint
├── .pre-commit-config.yaml      Configuración de hooks
├── tests/
│   ├── LINTING.md               Este archivo
│   └── linting/
│       ├── run_pylint.py        Script manual
│       ├── test_linting.py      Tests pytest
│       ├── setup_linting.py     Setup inicial
│       └── README.md            Quick start
└── requirements.txt             Dependencias
```

---ython tests/linting/run_pylint.py --verbose    # Check cambios locales
   ```

2. **Para debugging:**
   ```bash
   pylint backend/daos/usuario_dao.py    # Un archivo específico
   ```

3. **En CI/CD:**
   ```bash
   pytest tests/linting/test_linting.py --tb=short
   ```

4. **Personalizar reglas:**
   - Edita `.pylintrc` sección `[MESSAGES CONTROL]`
   - Agrega reglas a `disable=` si son innecesarias para tu contexto
   pytest tests/linting/test_linting.py --tb=short
   ```

4. **Personalizar reglas:**
   - Edita `.pylintrc` sección `[MESSAGES CONTROL]`
   - Agrega reglas a `disable=` si son innecesarias

---

## Referencias

- Documentación de Pylint: https://pylint.pycqa.org/
- Pre-commit documentation: https://pre-commit.com/
- PEP 8 Style Guide: https://www.python.org/dev/peps/pep-0008/
