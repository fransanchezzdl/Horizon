"""
Arquitectura del modelo Horizon Predictor.

Modelo BiGRU bidireccional para predicción de retornos logarítmicos
a 5 días de trading.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class HorizonBiGRU(nn.Module):
    """
    Modelo Bi-GRU bidireccional para predicción de retornos a 5 días.

    Input: [batch, window_size, num_features]
    Output: [batch, 1] → retorno logarítmico predicho a 5 días
    """

    def __init__(
        self,
        input_dim: int = 9,
        hidden_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.1,
    ):
        super(HorizonBiGRU, self).__init__()

        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers

        self.gru = nn.GRU(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
            bidirectional=True,
        )

        self.fc = nn.Linear(hidden_dim * 2, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.gru(x)
        last_output = out[:, -1, :]
        return self.fc(last_output)


class TemporalAttention(nn.Module):
    """
    Mecanismo de atención temporal sobre la secuencia de salida del GRU.

    Aprende a ponderar cada timestep según su relevancia para la predicción.
    Timesteps con patrones más informativos reciben mayor peso.

    Implementa scaled dot-product attention con una query aprendida:
        score_t = (q · h_t) / sqrt(d)
        alpha_t = softmax(score_t)
        context = sum(alpha_t * h_t)
    """

    def __init__(self, hidden_dim: int):
        super().__init__()
        # Query aprendida: vector que representa "qué buscar" en la secuencia
        self.query = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.scale = hidden_dim ** 0.5

    def forward(self, gru_output: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            gru_output: [batch, seq_len, hidden_dim]

        Returns:
            context: [batch, hidden_dim] — representación ponderada
            weights: [batch, seq_len]    — pesos de atención (para interpretabilidad)
        """
        # Proyectar cada timestep
        keys = self.query(gru_output)  # [batch, seq_len, hidden_dim]

        # Score: producto punto entre cada key y el último hidden state (como query)
        query_vec = gru_output[:, -1:, :]  # [batch, 1, hidden_dim]
        scores = torch.bmm(query_vec, keys.transpose(1, 2))  # [batch, 1, seq_len]
        scores = scores / self.scale
        weights = F.softmax(scores, dim=-1)  # [batch, 1, seq_len]

        # Contexto: suma ponderada de todos los timesteps
        context = torch.bmm(weights, gru_output).squeeze(1)  # [batch, hidden_dim]
        return context, weights.squeeze(1)


class HorizonBiGRUAttention(nn.Module):
    """
    BiGRU con mecanismo de atención temporal y cabeza de clasificación.

    Predice directamente 3 clases: BAJISTA (0), LATERAL (1), ALCISTA (2).
    Esto elimina el problema de regresión + umbral post-hoc que causaba
    que el modelo predijera siempre la clase mayoritaria.

    Arquitectura:
        Input → BiGRU → Attention → [context || last_hidden] → FC → 3 logits

    Args:
        input_dim:   Número de features de entrada.
        hidden_dim:  Dimensión del estado oculto GRU (default: 64).
        num_layers:  Capas GRU apiladas (default: 2).
        dropout:     Dropout entre capas GRU y antes de FC (default: 0.2).
        num_classes: Número de clases de salida (default: 3).
    """

    def __init__(
        self,
        input_dim: int = 9,
        hidden_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
        num_classes: int = 3,
    ):
        super().__init__()

        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.num_classes = num_classes

        self.gru = nn.GRU(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
            bidirectional=True,
        )

        self.attention = TemporalAttention(hidden_dim * 2)
        self.dropout = nn.Dropout(dropout)

        # Cabeza de regresión: context + last_hidden → 1 retorno predicho
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim * 4, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [batch_size, window_size, input_dim]

        Returns:
            [batch_size, 1] — retorno logarítmico predicho a 5 días
        """
        gru_out, _ = self.gru(x)
        context, _ = self.attention(gru_out)
        last_hidden = gru_out[:, -1, :]
        combined = torch.cat([context, last_hidden], dim=-1)
        combined = self.dropout(combined)
        return self.fc(combined)
