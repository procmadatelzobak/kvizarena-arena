"""Database helpers for Kvizarena."""

from __future__ import annotations

from flask import Flask
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def init_app(app: Flask) -> None:
    """Initialise the SQLAlchemy extension with the given Flask app."""
    db.init_app(app)
