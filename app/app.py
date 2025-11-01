"""Flask application factory for Kvizarena."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from flask import Flask

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

    return app


def main() -> None:
    """Entry point for running the development server."""
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)


if __name__ == "__main__":
    main()
