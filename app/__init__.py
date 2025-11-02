"""Application package for the Kvizarena service."""

from .app import create_app
from .sockets import socketio

__all__ = ["create_app", "socketio"]
