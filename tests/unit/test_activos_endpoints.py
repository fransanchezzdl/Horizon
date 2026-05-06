"""Tests unitarios para endpoints de activos y fiabilidad de modelo."""

from unittest.mock import patch


class TestActivosEndpoints:
    def test_listar_activos_sin_filtro(self, client, mock_activo_service, activo_mock):
        activos = [activo_mock]
        mock_activo_service.listar_activos.return_value = activos

        with patch("backend.main.activo_service", mock_activo_service):
            response = client.get("/activos")

        assert response.status_code == 200
        assert response.json() == activos
        mock_activo_service.listar_activos.assert_called_once()

    def test_listar_activos_con_filtro(self, client, mock_activo_service, activo_mock):
        filtro = "AAPL"
        activos = [activo_mock]
        mock_activo_service.buscar_activos.return_value = activos

        with patch("backend.main.activo_service", mock_activo_service):
            response = client.get(f"/activos?q={filtro}")

        assert response.status_code == 200
        assert response.json() == activos
        mock_activo_service.buscar_activos.assert_called_once_with(filtro)

    def test_obtener_activo_existente(self, client, mock_activo_service, activo_mock):
        ticker = "AAPL"
        mock_activo_service.obtener_activo.return_value = activo_mock

        with patch("backend.main.activo_service", mock_activo_service):
            response = client.get(f"/activos/{ticker}")

        assert response.status_code == 200
        assert response.json() == activo_mock

    def test_obtener_activo_no_encontrado(self, client, mock_activo_service):
        mock_activo_service.obtener_activo.return_value = None

        with patch("backend.main.activo_service", mock_activo_service):
            response = client.get("/activos/XXXX")

        assert response.status_code == 404
        assert response.json()["detail"] == "Activo no encontrado"

    def test_obtener_noticias_activo_existente(
        self,
        client,
        mock_activo_service,
        mock_ticker_news_service,
    ):
        ticker = "AAPL"
        mock_activo_service.obtener_activo.return_value = {"ticker": ticker}
        noticias = [{"titulo": "Noticia 1", "sentimiento": "positivo"}]
        mock_ticker_news_service.obtener_noticias_ticker.return_value = noticias

        with patch("backend.main.activo_service", mock_activo_service), patch(
            "backend.main.ticker_news_service", mock_ticker_news_service
        ):
            response = client.get(f"/activos/{ticker}/noticias?limit=2")

        assert response.status_code == 200
        assert response.json() == noticias
        mock_ticker_news_service.obtener_noticias_ticker.assert_called_once_with(
            ticker=ticker,
            limit=2,
        )

    def test_obtener_noticias_activo_no_encontrado(self, client, mock_activo_service):
        mock_activo_service.obtener_activo.return_value = None

        with patch("backend.main.activo_service", mock_activo_service):
            response = client.get("/activos/XXXX/noticias")

        assert response.status_code == 404
        assert response.json()["detail"] == "Activo no encontrado"

    def test_noticias_limite_por_defecto(
        self,
        client,
        mock_activo_service,
        mock_ticker_news_service,
    ):
        ticker = "AAPL"
        mock_activo_service.obtener_activo.return_value = {"ticker": ticker}
        mock_ticker_news_service.obtener_noticias_ticker.return_value = []

        with patch("backend.main.activo_service", mock_activo_service), patch(
            "backend.main.ticker_news_service", mock_ticker_news_service
        ):
            response = client.get(f"/activos/{ticker}/noticias")

        assert response.status_code == 200
        call_args = mock_ticker_news_service.obtener_noticias_ticker.call_args
        assert call_args.kwargs["limit"] == 3


class TestFiabilidadYHistoricoEndpoints:
    def test_reliability_404_si_activo_no_existe(self, client, mock_activo_service):
        mock_activo_service.obtener_activo.return_value = None

        with patch("backend.main.activo_service", mock_activo_service):
            response = client.get("/activos/XXXX/reliability")

        assert response.status_code == 404
        assert response.json()["detail"] == "Activo no encontrado"

    def test_reliability_ok(self, client, mock_activo_service):
        mock_activo_service.obtener_activo.return_value = {"ticker": "AAPL"}
        payload = {
            "ticker": "AAPL",
            "walk_forward": {"ba_mean": 40.0, "f1_mean": 39.0, "n_folds": 5},
            "live": {"total": 10, "resueltas": 5, "correctas": 3, "accuracy": 60.0},
            "baseline": 33.33,
            "señal": "MODERADA",
        }

        with patch("backend.main.activo_service", mock_activo_service), patch(
            "backend.services.prediction_log_service.get_reliability_stats",
            return_value=payload,
        ):
            response = client.get("/activos/AAPL/reliability")

        assert response.status_code == 200
        assert response.json() == payload

    def test_price_history_404_si_activo_no_existe(self, client, mock_activo_service):
        mock_activo_service.obtener_activo.return_value = None

        with patch("backend.main.activo_service", mock_activo_service):
            response = client.get("/activos/XXXX/price-history")

        assert response.status_code == 404
        assert response.json()["detail"] == "Activo no encontrado"

    def test_price_history_ok(self, client, mock_activo_service):
        mock_activo_service.obtener_activo.return_value = {"ticker": "AAPL"}
        payload = {
            "ticker": "AAPL",
            "days": 30,
            "series": [{"date": "2026-04-01", "close": 150.0, "signal": "ALCISTA"}],
        }

        with patch("backend.main.activo_service", mock_activo_service), patch(
            "backend.main.PriceHistoryService.get_price_and_signals",
            return_value=payload,
        ):
            response = client.get("/activos/AAPL/price-history?days=30")

        assert response.status_code == 200
        assert response.json() == payload

    def test_quote_404_si_activo_no_existe(self, client, mock_activo_service):
        mock_activo_service.obtener_activo.return_value = None

        with patch("backend.main.activo_service", mock_activo_service):
            response = client.get("/activos/XXXX/quote")

        assert response.status_code == 404
        assert response.json()["detail"] == "Activo no encontrado"

    def test_quote_ok(self, client, mock_activo_service):
        mock_activo_service.obtener_activo.return_value = {"ticker": "AAPL"}
        payload = {"price": 287.69, "previous_close": 284.18, "change_percent": 1.235}

        with patch("backend.main.activo_service", mock_activo_service), patch(
            "backend.main.PriceHistoryService.get_quote",
            return_value=payload,
        ):
            response = client.get("/activos/AAPL/quote")

        assert response.status_code == 200
        assert response.json() == payload
