"""Tests for SocketIO integration in the Kvizarena application."""

from app import create_app
from app.sockets import socketio


def test_socketio_initialized() -> None:
    """Test that SocketIO is properly initialized."""
    app = create_app({"TESTING": True})
    
    # Verify socketio is initialized
    assert socketio is not None
    
    # Check that socketio has been initialized with the app
    assert socketio.server is not None


def test_socketio_cors_configured() -> None:
    """Test that SocketIO CORS is properly configured."""
    from flask_socketio import SocketIO
    
    # The socketio instance should have CORS enabled for all origins
    assert isinstance(socketio, SocketIO)
    
    # Check that the socketio instance exists
    assert socketio is not None


def test_socketio_middleware_wraps_app() -> None:
    """Test that SocketIO middleware properly wraps the Flask app."""
    app = create_app({"TESTING": True})
    
    # After SocketIO integration, wsgi_app should be wrapped
    # by SocketIO's middleware
    assert hasattr(app.wsgi_app, 'wsgi_app')
    assert app.wsgi_app.__class__.__name__ == '_SocketIOMiddleware'


def test_socketio_test_client_works() -> None:
    """Test that SocketIO test client can be created."""
    app = create_app({"TESTING": True})
    
    # Create a SocketIO test client
    client = socketio.test_client(app)
    
    # Verify the client is connected
    assert client.is_connected()
    
    # Disconnect the client
    client.disconnect()
    
    # Verify disconnection
    assert not client.is_connected()


def test_app_still_responds_to_http() -> None:
    """Test that regular HTTP requests still work after SocketIO integration."""
    app = create_app({"TESTING": True})
    client = app.test_client()
    
    # Test that health endpoint still works
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}
