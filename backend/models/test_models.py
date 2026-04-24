"""
Tests unitarios para el módulo completo de modelos Horizon.

Cubre:
- Shapes de input/output de modelos
- Forward pass con diferentes configuraciones
- Router automático
- Feature pipeline
- Loss functions
- Evaluador

Uso:
    pytest backend/models/test_models.py -v
    pytest backend/models/test_models.py::test_stable_model -v
"""

import pytest
import numpy as np
import torch
import torch.nn as nn
from typing import Tuple

from .model import (
    HorizonBiGRU,
    HorizonBiGRUAttention,
    StableHorizonModel,
    VolatileHorizonModel,
    TemporalAttention,
    FocalLoss,
)
from .model_router import HorizonModelRouter
from .feature_pipeline import HorizonFeaturePipeline


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                    FIXTURES Y UTILIDADES                                  ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


@pytest.fixture
def device():
    """Usar CPU para tests (más portable)."""
    return torch.device("cpu")


@pytest.fixture
def random_batch_stable() -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Batch aleatorio para modelo STABLE.
    
    Returns:
        (X, y) donde:
        - X: [batch_size=8, window_size=60, input_dim=9]
        - y: [batch_size=8] clases [0, 1, 2]
    """
    batch_size = 8
    window_size = 60
    input_dim = 9
    
    X = torch.randn(batch_size, window_size, input_dim)
    y = torch.randint(0, 3, (batch_size,))  # Clases
    
    return X, y


@pytest.fixture
def random_batch_volatile() -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Batch aleatorio para modelo VOLATILE.
    
    Returns:
        (X, y) donde:
        - X: [batch_size=16, window_size=20, input_dim=11]  
        - y: [batch_size=16] clases [0, 1, 2]
    """
    batch_size = 16
    window_size = 20
    input_dim = 11
    
    X = torch.randn(batch_size, window_size, input_dim)
    y = torch.randint(0, 3, (batch_size,))
    
    return X, y


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                    TESTS DE ARQUITECTURA                                  ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


class TestTemporalAttention:
    """Tests para el mecanismo de atención temporal."""

    def test_temporal_attention_forward_shape(self, device):
        """Verificar que la atención devuelve shapes correctos."""
        attention = TemporalAttention(hidden_dim=128).to(device)
        
        # Input: [batch=4, seq_len=30, hidden_dim=128]
        gru_output = torch.randn(4, 30, 128, device=device)
        
        context, weights = attention(gru_output)
        
        # Context: [batch, hidden_dim]
        assert context.shape == (4, 128), f"Context shape incorrecto: {context.shape}"
        
        # Weights: [batch, seq_len]
        assert weights.shape == (4, 30), f"Weights shape incorrecto: {weights.shape}"
        
        # Verificar que weights suman a 1 (softmax)
        weight_sums = weights.sum(dim=1)
        assert torch.allclose(weight_sums, torch.ones_like(weight_sums), atol=1e-6)

    def test_temporal_attention_query_parameter(self):
        """Verificar que la query es un parámetro aprendible (BUG FIX #2)."""
        attention = TemporalAttention(hidden_dim=64)
        
        # La query debe ser un parámetro nn.Parameter
        assert isinstance(attention.query_param, nn.Parameter), \
            "query_param debe ser nn.Parameter (no query dependiente del input)"


class TestHorizonBiGRU:
    """Tests baseline para BiGRU simple."""

    def test_bigru_forward_shape(self, device, random_batch_stable):
        """Verificar output shape del BiGRU."""
        X, y = random_batch_stable
        X = X.to(device)
        
        model = HorizonBiGRU(
            input_dim=9,
            hidden_dim=64,
            num_layers=2,
            dropout=0.1,
            num_classes=3,
        ).to(device)
        
        logits = model(X)
        
        # Output: [batch, num_classes]
        assert logits.shape == (8, 3), f"Output shape incorrecto: {logits.shape}"
        assert logits.dtype == torch.float32

    def test_bigru_classification_output(self, device):
        """Verificar que BiGRU devuelve logits válidos para clasificación."""
        batch_size = 4
        input_dim = 9
        
        X = torch.randn(batch_size, 30, input_dim, device=device)
        
        model = HorizonBiGRU(
            input_dim=input_dim,
            num_classes=3,
        ).to(device)
        
        logits = model(X)
        
        # Debe poder convertir a probabilidades con softmax
        probs = torch.softmax(logits, dim=1)
        assert torch.allclose(probs.sum(dim=1), torch.ones(batch_size, device=device))


