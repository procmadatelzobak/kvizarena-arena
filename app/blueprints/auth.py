"""
Authentication Blueprint for KvízAréna.

Handles Google OAuth2 authentication flow.
"""
import os
import secrets
import logging
from flask import Blueprint, url_for, redirect, session, request, jsonify
from authlib.integrations.flask_client import OAuth
from authlib.common.errors import AuthlibBaseError
from sqlalchemy.exc import IntegrityError
from app.database import db, User

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# This 'oauth' object will be configured from app.py
oauth = OAuth()

@auth_bp.route('/login/google')
def login_google():
    """Redirects to Google's login page."""
    # The redirect_uri must match *exactly* what's in Google Console
    redirect_uri = url_for('auth.callback_google', _external=True)
    
    # Generate a secure nonce and store it in the session
    nonce = secrets.token_urlsafe(32)
    session['google_auth_nonce'] = nonce
    
    # Pass the nonce to Google
    return oauth.google.authorize_redirect(redirect_uri, nonce=nonce)

@auth_bp.route('/callback/google')
def callback_google():
    """Handles the callback from Google."""
    try:
        token = oauth.google.authorize_access_token()
        
        # Retrieve the nonce we stored in the session
        nonce = session.get('google_auth_nonce')
        if not nonce:
            raise Exception("Nonce not found in session.")
        
        # Pass the token AND the nonce for validation
        user_info = oauth.google.parse_id_token(token, nonce=nonce)
        
        # Clear the used nonce from the session
        session.pop('google_auth_nonce', None)
        
    except AuthlibBaseError as e:
        # Log OAuth-specific errors with more context for debugging
        logger.error(f"OAuth error during callback: {type(e).__name__} - {str(e)[:100]}")
        return redirect('/?error=auth_failed')
    except Exception as e:
        # Print the actual error to the log
        print(f"Unexpected error during OAuth callback: {type(e).__name__} - {e}")
        return redirect('/?error=auth_failed') # Redirect to frontend with error

    # Find or create user in database
    google_id = user_info.get('sub')
    user = User.query.filter_by(google_id=google_id).first()

    if not user:
        user = User(
            google_id=google_id,
            email=user_info.get('email'),
            name=user_info.get('name'),
            profile_pic_url=user_info.get('picture')
        )
        db.session.add(user)
        db.session.commit()

    # IMPORTANT: Store user ID in the secure server-side session
    session['user_id'] = user.id
    session['user_name'] = user.name

    # Redirect back to the main frontend page
    return redirect('/')

@auth_bp.route('/logout')
def logout():
    """Logs the user out by clearing the session."""
    session.pop('user_id', None)
    session.pop('user_name', None)
    return redirect('/')

def init_oauth(app):
    """Initializes the OAuth object with config from the app."""
    oauth.init_app(app)
    oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

@auth_bp.route('/login/local', methods=['POST'])
def login_local():
    """Handles login for the local test user defined in .env"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # Get credentials from environment
    local_user = os.getenv('LOCAL_TEST_USERNAME')
    local_pass = os.getenv('LOCAL_TEST_PASSWORD')

    if not local_user or not local_pass:
        return jsonify({"error": "Local test user is not configured."}), 500

    if username == local_user and password == local_pass:
        # Find or create the test user
        user = User.query.filter_by(username=local_user).first()
        if not user:
            try:
                user = User(
                    username=local_user,
                    name="Local Test User",
                    # Make this user an admin by default for easy testing
                    is_admin=True 
                )
                db.session.add(user)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                return jsonify({"error": "Failed to create local test user."}), 500

        # Log them in
        session['user_id'] = user.id
        session['user_name'] = user.name
        return jsonify({"message": "Login successful", "user_id": user.id, "name": user.name}), 200

    return jsonify({"error": "Invalid username or password"}), 401
