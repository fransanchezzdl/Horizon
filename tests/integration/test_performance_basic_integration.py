from time import perf_counter
from unittest.mock import patch


def test_endpoint_activos_basic_performance(client):
    payload = [{"ticker": "AAPL", "nombre_completo": "Apple"}]

    with patch("backend.main.activo_service.listar_activos", return_value=payload):
        start = perf_counter()
        response = client.get("/activos")
        elapsed = perf_counter() - start

    assert response.status_code == 200
    assert elapsed < 1.5


def test_endpoint_auth_me_basic_performance(client, auth_header, user_id, usuario_response):
    with patch("backend.main.auth_service.validar_token", return_value=user_id), patch(
        "backend.main.usuario_dao.obtener_por_id", return_value=usuario_response
    ), patch("backend.main.storage_service.hydrate_user_avatar_safe"):
        start = perf_counter()
        response = client.get("/auth/me", headers=auth_header)
        elapsed = perf_counter() - start

    assert response.status_code == 200
    assert elapsed < 1.5
