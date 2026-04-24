"""
Arquitectura del modelo Horizon Predictor.

Modelos BiGRU bidireccionales especializados para clasificación de tendencias
a 5 días de trading: BAJISTA (0), LATERAL (1), ALCISTA (2).

Arquitecturas:
- HorizonBiGRU: BiGRU simple → FC(num_classes) - baseline
- HorizonBiGRUAttention: BiGRU + Attention temporal → FC(num_classes) - mejorado
- StableHorizonModel: Para activos de baja volatilidad (window_size=60, hidden=128, dropout=0.1)
- VolatileHorizonModel: Para activos de alta volatilidad (window_size=20, num_layers=3, dropout=0.3, FocalLoss)

Todos usan clasificación pura con CrossEntropyLoss.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple


class TemporalAttention(nn.Module):
    """
    Mecanismo de atención temporal con query aprendible (no circular).

    Implementa scaled dot-product attention:
        score_t = (q · h_t) / sqrt(d)
        alpha_t = softmax(score_t)
        context = sum(alpha_t * h_t)

    La query es un parámetro aprendible independiente, NO el último timestep.
    """

    def __init__(self, hidden_dim: int):
        super().__init__()
        # BUG FIX #2: Query aprendible (antes era el último timestep → query circular)
        self.query_param = nn.Parameter(torch.randn(hidden_dim) / (hidden_dim ** 0.5))
        self.scale = hidden_dim ** 0.5

    def forward(self, gru_output: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            gru_output: [batch, seq_len, hidden_dim]

        Returns:
            context: [batch, hidden_dim] — representación ponderada
            weights: [batch, seq_len]    — pesos de atención
        """
        batch_size = gru_output.size(0)

        # Expandir query para batch
        query = self.query_param.unsqueeze(0).unsqueeze(0)  # [1, 1, hidden_dim]
        query = query.expand(batch_size, 1, -1)  # [batch, 1, hidden_dim]

        # Scores: query · keys
        scores = torch.bmm(query, gru_output.transpose(1, 2))  # [batch, 1, seq_len]
        scores = scores / self.scale
        weights = F.softmax(scores, dim=-1)  # [batch, 1, seq_len]

        # Contexto ponderado
        context = torch.bmm(weights, gru_output).squeeze(1)  # [batch, hidden_dim]
        return context, weights.squeeze(1)


