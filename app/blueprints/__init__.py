"""
Blueprint registration for Kvizarena.

This file imports and registers all Blueprints
for the main Flask application.
"""

from __future__ import annotations
import os

from flask import Blueprint, Flask, jsonify, redirect, url_for, render_template, send_from_directory

# Import new blueprints here
from .admin import admin_bp
from .game_api import game_api_bp
from .auth import auth_bp


def register_blueprints(app: Flask) -> None:
    """Register all application blueprints."""
    
    # Basic health-check
    app.register_blueprint(create_health_blueprint())
    
    # Main blueprint for root URL redirect
    app.register_blueprint(create_main_blueprint())
    
    # New admin blueprint
    app.register_blueprint(admin_bp)
    
    # New Game API blueprint
    app.register_blueprint(game_api_bp)
    
    # New Auth blueprint
    app.register_blueprint(auth_bp)

    # --- PWA FILE ROUTES ---
    # Get the absolute path to the frontend directory
    # __file__ is app/blueprints/__init__.py
    # We need to go up to the project root (3 levels) then into frontend
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'frontend')

    @app.route('/sw.js')
    def serve_sw():
        """Serves the service worker file from the frontend directory."""
        return send_from_directory(frontend_dir, 'sw.js')

    @app.route('/manifest.json')
    def serve_manifest():
        """Serves the manifest file from the frontend directory."""
        return send_from_directory(frontend_dir, 'manifest.json')


def create_health_blueprint() -> Blueprint:
    """Creates a basic health-check blueprint."""
    blueprint = Blueprint("health", __name__)

    @blueprint.get("/health")
    def health() -> tuple[dict[str, str], int]:
        return jsonify(status="ok"), 200

    return blueprint

def create_main_blueprint() -> Blueprint:
    """Creates the main blueprint for homepage redirect."""
    blueprint = Blueprint("main", __name__)
    
    # Get the absolute path to the frontend directory
    # __file__ is app/blueprints/__init__.py
    # We need to go up to the project root (3 levels) then into frontend
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'frontend')

    @blueprint.get("/")
    def index():
        # Serve the main frontend application
        return render_template('index.html')
    
    @blueprint.get("/manifest.json")
    def manifest():
        # Serve the PWA manifest
        return send_from_directory(frontend_dir, 'manifest.json')
    
    @blueprint.get("/sw.js")
    def service_worker():
        # Serve the service worker
        return send_from_directory(frontend_dir, 'sw.js')

    return blueprint
