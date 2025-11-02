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
    # Note: If .env file exists, load_dotenv() will load SECRET_KEY from it
    # This test may load "change-me" from .env.example if it exists
    with patch.dict(os.environ, {}, clear=True):
        # Also need to prevent dotenv from loading .env file
        with patch('app.app.load_dotenv'):
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


def test_proxy_fix_middleware_applied() -> None:
    """Test that ProxyFix middleware is applied to the app."""
    from werkzeug.middleware.proxy_fix import ProxyFix
    
    app = create_app({"TESTING": True})
    
    # After SocketIO integration, the wsgi_app is wrapped by SocketIO middleware
    # which in turn wraps the ProxyFix middleware
    # Check that ProxyFix is in the middleware chain
    if hasattr(app.wsgi_app, 'wsgi_app'):
        # SocketIO wraps the app, so ProxyFix is the inner wsgi_app
        proxy_fix = app.wsgi_app.wsgi_app
    else:
        # Fallback for when SocketIO is not used
        proxy_fix = app.wsgi_app
    
    assert isinstance(proxy_fix, ProxyFix)
    
    # Verify ProxyFix parameters are set correctly
    # These ensure that X-Forwarded-For, X-Forwarded-Proto, and X-Forwarded-Host 
    # headers are trusted from the reverse proxy
    assert proxy_fix.x_for == 1
    assert proxy_fix.x_proto == 1
    assert proxy_fix.x_host == 1


def test_pwa_service_worker_route() -> None:
    """Test that /sw.js route is accessible."""
    app = create_app({"TESTING": True})
    client = app.test_client()
    
    response = client.get("/sw.js")
    assert response.status_code == 200
    assert response.content_type.startswith("text/javascript") or response.content_type.startswith("application/javascript")


def test_pwa_manifest_route() -> None:
    """Test that /manifest.json route is accessible."""
    app = create_app({"TESTING": True})
    client = app.test_client()
    
    response = client.get("/manifest.json")
    assert response.status_code == 200
    assert response.content_type == "application/json"


def test_privacy_page_route() -> None:
    """Test that /privacy route is accessible and returns HTML."""
    app = create_app({"TESTING": True})
    client = app.test_client()
    
    response = client.get("/privacy")
    assert response.status_code == 200
    assert response.content_type.startswith("text/html")
    # Decode to check Czech text content
    content = response.data.decode('utf-8')
    assert "Zásady ochrany osobních údajů" in content
    assert "Privacy Policy" in content


def test_terms_page_route() -> None:
    """Test that /terms route is accessible and returns HTML."""
    app = create_app({"TESTING": True})
    client = app.test_client()
    
    response = client.get("/terms")
    assert response.status_code == 200
    assert response.content_type.startswith("text/html")
    # Decode to check Czech text content
    content = response.data.decode('utf-8')
    assert "Podmínky použití" in content
    assert "Terms of Service" in content


def test_no_cache_headers_present() -> None:
    """Test that no-cache headers are present in all responses to prevent session hijacking."""
    app = create_app({"TESTING": True})
    client = app.test_client()
    
    # Test on health endpoint
    response = client.get("/health")
    assert response.status_code == 200
    
    # Verify all no-cache headers are present
    assert 'Cache-Control' in response.headers
    assert 'no-store' in response.headers['Cache-Control']
    assert 'no-cache' in response.headers['Cache-Control']
    assert 'must-revalidate' in response.headers['Cache-Control']
    assert 'max-age=0' in response.headers['Cache-Control']
    
    assert 'Pragma' in response.headers
    assert response.headers['Pragma'] == 'no-cache'
    
    assert 'Expires' in response.headers
    assert response.headers['Expires'] == '-1'


def test_no_cache_headers_on_different_routes() -> None:
    """Test that no-cache headers are applied to various routes."""
    app = create_app({"TESTING": True})
    client = app.test_client()
    
    # Test multiple routes to ensure headers are applied universally
    routes = ["/health", "/privacy", "/terms", "/manifest.json", "/sw.js"]
    
    for route in routes:
        response = client.get(route)
        # Only check successful responses
        if response.status_code == 200:
            assert 'Cache-Control' in response.headers, f"Cache-Control missing on {route}"
            assert 'no-cache' in response.headers['Cache-Control'], f"no-cache missing on {route}"
            assert 'Pragma' in response.headers, f"Pragma missing on {route}"
            assert 'Expires' in response.headers, f"Expires missing on {route}"