class HorizonBiGRU(nn.Module):
    """
    Modelo Bi-GRU bidireccional baseline para clasificación de 3 clases.

    Arquitectura simple: Input → BiGRU → take_last → FC(num_classes) → logits

    Input:  [batch, window_size, input_dim]
    Output: [batch, num_classes]   logits para CrossEntropyLoss
    """

    def __init__(
        self,
        input_dim: int = 9,
        hidden_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.1,
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

        # BUG FIX #3: Dropout explícito después del GRU
        self.dropout_layer = nn.Dropout(dropout)

        # Cabeza de clasificación: [hidden_dim * 2] → num_classes logits
        self.fc = nn.Linear(hidden_dim * 2, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [batch_size, window_size, input_dim]

        Returns:
            [batch_size, num_classes] logits
        """
        out, _ = self.gru(x)
        last_output = out[:, -1, :]  # [batch, hidden_dim*2]
        last_output = self.dropout_layer(last_output)
        return self.fc(last_output)


class HorizonBiGRUAttention(nn.Module):
    """
    BiGRU con mecanismo de atención temporal para clasificación de 3 clases.

    Arquitectura: Input → BiGRU → Attention → [context || last_hidden] → FC(num_classes)

    La atención aprende pesos dinámicos para cada timestep, capturando patrones
    temporales más complejos que solo usar el último step.

    Args:
        input_dim:   Dimensión de entrada.
        hidden_dim:  Dimensión del GRU (default: 64).
        num_layers:  Capas GRU apiladas (default: 2).
        dropout:     Dropout en GRU y FC (default: 0.2).
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

        # BUG FIX #3: Dropout explícito
        self.dropout_layer = nn.Dropout(dropout)

        # Cabeza de clasificación: [context || last_hidden] = [hidden_dim*4] → num_classes
        # BUG FIX #1: Ahora retorna num_classes, no 1 (antes era regresión)
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim * 4, hidden_dim * 2),
            nn.BatchNorm1d(hidden_dim * 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [batch_size, window_size, input_dim]

        Returns:
            [batch_size, num_classes] logits para CrossEntropyLoss
        """
        gru_out, _ = self.gru(x)
        context, _ = self.attention(gru_out)
        last_hidden = gru_out[:, -1, :]
        combined = torch.cat([context, last_hidden], dim=-1)  # [batch, hidden_dim*4]
        combined = self.dropout_layer(combined)
        return self.fc(combined)


class StableHorizonModel(nn.Module):
    """
    Modelo especializado para activos de BAJA VOLATILIDAD (blue chips, ETFs, índices).

    Configuración:
    - window_size: 60 días (contexto largo, menos noise)
    - hidden_dim: 128 (más expresividad)
    - num_layers: 2 (capas moderadas)
    - dropout: 0.1 (conservador, regularización suave)
    - Atención temporal para capturar cambios lentos
    - CrossEntropyLoss + class_weights

    Arquitectura: Input → BiGRU(128) → Attention → Dense layers → logits(3)
    """

    def __init__(
        self,
        input_dim: int = 9,
        hidden_dim: int = 128,
        num_layers: int = 2,
        dropout: float = 0.1,
        num_classes: int = 3,
    ):
        super().__init__()
        self.model_type = "stable"
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.num_classes = num_classes

        # BiGRU bidireccional
        self.gru = nn.GRU(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
            bidirectional=True,
        )

        # Atención temporal
        self.attention = TemporalAttention(hidden_dim * 2)

        # Regularización
        self.dropout_layer = nn.Dropout(dropout)
        self.batch_norm = nn.BatchNorm1d(hidden_dim * 4)

        # Cabeza de clasificación con arquitectura más profunda
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim * 4, hidden_dim * 2),
            nn.BatchNorm1d(hidden_dim * 2),
            nn.Tanh(),  # Mejor que ReLU para representaciones suaves
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [batch_size, window_size, input_dim]

        Returns:
            [batch_size, num_classes] logits
        """
        gru_out, _ = self.gru(x)
        context, _ = self.attention(gru_out)
        last_hidden = gru_out[:, -1, :]
        combined = torch.cat([context, last_hidden], dim=-1)
        combined = self.batch_norm(combined)
        combined = self.dropout_layer(combined)
        return self.fc(combined)


class VolatileHorizonModel(nn.Module):
    """
    Modelo especializado para activos de ALTA VOLATILIDAD (small caps, crypto, earnings plays).

    Configuración:
    - window_size: 20 días (ventana corta, responde rápido)
    - hidden_dim: 96 (mantener eficiencia)
    - num_layers: 3 (más capas para capturar volatilidad)
    - dropout: 0.3 (agresivo, fuerte regularización)
    - Atención temporal para detectar cambios bruscos
    - FocalLoss para manejar desbalanceo de clases

    Arquitectura: Input → BiGRU(96)x3 → Attention → Dense → logits(3)

    La FocalLoss penaliza menos los ejemplos fáciles de clasificar,
    enfocándose en los difíciles (clases minoritarias).
    """

    def __init__(
        self,
        input_dim: int = 9,
        hidden_dim: int = 96,
        num_layers: int = 3,
        dropout: float = 0.3,
        num_classes: int = 3,
    ):
        super().__init__()
        self.model_type = "volatile"
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.num_classes = num_classes

        # BiGRU con más capas para capturar volatilidad
        self.gru = nn.GRU(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
            bidirectional=True,
        )

        # Atención temporal (crucial para detectar cambios rápidos)
        self.attention = TemporalAttention(hidden_dim * 2)

        # Regularización agresiva
        self.dropout_layer = nn.Dropout(dropout)

        # Cabeza de clasificación con residual connection
        self.fc_initial = nn.Linear(hidden_dim * 4, hidden_dim * 2)
        self.batch_norm1 = nn.BatchNorm1d(hidden_dim * 2)

        self.fc_hidden = nn.Linear(hidden_dim * 2, hidden_dim)
        self.batch_norm2 = nn.BatchNorm1d(hidden_dim)

        self.fc_out = nn.Linear(hidden_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [batch_size, window_size, input_dim]

        Returns:
            [batch_size, num_classes] logits
        """
        gru_out, _ = self.gru(x)
        context, _ = self.attention(gru_out)
        last_hidden = gru_out[:, -1, :]
        combined = torch.cat([context, last_hidden], dim=-1)

        # Primer layer
        h = self.fc_initial(combined)
        h = self.batch_norm1(h)
        h = torch.tanh(h)
        h = self.dropout_layer(h)

        # Segundo layer
        h = self.fc_hidden(h)
        h = self.batch_norm2(h)
        h = torch.relu(h)
        h = self.dropout_layer(h)

        # Salida
        logits = self.fc_out(h)
        return logits


class FocalLoss(nn.Module):
    """
    Focal Loss para manejo de desbalanceo de clases.

    Propuesto en "Focal Loss for Dense Object Detection" (Lin et al., 2017).

    FL(p_t) = -alpha * (1 - p_t)^gamma * log(p_t)

    Parámetros:
    - alpha: balance de clases (None = sin balance)
    - gamma: focusing parameter (0 = CE loss, >0 = down-weighs easy examples)

    Uso en VolatileHorizonModel para activos con clases muy desbalanceadas.
    """

    def __init__(
        self,
        alpha: torch.Tensor | None = None,
        gamma: float = 2.0,
        reduction: str = "mean",
    ):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction

    def forward(
        self,
        predictions: torch.Tensor,  # [batch, num_classes] logits
        targets: torch.Tensor,      # [batch] class indices
    ) -> torch.Tensor:
        """
        Args:
            predictions: [batch, num_classes] logits de red
            targets: [batch] índices de clase verdadera [0, 1, 2]

        Returns:
            Scalar loss
        """
        p = F.softmax(predictions, dim=1)
        ce_loss = F.cross_entropy(predictions, targets, reduction="none")
        p_t = p.gather(1, targets.unsqueeze(1)).squeeze(1)
        focal_weight = (1 - p_t) ** self.gamma
        focal_loss = focal_weight * ce_loss

        if self.alpha is not None:
            alpha_t = self.alpha.gather(0, targets)
            focal_loss = alpha_t * focal_loss

        if self.reduction == "mean":
            return focal_loss.mean()
        elif self.reduction == "sum":
            return focal_loss.sum()
        else:
            return focal_loss
