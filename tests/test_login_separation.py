"""Tests for the separated login page functionality."""

from app import create_app


def test_index_route_serves_login_when_not_logged_in() -> None:
    """Test that the index route serves login.html when user is not logged in."""
    app = create_app({"TESTING": True})
    client = app.test_client()
    
    # Access root without session
    response = client.get("/")
    assert response.status_code == 200
    assert response.content_type.startswith("text/html")
    
    # Check for login page content
    content = response.data.decode('utf-8')
    assert "Přihlaste se prosím pro pokračování" in content
    assert "Přihlásit se přes Google" in content
    assert "Local Dev Login" in content


def test_index_route_serves_app_when_logged_in() -> None:
    """Test that the index route serves index.html when user is logged in."""
    app = create_app({"TESTING": True})
    client = app.test_client()
    
    # Create a session with user_id
    with client.session_transaction() as session:
        session['user_id'] = 1
        session['user_name'] = 'Test User'
    
    # Access root with session
    response = client.get("/")
    assert response.status_code == 200
    assert response.content_type.startswith("text/html")
    
    # Check for main app content (not login page)
    content = response.data.decode('utf-8')
    assert "KvízAréna" in content
    # Should have navigation
    assert "Domů" in content or "nav" in content.lower()
    # Should NOT have login prompt
    assert "Přihlaste se prosím pro pokračování" not in content


def test_login_page_has_required_elements() -> None:
    """Test that the login page contains all required elements."""
    app = create_app({"TESTING": True})
    client = app.test_client()
    
    response = client.get("/")
    content = response.data.decode('utf-8')
    
    # Check for Google login button
    assert 'href="/api/auth/login/google"' in content
    
    # Check for local login form elements
    assert 'id="local-user"' in content
    assert 'id="local-pass"' in content
    assert 'id="local-login-btn"' in content
    
    # Check for footer with legal links
    assert 'href="/privacy"' in content
    assert 'href="/terms"' in content
    assert "Zásady ochrany osobních údajů" in content
    assert "Podmínky použití" in content


def test_main_app_does_not_have_login_elements() -> None:
    """Test that the main app (index.html) does not contain login elements."""
    app = create_app({"TESTING": True})
    client = app.test_client()
    
    # Set session to simulate logged in user
    with client.session_transaction() as session:
        session['user_id'] = 1
        session['user_name'] = 'Test User'
    
    response = client.get("/")
    content = response.data.decode('utf-8')
    
    # Should NOT have login button in the main nav area
    # (login.html has the Google login button, index.html should not)
    # Check that there's no standalone Google login link
    assert "Přihlásit se přes Google" not in content and '<a href="/api/auth/login/google" id="login-link"' not in content
    
    # Should NOT have the local dev login form
    assert 'id="local-login-btn"' not in content
    
    # Should NOT have footer in main app (moved to login page)
    assert "Ikony od" not in content and "Font Awesome" not in content


def test_session_import_exists() -> None:
    """Test that session is properly imported in blueprints.__init__."""
    from app.blueprints import session
    assert session is not None
