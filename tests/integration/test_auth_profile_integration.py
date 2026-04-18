from unittest.mock import patch


def test_login_then_auth_me_flow(client, user_id, usuario_response):
    token = "integration-token"
    credentials = {"email": "integration@test.com", "password": "123456"}

    with patch("backend.main.auth_service.iniciar_sesion", return_value=(token, usuario_response)), patch(
        "backend.main.auth_service.validar_token", return_value=user_id
    ), patch("backend.main.usuario_dao.obtener_por_id", return_value=usuario_response), patch(
        "backend.main.storage_service.hydrate_user_avatar_safe"
    ):
        login_response = client.post("/login", json=credentials)
        assert login_response.status_code == 200
        assert login_response.json()["access_token"] == token

        me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_response.status_code == 200
        assert me_response.json()["id_usuario"] == user_id


def test_auth_me_requires_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401
