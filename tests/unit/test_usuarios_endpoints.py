"""Tests unitarios para endpoints de usuarios."""

from unittest.mock import patch


class TestObtenerUsuarios:
    def test_obtener_todos_usuarios(self, client, mock_usuario_dao, usuario_mock):
        usuarios = [usuario_mock]
        mock_usuario_dao.obtener_todos.return_value = usuarios

        with patch("backend.main.usuario_dao", mock_usuario_dao):
            response = client.get("/usuarios")

        assert response.status_code == 200
        assert response.json() == usuarios
        mock_usuario_dao.obtener_todos.assert_called_once()

    def test_obtener_usuarios_lista_vacia(self, client, mock_usuario_dao):
        mock_usuario_dao.obtener_todos.return_value = []

        with patch("backend.main.usuario_dao", mock_usuario_dao):
            response = client.get("/usuarios")

        assert response.status_code == 200
        assert response.json() == []

    def test_obtener_usuarios_error_base_datos(self, client, mock_usuario_dao):
        mock_usuario_dao.obtener_todos.side_effect = Exception("DB Error")

        with patch("backend.main.usuario_dao", mock_usuario_dao):
            response = client.get("/usuarios")

        assert response.status_code >= 500


class TestObtenerInfoUsuarioAutenticado:
    def test_get_current_user_info_ok(
        self,
        client,
        mock_usuario_dao,
        usuario_mock,
        user_id_mock,
        valid_jwt_token,
    ):
        mock_usuario_dao.obtener_por_id.return_value = usuario_mock

        with patch("backend.main.auth_service.validar_token", return_value=user_id_mock), patch(
            "backend.main.usuario_dao", mock_usuario_dao
        ), patch("backend.main.storage_service.hydrate_user_avatar_safe"):
            response = client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {valid_jwt_token}"},
            )

        assert response.status_code == 200
        assert response.json()["id_usuario"] == user_id_mock

    def test_get_current_user_info_usuario_no_encontrado(
        self,
        client,
        mock_usuario_dao,
        user_id_mock,
        valid_jwt_token,
    ):
        mock_usuario_dao.obtener_por_id.return_value = None

        with patch("backend.main.auth_service.validar_token", return_value=user_id_mock), patch(
            "backend.main.usuario_dao", mock_usuario_dao
        ):
            response = client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {valid_jwt_token}"},
            )

        assert response.status_code == 401
        assert response.json()["detail"] == "Usuario no encontrado"

    def test_get_current_user_info_sin_token(self, client):
        response = client.get("/auth/me")
        assert response.status_code == 401
