from .usuario_dto import UsuarioResponse
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

__all__ = [
    "UsuarioResponse",
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
]
