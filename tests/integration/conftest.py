from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def auth_header() -> dict[str, str]:
    return {"Authorization": "Bearer integration-token"}


@pytest.fixture
def user_id() -> str:
    return "user-integration-123"


@pytest.fixture
def usuario_response(user_id: str) -> dict:
    return {
        "id_usuario": user_id,
        "nombre": "Integration",
        "apellidos": "Tester",
        "email": "integration@test.com",
        "membresia": "FREE",
        "foto_perfil": None,
        "created_at": datetime(2026, 4, 18, 12, 0, 0).isoformat(),
    }


@pytest.fixture
def portfolio_response(user_id: str) -> dict:
    now = datetime(2026, 4, 18, 12, 0, 0).isoformat()
    return {
        "id_portfolio": 1,
        "id_usuario": user_id,
        "nombre_portfolio": "Mi Portfolio",
        "descripcion": "Portfolio de integración",
        "riesgo": 0.5,
        "acciones": [],
        "created_at": now,
        "updated_at": now,
    }
