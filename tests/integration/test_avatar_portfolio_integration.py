from unittest.mock import patch


def test_upload_avatar_flow(client, auth_header, user_id, usuario_response):
    files = {"file": ("avatar.png", b"fake-image-content", "image/png")}

    with patch("backend.main.auth_service.validar_token", return_value=user_id), patch(
        "backend.main.user_service.agregar_avatar", return_value=usuario_response
    ) as mock_add_avatar:
        response = client.post("/usuarios/me/avatar", headers=auth_header, files=files)

    assert response.status_code == 200
    assert response.json()["id_usuario"] == user_id
    mock_add_avatar.assert_called_once()


def test_create_and_get_portfolio_flow(client, auth_header, user_id, portfolio_response):
    create_payload = {
        "nombre_portfolio": "Mi Portfolio",
        "descripcion": "Portfolio de integración",
        "riesgo": 0.5,
    }

    with patch("backend.main.auth_service.validar_token", return_value=user_id), patch(
        "backend.main.portfolio_service.crear_portfolio_usuario", return_value=portfolio_response
    ), patch("backend.main.portfolio_service.obtener_portfolio_usuario", return_value=portfolio_response):
        create_response = client.post("/portfolios", headers=auth_header, json=create_payload)
        assert create_response.status_code == 200
        assert create_response.json()["id_portfolio"] == 1

        get_response = client.get("/portfolios/1", headers=auth_header)
        assert get_response.status_code == 200
        assert get_response.json()["nombre_portfolio"] == "Mi Portfolio"
