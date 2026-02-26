"""Paquete de DAOs para el backend.

Exporta los DAOs principales para facilitar imports desde otros módulos.
"""

from .usuario_dao import UsuarioDAO, usuario_dao

__all__ = ["UsuarioDAO", "usuario_dao"]
