"""
Authentication Blueprint for KvízAréna.

Handles Google OAuth2 authentication flow.
"""
import os
from flask import Blueprint, url_for, redirect, session
from authlib.integrations.flask_client import OAuth
from app.database import db, User

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# This 'oauth' object will be configured from app.py
oauth = OAuth()

@auth_bp.route('/login/google')
def login_google():
    """Redirects to Google's login page."""
    # The redirect_uri must match *exactly* what's in Google Console
    redirect_uri = url_for('auth.callback_google', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/callback/google')
def callback_google():
    """Handles the callback from Google."""
    try:
        token = oauth.google.authorize_access_token()
        user_info = oauth.google.parse_id_token(token)
    except Exception as e:
        print(f"Error during OAuth callback: {e}")
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
