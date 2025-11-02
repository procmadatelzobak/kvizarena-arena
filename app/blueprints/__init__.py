"""
Blueprint registration for Kvizarena.

This file imports and registers all Blueprints
for the main Flask application.
"""

from __future__ import annotations
import os
from pathlib import Path

from flask import Blueprint, Flask, jsonify, redirect, url_for, render_template, send_from_directory

# Import new blueprints here
from .admin import admin_bp
from .game_api import game_api_bp
from .auth import auth_bp

# Calculate the frontend directory path once
FRONTEND_DIR = Path(__file__).parent.parent.parent / 'frontend'


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

    @app.route('/sw.js')
    def serve_sw():
        """Serves the service worker file from the frontend directory."""
        return send_from_directory(str(FRONTEND_DIR), 'sw.js')

    @app.route('/manifest.json')
    def serve_manifest():
        """Serves the manifest file from the frontend directory."""
        return send_from_directory(str(FRONTEND_DIR), 'manifest.json')


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

    @blueprint.get("/")
    def index():
        # Serve the main frontend application
        return render_template('index.html')
    
    @blueprint.get("/privacy")
    def privacy_page():
        """Serves the Privacy Policy page."""
        return render_template('privacy.html')

    @blueprint.get("/terms")
    def terms_page():
        """Serves the Terms of Service page."""
        return render_template('terms.html')
    
    @blueprint.get("/manifest.json")
    def manifest():
        # Serve the PWA manifest
        return send_from_directory(str(FRONTEND_DIR), 'manifest.json')
    
    @blueprint.get("/sw.js")
    def service_worker():
        # Serve the service worker
        return send_from_directory(str(FRONTEND_DIR), 'sw.js')

    return blueprint
