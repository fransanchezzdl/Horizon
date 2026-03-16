"""Paquete de DAOs para el backend.

Exporta los DAOs principales para facilitar imports desde otros módulos.
"""


from .usuario_dao import UsuarioDAO, usuario_dao
from .activo_dao import ActivoDAO, activo_dao
from .historico_dao import HistoricoActivoDAO, historico_dao
from .portfolio_dao import PortfolioDAO, portfolio_dao
from .prediction_dao import PredictionDAO, prediction_dao
from .chat_dao import ChatDAO, chat_dao

__all__ = [
    "UsuarioDAO", 
    "usuario_dao",
    "ActivoDAO",
    "activo_dao",
    "HistoricoActivoDAO",
    "historico_dao",
    "PortfolioDAO",
    "portfolio_dao",
    "PredictionDAO",
    "prediction_dao",
    "ChatDAO",
    "chat_dao",
]
