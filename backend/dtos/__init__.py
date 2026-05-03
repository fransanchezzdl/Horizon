from .usuario_dto import (
    UsuarioResponse, 
    PerfilUpdateDTO,
    ChangePasswordRequest,
)
from .activo_dto import (
    ActivoCreateRequest,
    ActivoUpdateRequest,
    ActivoResponse,
    ActivoListResponse,
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
from .curso_dto import (
    CursoListResponse,
    CursoDetailResponse,
    DiapositivaResponse,
    ProgresoResponse,
    ProgresoDiapositivaRequest,
)

__all__ = [
    "UsuarioResponse",
    "PerfilUpdateDTO",
    "ChangePasswordRequest",
    # Activo DTOs
    "ActivoCreateRequest",
    "ActivoUpdateRequest",
    "ActivoResponse",
    "ActivoListResponse",
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
    # Curso DTOs
    "CursoListResponse",
    "CursoDetailResponse",
    "DiapositivaResponse",
    "ProgresoResponse",
    "ProgresoDiapositivaRequest",
]
