"""Blueprint registration for Kvizarena."""

from __future__ import annotations

from flask import Blueprint, Flask, jsonify

# Importujte nové blueprinty zde
from .admin import admin_bp


def register_blueprints(app: Flask) -> None:
    """Register application blueprints."""

    # Základní health-check
    app.register_blueprint(create_health_blueprint())

    # Nový admin blueprint
    app.register_blueprint(admin_bp)

    # Zde budou v budoucnu další (např. game_api_bp)


def create_health_blueprint() -> Blueprint:
    """Vytvoří základní health-check blueprint."""
    blueprint = Blueprint("health", __name__)

    @blueprint.get("/health")
    def health() -> tuple[dict[str, str], int]:
        return jsonify(status="ok"), 200

    return blueprint
