"""Paquete de DAOs para el backend.

Exporta los DAOs principales para facilitar imports desde otros módulos.
"""

from .usuario_dao import UsuarioDAO, usuario_dao
from .portfolio_dao import PortfolioDAO, portfolio_dao
from .prediction_dao import PredictionDAO, prediction_dao

__all__ = [
    "UsuarioDAO", 
    "usuario_dao",
    "PortfolioDAO",
    "portfolio_dao",
    "PredictionDAO",
    "prediction_dao",
]
