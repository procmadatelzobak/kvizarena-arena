"""Blueprint registration for Kvizarena."""

from __future__ import annotations

from flask import Blueprint, Flask, jsonify


def register_blueprints(app: Flask) -> None:
    """Register application blueprints."""
    app.register_blueprint(create_health_blueprint())


def create_health_blueprint() -> Blueprint:
    """Create a basic health-check blueprint."""
    blueprint = Blueprint("health", __name__)

    @blueprint.get("/health")
    def health() -> tuple[dict[str, str], int]:
        return jsonify(status="ok"), 200

    return blueprint
