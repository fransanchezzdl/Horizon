"""
Arquitectura del modelo Horizon Predictor.

Modelo BiGRU bidireccional para predicción de retornos logarítmicos
a 5 días de trading.
"""

import torch
import torch.nn as nn


class HorizonBiGRU(nn.Module):
    """
    Modelo Bi-GRU bidireccional para predicción de retornos a 5 días.

    Input: [batch, window_size, num_features(9)]
    Output: [batch, 1] → retorno logarítmico predicho a 5 días

    El modelo realiza regresión pura. La clasificación de tendencia
    (ALCISTA / BAJISTA / LATERAL) se realiza externamente comparando
    el retorno predicho con los umbrales definidos en la configuración.

    Args:
        input_dim: Número de features de entrada (default: 9).
        hidden_dim: Dimensión del estado oculto de la GRU (default: 64).
        num_layers: Número de capas GRU apiladas (default: 2).
        dropout: Tasa de dropout entre capas (default: 0.1).
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

        # Bi-GRU: procesa la secuencia en ambas direcciones
        self.gru = nn.GRU(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
            bidirectional=True,
        )

        # Capa fully connected: hidden_dim * 2 (bidireccional) → 1 retorno
        self.fc = nn.Linear(hidden_dim * 2, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass del modelo.

        Args:
            x: Tensor de entrada [batch_size, window_size, input_dim].

        Returns:
            Tensor con retornos predichos [batch_size, 1].
        """
        # GRU retorna (output, hidden_state)
        # output: [batch_size, window_size, hidden_dim * 2]
        out, _ = self.gru(x)

        # Tomar el último timestep
        last_output = out[:, -1, :]  # [batch_size, hidden_dim * 2]

        # Capa de predicción
        prediction = self.fc(last_output)  # [batch_size, 1]

        return prediction
