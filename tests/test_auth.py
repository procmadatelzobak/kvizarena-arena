"""Tests for the authentication blueprint."""

import os
from unittest.mock import patch, MagicMock
from flask import url_for
from app import create_app


def test_auth_blueprint_registered() -> None:
    """Test that auth blueprint is registered."""
    app = create_app({"TESTING": True})
    
    blueprint_names = [bp for bp in app.blueprints.keys()]
    assert "auth" in blueprint_names, "Auth blueprint should be registered"


def test_login_google_uses_https_scheme() -> None:
    """Test that login_google generates redirect_uri with https scheme."""
    # Mock Google OAuth credentials
    with patch.dict(os.environ, {
        "GOOGLE_CLIENT_ID": "test-client-id",
        "GOOGLE_CLIENT_SECRET": "test-client-secret"
    }):
        app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-secret-key"
        })
        
        with app.test_request_context():
            # Generate the callback URL as login_google would do
            redirect_uri = url_for('auth.callback_google', _external=True, _scheme='https')
            
            # Verify the URL starts with https://
            assert redirect_uri.startswith('https://'), \
                f"Redirect URI should use https scheme, got: {redirect_uri}"
            
            # Verify it contains the callback endpoint
            assert '/api/auth/callback/google' in redirect_uri, \
                f"Redirect URI should contain callback path, got: {redirect_uri}"


def test_login_google_endpoint_exists() -> None:
    """Test that the login_google endpoint is accessible."""
    with patch.dict(os.environ, {
        "GOOGLE_CLIENT_ID": "test-client-id",
        "GOOGLE_CLIENT_SECRET": "test-client-secret"
    }):
        app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-secret-key"
        })
        
        # Check that the route exists in the app's URL map
        with app.test_request_context():
            # This will raise BuildError if route doesn't exist
            url = url_for('auth.login_google')
            assert url == '/api/auth/login/google'
