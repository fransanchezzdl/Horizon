# LINTING_TESTING

## Objetivo

Este documento describe exactamente que valida la capa de linting y control de calidad.

## Que se testea

### 1) Linting de codigo Python (Pylint)
Script: tests/linting/run_pylint.py

Alcance actual:
- backend/daos/
- backend/dtos/
- backend/services/
- backend/exceptions/
- backend/main.py

Validaciones principales:
- errores de sintaxis detectables por pylint
- errores/fallos de importacion
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
- pylint y check-ast: cambios en backend/daos, dtos, services, exceptions o main.py

Nota:
- el disparo y alcance de `pytest-unit` y `pytest-integration` se documenta en tests/UNIT_TESTING.md y tests/INTEGRATION_TESTING.md

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

## Como ejecutar

### Linting manual
- python tests/linting/run_pylint.py --verbose
- python tests/linting/run_pylint.py --reports

### Linting en pre-commit
- pre-commit run --all-files

### Solo un hook
- pre-commit run pylint --all-files
- pre-commit run check-ast --all-files
