"""Smoke tests for the Kvizarena Flask application."""

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
    assert "admin" in blueprint_names, "Admin blueprint should be registered"


def test_health_endpoint() -> None:
    """Test that the health endpoint works correctly."""
    app = create_app({"TESTING": True})
    client = app.test_client()
    
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}
