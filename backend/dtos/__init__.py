from .usuario_dto import UsuarioResponse
from .activo_dto import (
    ActivoCreateRequest,
    ActivoUpdateRequest,
    ActivoResponse,
    ActivoListResponse,
)
from .historico_dto import (
    HistoricoActivoCreateRequest,
    HistoricoActivoUpdateRequest,
    HistoricoActivoResponse,
    HistoricoActivoListResponse,
)
from .login_dto import LoginRequest, LoginResponse
from .register_dto import RegisterRequest, RegisterResponse
from .portfolio_dto import (
    StockInPortfolioRequest,
    StockInPortfolioResponse,
    PortfolioCreateRequest,
    PortfolioUpdateRequest,
    PortfolioResponse,
    PortfolioListResponse,
    PortfolioRecommendationRequest,
    AllocationRecommendation,
    PortfolioRecommendationResponse,
    PortfolioAnalysisResponse,
)
from .prediction_dto import (
    PredictionRequest,
    PredictionDetailDay,
    PredictionResponse,
    BlendedReturnRequest,
    BlendedReturnResponse,
    HistoricalPredictionResponse,
    PredictionStatsResponse,
)
from .chat_dto import (
    ChatMessageRequest,
    ChatMessageResponse,
)
from .reflexion_dto import (
    ReflexionCardResponse,
    ReflexionArticuloResponse,
)

__all__ = [
    "UsuarioResponse",
    # Activo DTOs
    "ActivoCreateRequest",
    "ActivoUpdateRequest",
    "ActivoResponse",
    "ActivoListResponse",
    # Histórico DTOs
    "HistoricoActivoCreateRequest",
    "HistoricoActivoUpdateRequest",
    "HistoricoActivoResponse",
    "HistoricoActivoListResponse",
    "LoginRequest",
    "LoginResponse",
    "RegisterRequest",
    "RegisterResponse",
    # Portfolio DTOs
    "StockInPortfolioRequest",
    "StockInPortfolioResponse",
    "PortfolioCreateRequest",
    "PortfolioUpdateRequest",
    "PortfolioResponse",
    "PortfolioListResponse",
    "PortfolioRecommendationRequest",
    "AllocationRecommendation",
    "PortfolioRecommendationResponse",
    "PortfolioAnalysisResponse",
    # Prediction DTOs
    "PredictionRequest",
    "PredictionDetailDay",
    "PredictionResponse",
    "BlendedReturnRequest",
    "BlendedReturnResponse",
    "HistoricalPredictionResponse",
    "PredictionStatsResponse",
    # Chat DTOs
    "ChatMessageRequest",
    "ChatMessageResponse",
    # Reflexión DTOs
    "ReflexionCardResponse",
    "ReflexionArticuloResponse",
]
