"""Smoke tests for the Kvizarena Flask application."""

from app import create_app


def test_create_app() -> None:
    app = create_app({"TESTING": True})

    assert app.testing is True
    assert app.url_map is not None