class TestStableHorizonModel:
    """Tests para modelo especializado STABLE."""

    def test_stable_model_instantiation(self):
        """Verificar que StableHorizonModel se instancia correctamente."""
        model = StableHorizonModel(
            input_dim=9,
            hidden_dim=128,
            num_layers=2,
            dropout=0.1,
            num_classes=3,
        )
        
        # Verificar configuración
        assert model.model_type == "stable"
        assert model.hidden_dim == 128
        assert model.num_classes == 3

    def test_stable_model_forward(self, device, random_batch_stable):
        """Forward pass del modelo STABLE."""
        X, y = random_batch_stable
        X = X.to(device)
        
        model = StableHorizonModel(
            input_dim=9,
            hidden_dim=128,
            dropout=0.1,
        ).to(device)
        
        logits = model(X)
        
        assert logits.shape == (8, 3)
        assert torch.isfinite(logits).all(), "Output contiene NaN o Inf"


class TestVolatileHorizonModel:
    """Tests para modelo especializado VOLATILE."""

    def test_volatile_model_instantiation(self):
        """Verificar que VolatileHorizonModel se instancia correctamente."""
        model = VolatileHorizonModel(
            input_dim=11,
            hidden_dim=96,
            num_layers=3,
            dropout=0.3,
            num_classes=3,
        )
        
        assert model.model_type == "volatile"
        assert model.hidden_dim == 96
        assert model.num_layers == 3

    def test_volatile_model_forward(self, device, random_batch_volatile):
        """Forward pass del modelo VOLATILE."""
        X, y = random_batch_volatile
        X = X.to(device)
        
        model = VolatileHorizonModel(
            input_dim=11,
            hidden_dim=96,
            num_layers=3,
            dropout=0.3,
        ).to(device)
        
        logits = model(X)
        
        assert logits.shape == (16, 3)
        assert torch.isfinite(logits).all()


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                    TESTS DE LOSS FUNCTIONS                                ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


class TestFocalLoss:
    """Tests para FocalLoss."""

    def test_focal_loss_basic(self, device):
        """Verificar que FocalLoss funciona básicamente."""
        predictions = torch.randn(4, 3, device=device)  # batch=4, classes=3
        targets = torch.tensor([0, 1, 2, 1], device=device)
        
        loss_fn = FocalLoss(gamma=2.0)
        loss = loss_fn(predictions, targets)
        
        assert loss.item() > 0
        assert torch.isfinite(loss)

    def test_focal_loss_with_class_weights(self, device):
        """Verificar FocalLoss con class weights."""
        predictions = torch.randn(8, 3, device=device)
        targets = torch.tensor([0, 0, 1, 1, 2, 2, 0, 1], device=device)
        
        # Desbalancear pesos: clase 2 es más importante
        class_weights = torch.tensor([1.0, 1.0, 3.0], device=device)
        
        loss_fn = FocalLoss(alpha=class_weights, gamma=2.0)
        loss = loss_fn(predictions, targets)
        
        assert torch.isfinite(loss)

    def test_focal_loss_reduction_modes(self, device):
        """Verificar diferentes modos de reduction."""
        predictions = torch.randn(4, 3, device=device)
        targets = torch.tensor([0, 1, 2, 1], device=device)
        
        # Mean
        loss_mean = FocalLoss(reduction="mean")(predictions, targets)
        assert loss_mean.shape == ()
        
        # Sum
        loss_sum = FocalLoss(reduction="sum")(predictions, targets)
        assert loss_sum.shape == ()
        
        # None (per-sample)
        loss_none = FocalLoss(reduction="none")(predictions, targets)
        assert loss_none.shape == (4,)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                    TESTS DEL ROUTER                                       ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


