# Horizon

Plataforma web de análisis financiero con **predicciones de mercado explicables (XAI)**, asesor con IA generativa y una academia de formación en inversión. Proyecto de Trabajo de Fin de Grado (TFG).

> ⚠️ **Aviso:** Horizon es un proyecto académico. Nada de lo que muestra constituye asesoramiento financiero ni una recomendación de inversión.

## Características

- **Predicción de activos:** modelos XGBoost (con calibración de probabilidades y umbrales congelados) para acciones, criptomonedas y materias primas.
- **IA explicable:** explicaciones SHAP (waterfall y evolución temporal) con narrativa en lenguaje natural.
- **Asesor IA:** chat financiero basado en Google Gemini con contexto del usuario y del activo.
- **Portfolios:** creación y análisis de carteras, con optimización y rebalanceo.
- **Análisis de activos:** precios, variaciones, noticias y sentimiento por ticker.
- **Academia y reflexión del día:** contenido formativo para nuevos inversores.
- **Cuentas de usuario:** autenticación con Supabase Auth, perfil y avatar, tema claro/oscuro.

## Stack

| Capa | Tecnología |
|---|---|
| Frontend | HTML, CSS y JavaScript sin framework |
| Backend | Python, FastAPI, Uvicorn |
| Datos y autenticación | Supabase (PostgreSQL + Auth + Storage) |
| Machine Learning | XGBoost, PyTorch, scikit-learn, SHAP |
| Datos de mercado | yfinance, Finnhub, Alpha Vantage |
| IA generativa | Google Gemini |
| Despliegue | Docker Compose + nginx |
| Calidad | pytest, pylint, pre-commit |

## Estructura

```text
backend/    API FastAPI (daos, dtos, services, routes) y modelos de ML
frontend/   Páginas HTML, estilos y JavaScript
docs/       Arquitectura, autenticación, asesor IA y esquema de base de datos
infra/      Dockerfile, docker-compose y configuración de nginx
tests/      Tests unitarios, de integración, linting y scripts de entrenamiento
```

La arquitectura por capas está descrita en [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Puesta en marcha

### Requisitos

- Python 3.11+
- Un proyecto de [Supabase](https://supabase.com) con el esquema de [`docs/bbdd.sql`](docs/bbdd.sql)
- Claves de API de Gemini, Finnhub y Alpha Vantage (todas tienen plan gratuito)

### 1. Configurar variables de entorno

Copia `backend/.env_example` a `backend/.env` y rellena los valores:

```env
SUPABASE_URL=...
SUPABASE_KEY=...                 # clave anon
SUPABASE_SERVICE_ROLE_KEY=...    # clave secreta, solo en el backend
GEMINI_API_KEY=...
ALPHA_VANTAGE_API_KEY=...
FINNHUB_API_KEY=...
```

> Nunca subas `backend/.env` al repositorio ni expongas la `service_role` key en el frontend.

### 2. Backend

```bash
python -m venv backend/venv
. backend/venv/Scripts/activate      # Linux/macOS: source backend/venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

La API queda en `http://localhost:8000` (documentación interactiva en `/docs`).

### 3. Frontend

```bash
cd frontend
python -m http.server 5000
```

Abre `http://localhost:5000/login.html`.

### Con Docker

```bash
docker compose -f infra/compose/docker-compose.yml up --build
```

Más detalles en [`infra/README.md`](infra/README.md).

## Tests

```bash
pytest tests/unit
```

## Licencia

Distribuido bajo licencia [MIT](LICENSE).
