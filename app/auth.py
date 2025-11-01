"""
OAuth-based authentication decorator for admin routes.
"""
from functools import wraps
from flask import session, redirect, url_for
from app.database import User

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session.get('user_id')

        if not user_id:
            # Not logged in, redirect to Google login
            return redirect(url_for('auth.login_google'))

        user = User.query.get(user_id)

        if not user or not user.is_admin:
            # Logged in, but not an admin
            return redirect(url_for('main.index')) # Redirect to homepage

        return f(*args, **kwargs)
    return decorated