class TestHorizonModelRouter:
    """Tests para HorizonModelRouter."""

    def test_router_get_model_config_stable(self):
        """Verificar configuración para activos STABLE."""
        config = HorizonModelRouter.get_model_config("KO", asset_type="stable")
        
        assert config["asset_type"] == "stable"
        assert config["window_size"] == 60
        assert config["hidden_dim"] == 128
        assert config["dropout"] == 0.1
        assert config["model_class"] == "StableHorizonModel"

    def test_router_get_model_config_volatile(self):
        """Verificar configuración para activos VOLATILE."""
        config = HorizonModelRouter.get_model_config("TSLA", asset_type="volatile")
        
        assert config["asset_type"] == "volatile"
        assert config["window_size"] == 20
        assert config["hidden_dim"] == 96
        assert config["num_layers"] == 3
        assert config["dropout"] == 0.3
        assert config["loss_function"] == "FocalLoss"

    def test_router_instantiate_stable_model(self, device):
        """Verificar que el router instancia correctamente StableHorizonModel."""
        model = HorizonModelRouter.get_model(
            "KO",
            input_dim=9,
            device=device,
            asset_type="stable"
        )
        
        assert isinstance(model, StableHorizonModel)
        assert model.hidden_dim == 128

    def test_router_instantiate_volatile_model(self, device):
        """Verificar que el router instancia correctamente VolatileHorizonModel."""
        model = HorizonModelRouter.get_model(
            "TSLA",
            input_dim=11,
            device=device,
            asset_type="volatile"
        )
        
        assert isinstance(model, VolatileHorizonModel)
        assert model.num_layers == 3

    def test_router_cache_mechanism(self):
        """Verificar que el caché del router funciona."""
        HorizonModelRouter.clear_cache()
        
        # Primera llamada sin caché
        asset_type_1 = HorizonModelRouter.classify_asset("KO", use_cache=True)
        cache_stats_1 = HorizonModelRouter.get_cache_stats()
        assert len(cache_stats_1["cached_tickers"]) == 1
        
        # Segunda llamada debe usar caché
        asset_type_2 = HorizonModelRouter.classify_asset("KO", use_cache=True)
        cache_stats_2 = HorizonModelRouter.get_cache_stats()
        assert len(cache_stats_2["cached_tickers"]) == 1
        assert asset_type_1 == asset_type_2


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                    TESTS DE FEATURE PIPELINE                              ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


class TestFeaturePipeline:
    """Tests para HorizonFeaturePipeline."""

    def test_get_feature_columns_stable(self):
        """Verificar que get_feature_columns devuelve correctas para stable."""
        cols = HorizonFeaturePipeline.get_feature_columns(
            "stable",
            include_sentiment=False,
            include_advanced=False,
        )
        
        # 9 base + 3 régimen = 12
        assert len(cols) == 12
        assert "Close" in cols
        assert "SMA200_Dist" in cols
        assert "VIX_Close" not in cols  # No es volatile

    def test_get_feature_columns_volatile(self):
        """Verificar que get_feature_columns devuelve correctas para volatile."""
        cols = HorizonFeaturePipeline.get_feature_columns(
            "volatile",
            include_sentiment=False,
            include_advanced=False,
        )
        
        # 9 base + 3 régimen + 2 volátiles = 14
        assert len(cols) == 14
        assert "VIX_Close" in cols
        assert "NASDAQ_Return" in cols

    def test_get_feature_columns_with_sentiment(self):
        """Verificar que sentimiento se añade correctamente."""
        cols = HorizonFeaturePipeline.get_feature_columns(
            "stable",
            include_sentiment=True,
            include_advanced=False,
        )
        
        # 9 base + 3 régimen + 3 sentimiento = 15
        assert len(cols) == 15
        assert "sentiment_score" in cols
        assert "sentiment_magnitude" in cols
        assert "news_volume" in cols

    def test_feature_documentation(self):
        """Verificar que la documentación de features existe."""
        doc = HorizonFeaturePipeline.get_feature_documentation()
        
        assert len(doc) > 0
        assert "Close" in doc
        assert "RSI" in doc
        assert isinstance(doc["Close"], str)

    def test_validate_feature_matrix_clean(self):
        """Verificar validación con matrix limpia."""
        X = np.random.randn(100, 12)  # 100 samples, 12 features
        cols = [f"feat_{i}" for i in range(12)]
        
        is_valid, issues = HorizonFeaturePipeline.validate_feature_matrix(X, cols)
        
        assert is_valid
        assert len(issues) == 0

    def test_validate_feature_matrix_with_nans(self):
        """Verificar detección de NaNs."""
        X = np.random.randn(100, 12)
        X[0:10, 0] = np.nan  # 10% NaNs en feature 0
        cols = [f"feat_{i}" for i in range(12)]
        
        is_valid, issues = HorizonFeaturePipeline.validate_feature_matrix(
            X, cols, max_nan_pct=5.0
        )
        
        assert not is_valid
        assert len(issues) > 0
        assert "feat_0" in str(issues)

    def test_validate_feature_matrix_with_infinites(self):
        """Verificar detección de infinitos."""
        X = np.random.randn(100, 12)
        X[0, 1] = np.inf  # Infinito en feature 1
        cols = [f"feat_{i}" for i in range(12)]
        
        is_valid, issues = HorizonFeaturePipeline.validate_feature_matrix(X, cols)
        
        assert not is_valid
        assert any("infinitos" in str(issue) for issue in issues)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                    TESTS DE INTEGRACIÓN                                   ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


