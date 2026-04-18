"""Tests unitarios para endpoints de autenticación."""

from unittest.mock import patch

from fastapi import HTTPException


class TestLoginEndpoint:
    def test_login_exitoso(self, client, mock_auth_service, usuario_mock):
        credenciales = {
            "email": "test@example.com",
            "password": "password123",
        }
        token = "token.jwt.valido"
        mock_auth_service.iniciar_sesion.return_value = (token, usuario_mock)

        with patch("backend.main.auth_service", mock_auth_service):
            response = client.post("/login", json=credenciales)

        assert response.status_code == 200
        assert response.json()["access_token"] == token
        assert response.json()["token_type"] == "bearer"
        assert response.json()["user"]["id_usuario"] == usuario_mock["id_usuario"]

    def test_login_email_invalido(self, client):
        response = client.post(
            "/login",
            json={"email": "no-es-email", "password": "password123"},
        )
        assert response.status_code == 422

    def test_login_sin_password(self, client):
        response = client.post("/login", json={"email": "test@example.com"})
        assert response.status_code == 422


class TestRegisterEndpoint:
    def test_register_exitoso(self, client, mock_auth_service, usuario_mock):
        payload = {
            "email": "nuevo@example.com",
            "password": "password123",
            "nombre": "Juan",
            "apellidos": "Perez",
            "foto_perfil": None,
        }
        token = "token.jwt.nuevo"
        usuario = {**usuario_mock, "email": payload["email"]}
        mock_auth_service.registrar_usuario.return_value = (token, usuario)

        with patch("backend.main.auth_service", mock_auth_service):
            response = client.post("/register", json=payload)

        assert response.status_code == 200
        assert response.json()["access_token"] == token
        assert response.json()["user"]["email"] == payload["email"]

    def test_register_permite_nombre_opcional(self, client, mock_auth_service, usuario_mock):
        payload = {
            "email": "sin-nombre@example.com",
            "password": "password123",
        }
        token = "token.jwt"
        usuario = {**usuario_mock, "email": payload["email"], "nombre": None}
        mock_auth_service.registrar_usuario.return_value = (token, usuario)

        with patch("backend.main.auth_service", mock_auth_service):
            response = client.post("/register", json=payload)

        assert response.status_code == 200
        assert response.json()["user"]["nombre"] is None

    def test_register_error_controlado_si_servicio_falla(self, client, mock_auth_service):
        payload = {
            "email": "existente@example.com",
            "password": "password123",
            "nombre": "Juan",
            "apellidos": "Perez",
        }
        mock_auth_service.registrar_usuario.side_effect = HTTPException(
            status_code=400,
            detail="Email ya registrado",
        )

        with patch("backend.main.auth_service", mock_auth_service):
            response = client.post("/register", json=payload)

        assert response.status_code == 400

    def test_register_usuario_none_devuelve_500(self, client, mock_auth_service):
        payload = {
            "email": "nuevo@example.com",
            "password": "password123",
            "nombre": "Juan",
            "apellidos": "Perez",
        }
        mock_auth_service.registrar_usuario.return_value = (None, None)

        with patch("backend.main.auth_service", mock_auth_service):
            response = client.post("/register", json=payload)

        assert response.status_code == 500
        assert "Error al crear el usuario" in response.json()["detail"]


class TestCambiarContrasenaEndpoint:
    def test_cambiar_contrasena_exitoso(
        self,
        client,
        valid_jwt_token,
        user_id_mock,
    ):
        payload = {
            "password_actual": "vieja123",
            "password_nueva": "nueva123",
        }
        resultado = {"mensaje": "Contraseña actualizada correctamente"}

        with patch("backend.main.auth_service.validar_token", return_value=user_id_mock), patch(
            "backend.main.auth_service.cambiar_contrasena",
            return_value=resultado,
        ) as mock_cambiar:
            response = client.post(
                "/auth/change-password",
                json=payload,
                headers={"Authorization": f"Bearer {valid_jwt_token}"},
            )

        assert response.status_code == 200
        assert response.json() == resultado
        mock_cambiar.assert_called_once_with(
            id_usuario=user_id_mock,
            password_actual=payload["password_actual"],
            password_nueva=payload["password_nueva"],
        )

    def test_cambiar_contrasena_sin_autenticacion(self, client):
        response = client.post(
            "/auth/change-password",
            json={"password_actual": "vieja123", "password_nueva": "nueva123"},
        )
        assert response.status_code == 401
