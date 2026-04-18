"""Tests unitarios para endpoints de reflexiones."""

from datetime import datetime
from unittest.mock import patch


def build_reflexion_payload(reflexion_id: int):
    return {
        "id_reflexion": reflexion_id,
        "cita": "La disciplina supera al talento",
        "autor": "Autor Test",
        "tema": "Psicologia",
        "titulo_articulo": "Gestion emocional al invertir",
        "contenido": "Contenido de prueba",
        "tiempo_lectura": 4,
        "tags": ["disciplina", "riesgo"],
        "created_at": datetime(2026, 1, 1, 0, 0, 0).isoformat(),
    }


class TestObtenerReflexionAleatoria:
    def test_obtener_reflexion_aleatoria_exitoso(
        self,
        client,
        mock_reflexion_service,
        user_id_mock,
        valid_jwt_token,
    ):
        payload = build_reflexion_payload(1)
        mock_reflexion_service.obtener_aleatoria.return_value = payload

        with patch("backend.main.auth_service.validar_token", return_value=user_id_mock), patch(
            "backend.main.reflexion_service", mock_reflexion_service
        ):
            response = client.get(
                "/reflexion/aleatoria",
                headers={"Authorization": f"Bearer {valid_jwt_token}"},
            )

        assert response.status_code == 200
        assert response.json()["id_reflexion"] == 1

    def test_obtener_reflexion_aleatoria_requiere_auth(self, client):
        response = client.get("/reflexion/aleatoria")
        assert response.status_code == 401


class TestObtenerReflexionPorId:
    def test_obtener_reflexion_por_id_existente(
        self,
        client,
        mock_reflexion_service,
        user_id_mock,
        valid_jwt_token,
    ):
        reflexion_id = 2
        payload = build_reflexion_payload(reflexion_id)
        mock_reflexion_service.obtener_por_id.return_value = payload

        with patch("backend.main.auth_service.validar_token", return_value=user_id_mock), patch(
            "backend.main.reflexion_service", mock_reflexion_service
        ):
            response = client.get(
                f"/reflexion/{reflexion_id}",
                headers={"Authorization": f"Bearer {valid_jwt_token}"},
            )

        assert response.status_code == 200
        assert response.json()["id_reflexion"] == reflexion_id
        mock_reflexion_service.obtener_por_id.assert_called_once_with(reflexion_id)

    def test_obtener_reflexion_id_invalido_con_auth(self, client, user_id_mock, valid_jwt_token):
        with patch("backend.main.auth_service.validar_token", return_value=user_id_mock):
            response = client.get(
                "/reflexion/abc",
                headers={"Authorization": f"Bearer {valid_jwt_token}"},
            )

        assert response.status_code == 422

    def test_obtener_reflexion_requiere_autenticacion(self, client):
        response = client.get("/reflexion/1")
        assert response.status_code == 401