class TestModelIntegration:
    """Tests de integración entre componentes."""

    def test_stable_model_with_crossentropyloss(self, device):
        """Verificar que StableModel funciona con CrossEntropyLoss."""
        batch_size = 8
        X = torch.randn(batch_size, 60, 9, device=device)
        y = torch.randint(0, 3, (batch_size,), device=device)
        
        model = StableHorizonModel(input_dim=9, hidden_dim=128).to(device)
        criterion = nn.CrossEntropyLoss()
        
        logits = model(X)
        loss = criterion(logits, y)
        
        assert torch.isfinite(loss)
        assert loss.item() > 0

    def test_volatile_model_with_focal_loss(self, device):
        """Verificar que VolatileModel funciona con FocalLoss."""
        batch_size = 16
        X = torch.randn(batch_size, 20, 11, device=device)
        y = torch.randint(0, 3, (batch_size,), device=device)
        
        model = VolatileHorizonModel(input_dim=11, hidden_dim=96).to(device)
        criterion = FocalLoss(gamma=2.0)
        
        logits = model(X)
        loss = criterion(logits, y)
        
        assert torch.isfinite(loss)
        assert loss.item() > 0

    def test_training_step_stable_model(self, device):
        """Verificar que se puede entrenar un paso el modelo STABLE."""
        batch_size = 8
        X = torch.randn(batch_size, 60, 9, device=device)
        y = torch.randint(0, 3, (batch_size,), device=device)
        
        model = StableHorizonModel().to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        criterion = nn.CrossEntropyLoss()
        
        # Forward
        logits = model(X)
        loss = criterion(logits, y)
        
        # Backward
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        assert torch.isfinite(loss)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                    TESTS DE REGRESSION                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


def test_no_regression_classification_output():
    """Regresión: Verificar que BiGRUAttention retorna 3 clases, no 1 (BUG FIX #1)."""
    model = HorizonBiGRUAttention(
        input_dim=9,
        hidden_dim=64,
        num_classes=3,
    )
    
    X = torch.randn(4, 30, 9)
    logits = model(X)
    
    # Debe retornar [batch, 3], NO [batch, 1]
    assert logits.shape == (4, 3), \
        f"BUG: BiGRUAttention debería retornar [batch, 3], no {logits.shape}"


def test_no_regression_query_circular_attention():
    """Regresión: Verificar que Attention usa query aprendible (BUG FIX #2)."""
    attention = TemporalAttention(hidden_dim=64)
    
    # Query debe ser parámetro, no dependencia del input
    assert hasattr(attention, "query_param"), \
        "BUG: TemporalAttention debe tener query_param nn.Parameter"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
