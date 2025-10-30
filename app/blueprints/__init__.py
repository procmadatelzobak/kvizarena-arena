"""
Blueprint registration for Kvizarena.

This file imports and registers all Blueprints
for the main Flask application.
"""

from __future__ import annotations
from flask import Blueprint, Flask, jsonify

# Import new blueprints here
from .admin import admin_bp


def register_blueprints(app: Flask) -> None:
    """Register all application blueprints."""
    
    # Basic health-check
    app.register_blueprint(create_health_blueprint())
    
    # New admin blueprint
    app.register_blueprint(admin_bp)
    
    # Future blueprints (e.g., game_api_bp) will go here


def create_health_blueprint() -> Blueprint:
    """Creates a basic health-check blueprint."""
    blueprint = Blueprint("health", __name__)

    @blueprint.get("/health")
    def health() -> tuple[dict[str, str], int]:
        return jsonify(status="ok"), 200

    return blueprint
