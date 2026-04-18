"""Configuración compartida para tests unitarios de endpoints."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    """Cliente HTTP de pruebas.

    raise_server_exceptions=False permite validar respuestas 4xx/5xx
    sin que el TestClient interrumpa el test con excepción local.
    """
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_usuario_dao():
    """Mock del DAO de usuarios."""
    mock = MagicMock()
    return mock


@pytest.fixture
def mock_auth_service():
    """Mock del servicio de autenticación."""
    mock = MagicMock()
    return mock


@pytest.fixture
def mock_activo_service():
    """Mock del servicio de activos."""
    mock = MagicMock()
    return mock


@pytest.fixture
def mock_chat_service():
    """Mock del servicio de chat."""
    mock = MagicMock()
    return mock


@pytest.fixture
def mock_reflexion_service():
    """Mock del servicio de reflexiones."""
    mock = MagicMock()
    return mock


@pytest.fixture
def mock_ticker_news_service():
    """Mock del servicio de noticias de ticker."""
    return MagicMock()


@pytest.fixture
def mock_portfolio_service():
    """Mock del servicio de portfolios."""
    mock = MagicMock()
    return mock


@pytest.fixture
def mock_user_service():
    """Mock del servicio de usuarios."""
    mock = MagicMock()
    return mock


@pytest.fixture
def user_id_mock():
    """ID de usuario para tests con autenticación."""
    return "user-123-uuid"


@pytest.fixture
def valid_jwt_token():
    """Token JWT válido para tests."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEyMy11dWlkIn0.token"


@pytest.fixture
def usuario_mock():
    """Usuario mock para responses."""
    return {
        "id_usuario": "user-123-uuid",
        "email": "test@example.com",
        "nombre": "Test",
        "apellidos": "User",
        "membresia": "FREE",
        "foto_perfil": None,
        "created_at": datetime(2026, 1, 1, 0, 0, 0).isoformat(),
    }


@pytest.fixture
def activo_mock():
    """Activo mock para responses."""
    return {
        "ticker": "AAPL",
        "nombre_completo": "Apple Inc.",
        "precio": 150.25,
        "confianza_bygru": 0.71,
        "senal_ia": "ALCISTA",
        "estabilidad": True,
        "senal_actualizada_en": None,
        "precio_predicho": None,
        "retorno_predicho_pct": None,
        "live_accuracy_30d": None,
        "sector": "Tecnologia",
        "volatilidad_30d": None,
    }
