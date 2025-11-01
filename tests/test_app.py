"""Smoke tests for the Kvizarena Flask application."""

import os
from unittest.mock import patch

from app import create_app


def test_create_app() -> None:
    app = create_app({"TESTING": True})

    assert app.testing is True
    assert app.url_map is not None


def test_blueprints_registered() -> None:
    """Test that all expected blueprints are registered."""
    app = create_app({"TESTING": True})
    
    # Get all registered blueprint names
    blueprint_names = [bp for bp in app.blueprints.keys()]
    
    # Verify expected blueprints are registered
    assert "health" in blueprint_names, "Health blueprint should be registered"
    assert "main" in blueprint_names, "Main blueprint should be registered"
    assert "admin" in blueprint_names, "Admin blueprint should be registered"
    assert "game_api" in blueprint_names, "Game API blueprint should be registered"


def test_health_endpoint() -> None:
    """Test that the health endpoint works correctly."""
    app = create_app({"TESTING": True})
    client = app.test_client()
    
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_secret_key_from_env() -> None:
    """Test that SECRET_KEY is loaded from environment variable."""
    with patch.dict(os.environ, {"SECRET_KEY": "test-secret-key-123"}):
        app = create_app()
        assert app.config["SECRET_KEY"] == "test-secret-key-123"


def test_secret_key_fallback() -> None:
    """Test that SECRET_KEY falls back to 'dev' when not set in environment."""
    with patch.dict(os.environ, {}, clear=True):
        app = create_app()
        assert app.config["SECRET_KEY"] == "dev"


def test_database_uri_from_env() -> None:
    """Test that DATABASE_URL is loaded from environment variable."""
    with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///test.db"}):
        app = create_app()
        assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///test.db"


def test_database_uri_fallback() -> None:
    """Test that DATABASE_URL falls back to sqlite when not set."""
    with patch.dict(os.environ, {}, clear=True):
        app = create_app()
        assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///kvizarena.db"


def test_config_parameter_overrides_env() -> None:
    """Test that config parameter can override environment variables."""
    with patch.dict(os.environ, {"SECRET_KEY": "env-secret"}):
        app = create_app({"SECRET_KEY": "config-secret"})
        # Direct assignment means env is set first, then config overrides
        assert app.config["SECRET_KEY"] == "config-secret"
