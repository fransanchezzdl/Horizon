from unittest.mock import MagicMock

from backend.services.auth_service import AuthService


def test_auth_service_login_supabase_light(usuario_response):
    db = MagicMock()
    usuario_dao = MagicMock()
    storage = MagicMock()

    db.auth.sign_in_with_password.return_value = {
        "user": {"id": usuario_response["id_usuario"]},
        "session": {"access_token": "supabase-token"},
    }
    usuario_dao.obtener_por_id.return_value = usuario_response

    service = AuthService(db, usuario_dao, storage)

    token, perfil = service.iniciar_sesion("integration@test.com", "123456")

    assert token == "supabase-token"
    assert perfil["id_usuario"] == usuario_response["id_usuario"]
    db.auth.sign_in_with_password.assert_called_once()
    usuario_dao.obtener_por_id.assert_called_once_with(usuario_response["id_usuario"])
    storage.hydrate_user_avatar_safe.assert_called_once()


def test_auth_service_validar_token_supabase_light():
    db = MagicMock()
    usuario_dao = MagicMock()
    storage = MagicMock()

    db.auth.get_user.return_value = {"user": {"id": "supabase-user-id"}}

    service = AuthService(db, usuario_dao, storage)

    user_id = service.validar_token("token-de-prueba")

    assert user_id == "supabase-user-id"
    db.auth.get_user.assert_called_once_with("token-de-prueba")
