# LINTING_TESTING

## Objetivo

Este documento describe exactamente que valida la capa de linting y control de calidad.

## Alcance de verificacion

El linting verifica solo los directorios criticos del backend:
- backend/daos/
- backend/dtos/
- backend/services/
- backend/exceptions/
- backend/main.py

No se verifican: backend/routes/, backend/models/, scripts/

## Que se testea

### 1) Linting de codigo Python (Pylint)
Script: tests/linting/run_pylint.py

Validaciones principales:
- errores de sintaxis detectables por pylint
- errores o fallos de importacion
- variables no definidas
- problemas de calidad configurados en .pylintrc

Salida:
- resumen por tipo (error, warning, refactor, convention)
- top de incidencias
- opcion de reporte JSON

### 2) Validaciones de linting con pytest
Archivo: tests/linting/test_linting.py

Cobertura actual:
- estructura minima del backend para linting
- existencia de pylint en entorno
- ausencia de errores criticos (error/fatal)
- ausencia de errores de importacion
- ausencia de variables indefinidas
- validacion de sintaxis de archivos Python del alcance

### 3) Hooks pre-commit
Archivo: .pre-commit-config.yaml

Hooks locales:
- pylint

Hooks externos:
- check-ast
- check-json

Cuando se disparan:
- pylint y check-ast: cambios en backend/daos, backend/dtos, backend/services, backend/exceptions o backend/main.py

## Ejecucion

### Linting manual
- python tests/linting/run_pylint.py --verbose
- python tests/linting/run_pylint.py --reports

### Linting con pytest
- pytest tests/linting/test_linting.py -v

### Linting en pre-commit
- pre-commit run --all-files

### Solo un hook
- pre-commit run pylint --all-files
- pre-commit run check-ast --all-files

## Archivos de configuracion

```
.pylintrc                              Reglas de linting (max 120 chars, max 6 args por funcion)
.pre-commit-config.yaml                Configuracion de git hooks automaticos
tests/linting/
  ├── run_pylint.py                    Script para analisis de codigo
  ├── test_linting.py                  Tests con pytest
  ├── setup_linting.py                 Utilidad de configuracion inicial
  └── LINTING_TESTING.md               Este archivo
```

## Verificaciones implementadas

- Errores de sintaxis Python
- Importaciones invalidas
- Variables indefinidas
- Limites de complejidad (max 6 argumentos por funcion, max 10 atributos por clase)
- Conformidad con PEP 8 (seleccionada)

## Animacion de carga en consola

Para evitar sensacion de bloqueo en ejecuciones largas:
- scripts/run_tool_with_fallback.py muestra spinner ASCII durante pylint/pytest
- tests/linting/run_pylint.py usa ese runner
- tests/unit/run_pytest.py usa ese runner
- tests/integration/run_integration.py usa ese runner

## Compatibilidad con y sin venv

El runner scripts/run_tool_with_fallback.py aplica esta politica:
1. Si existe venv local (backend/venv, .venv o venv), usa ese Python
2. Si no existe, usa Python del sistema (fallback)

Esto permite que pre-commit funcione en equipos que no tengan venv montado, siempre que tengan dependencias disponibles en su Python global.

## Resolucion de problemas

| Problema | Solucion |
|----------|----------|
| pylint no encontrado | pip install --upgrade pylint |
| Pre-commit no activo | pre-commit install && pre-commit run --all-files |
| Necesito saltarme control | git commit --no-verify |
