## TESTING DE LINTING - QUICK START

Punto de referencia rápida para verificación de código. Para documentación detallada, ver [tests/LINTING.md](LINTING.md).

## Alcance de verificación

El linting verifica solo los directorios críticos del backend:
- `daos/` – Capas de acceso a datos
- `dtos/` – Objetos de transferencia de datos
- `services/` – Lógica de negocio
- `exceptions/` – Excepciones personalizadas
- `main.py` – Archivo principal

No se verifican: `routes/`, `models/`, `scripts/`

## Instalación inicial (una sola vez)

```bash
pip install -r requirements.txt
pre-commit install
```

Los hooks de pre-commit se ejecutarán automáticamente en cada commit sobre los directorios especificados.

## Ejecutar verificaciones de linting

| Método | Comando | Descripción |
|--------|---------|-------------|
| Script manual | `python tests/linting/run_pylint.py --verbose` | Ejecución interactiva con detalles |
| Pytest | `pytest tests/linting/test_linting.py -v` | Tests estructurados para CI/CD |
| Reporte JSON | `python tests/linting/run_pylint.py --reports` | Genera reporte documentado |
| Pre-commit | `git commit` | Verificación automática |

## Archivos de configuración

```
.pylintrc                              Reglas de linting (máx 120 chars, máx 6 args función)
.pre-commit-config.yaml                Configuración de git hooks automáticos
tests/linting/
  ├── run_pylint.py                    Script para análisis de código
  ├── test_linting.py                  Tests con pytest
  └── setup_linting.py                 Utilidad de configuración inicial
```

## Verificaciones implementadas

- Errores de sintaxis Python
- Importaciones inválidas
- Variables indefinidas
- Límites de complejidad (máx 6 argumentos por función, máx 10 atributos por clase)
- Conformidad con PEP 8 (seleccionada)

## Uso común

**Ver problemas de código:**
```bash
python tests/linting/run_pylint.py --verbose
```

**Generar reporte formal:**
```bash
python tests/linting/run_pylint.py --reports
cat tests/linting/pylint_report.json
```

**Omitir verificación (solo cuando sea necesario):**
```bash
git commit --no-verify
```

**Personalizar reglas:**
```bash
# Editar: .pylintrc
# Secciones: [FORMAT], [DESIGN], [BASIC]
```

## Resolución de problemas

| Problema | Solución |
|----------|----------|
| pylint no encontrado | `pip install --upgrade pylint` |
| Pre-commit no activo | `pre-commit install && pre-commit run --all-files` |
| Necesito saltarme control | `git commit --no-verify` |

---

Para más detalles: Abre [tests/LINTING.md](LINTING.md)
