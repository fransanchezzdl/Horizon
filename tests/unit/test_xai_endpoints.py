"""Tests unitarios para endpoints XAI."""

from unittest.mock import patch, MagicMock


_SHAP_DAO = "backend.daos.xai_shap_dao.XaiShapDAO"

_LATEST_SHAP = {
    "ticker": "AAPL",
    "fecha": "2026-04-19",
    "senal": "BAJISTA",
    "confianza": 0.3491,
    "correcta": None,
    "shap_values": [
        {"feature": "EMA_sw30_trend",       "shap": 0.103,  "value": -0.12, "abs": 0.103},
        {"feature": "SMA50_Slope_sw15_std", "shap": -0.025, "value": 0.04,  "abs": 0.025},
        {"feature": "Realized_Vol_sw5_mean","shap": 0.022,  "value": 0.31,  "abs": 0.022},
    ],
}

_SHAP_TEMPORAL = {
    "ticker": "AAPL",
    "top_features": ["EMA_sw30_trend", "RSI_sw5_last", "Volume_sw15_mean"],
    "series": [
        {"fecha": "2026-04-10", "EMA_sw30_trend": 0.09, "RSI_sw5_last": -0.03, "Volume_sw15_mean": 0.01},
        {"fecha": "2026-04-15", "EMA_sw30_trend": 0.11, "RSI_sw5_last": -0.04, "Volume_sw15_mean": 0.02},
        {"fecha": "2026-04-19", "EMA_sw30_trend": 0.10, "RSI_sw5_last": -0.05, "Volume_sw15_mean": 0.01},
    ],
}


class TestLatestShapEndpoint:

    def test_devuelve_datos_shap(self, client):
        with patch(f"{_SHAP_DAO}.obtener_latest_shap", return_value=_LATEST_SHAP):
            response = client.get("/activos/AAPL/xai/latest-shap")

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert data["senal"] == "BAJISTA"
        assert isinstance(data["shap_values"], list)
        assert len(data["shap_values"]) == 3

    def test_ticker_se_normaliza_a_mayusculas(self, client):
        mock_dao = MagicMock(return_value=_LATEST_SHAP)
        with patch(f"{_SHAP_DAO}.obtener_latest_shap", mock_dao):
            client.get("/activos/aapl/xai/latest-shap")

        mock_dao.assert_called_once_with("AAPL")

    def test_404_si_no_hay_datos(self, client):
        with patch(f"{_SHAP_DAO}.obtener_latest_shap", return_value=None):
            response = client.get("/activos/AAPL/xai/latest-shap")

        assert response.status_code == 404

    def test_estructura_shap_values(self, client):
        with patch(f"{_SHAP_DAO}.obtener_latest_shap", return_value=_LATEST_SHAP):
            response = client.get("/activos/AAPL/xai/latest-shap")

        item = response.json()["shap_values"][0]
        assert "feature" in item
        assert "shap" in item
        assert "abs" in item


class TestShapTemporalEndpoint:

    def test_devuelve_series_temporales(self, client):
        with patch(f"{_SHAP_DAO}.obtener_shap_temporal", return_value=_SHAP_TEMPORAL):
            response = client.get("/activos/AAPL/xai/shap-temporal")

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert len(data["top_features"]) == 3
        assert len(data["series"]) == 3

    def test_ticker_se_normaliza_a_mayusculas(self, client):
        mock_dao = MagicMock(return_value=_SHAP_TEMPORAL)
        with patch(f"{_SHAP_DAO}.obtener_shap_temporal", mock_dao):
            client.get("/activos/aapl/xai/shap-temporal")

        args, kwargs = mock_dao.call_args
        assert args[0] == "AAPL"

    def test_limit_por_defecto_es_30(self, client):
        mock_dao = MagicMock(return_value=_SHAP_TEMPORAL)
        with patch(f"{_SHAP_DAO}.obtener_shap_temporal", mock_dao):
            client.get("/activos/AAPL/xai/shap-temporal")

        _, kwargs = mock_dao.call_args
        assert kwargs.get("limit", 30) == 30

    def test_limit_personalizado(self, client):
        mock_dao = MagicMock(return_value=_SHAP_TEMPORAL)
        with patch(f"{_SHAP_DAO}.obtener_shap_temporal", mock_dao):
            client.get("/activos/AAPL/xai/shap-temporal?limit=10")

        _, kwargs = mock_dao.call_args
        assert kwargs.get("limit") == 10

    def test_404_si_no_hay_datos(self, client):
        with patch(f"{_SHAP_DAO}.obtener_shap_temporal", return_value=None):
            response = client.get("/activos/AAPL/xai/shap-temporal")

        assert response.status_code == 404

    def test_cada_punto_tiene_fecha_y_features(self, client):
        with patch(f"{_SHAP_DAO}.obtener_shap_temporal", return_value=_SHAP_TEMPORAL):
            response = client.get("/activos/AAPL/xai/shap-temporal")

        series = response.json()["series"]
        top = response.json()["top_features"]
        for punto in series:
            assert "fecha" in punto
            for feat in top:
                assert feat in punto

    def test_error_dao_devuelve_500(self, client):
        with patch(f"{_SHAP_DAO}.obtener_shap_temporal", side_effect=Exception("DB error")):
            response = client.get("/activos/AAPL/xai/shap-temporal")

        assert response.status_code == 500
