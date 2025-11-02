"""Flask application factory for Kvizarena."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from .database import init_app as init_database
from .blueprints import register_blueprints
from .blueprints.auth import init_oauth


def create_app(config: dict[str, Any] | None = None) -> Flask:
    """Create and configure the Flask application instance."""
    load_dotenv()
    
    # Calculate absolute paths for frontend directories
    app_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(app_dir)
    frontend_dir = os.path.join(project_root, 'frontend')
    frontend_static_dir = os.path.join(frontend_dir, 'static')

    app = Flask(__name__, instance_relative_config=False, 
                template_folder=frontend_dir, 
                static_folder=frontend_static_dir)

    # Apply ProxyFix to trust headers from the reverse proxy
    # This ensures url_for(..., _external=True) generates the correct
    # public-facing URL (e.g., https://your.public.domain)
    # instead of the internal private IP (http://10.x.x.x).
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1
    )

    # Načte klíč z .env, a pokud tam není, použije "dev" jako záložní hodnotu
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev")

    # Načte URL databáze z .env, a pokud tam není, použije lokální sqlite
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "sqlite:///kvizarena.db"
    )

    # Natvrdo vypne modifikace
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if config:
        app.config.update(config)

    init_database(app)
    init_oauth(app)
    register_blueprints(app)

    @app.after_request
    def add_no_cache_headers(response):
        """
        Ensure responses aren't cached by proxies or browsers.
        This is critical for preventing session hijacking.
        """
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

    return app


def main() -> None:
    """Entry point for running the development server."""
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)


if __name__ == "__main__":
    main()
