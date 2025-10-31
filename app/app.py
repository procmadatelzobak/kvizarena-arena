"""Flask application factory for Kvizarena."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from flask import Flask

from .database import init_app as init_database
from .blueprints import register_blueprints


def create_app(config: dict[str, Any] | None = None) -> Flask:
    """Create and configure the Flask application instance."""
    load_dotenv()

    app = Flask(__name__, instance_relative_config=False, template_folder='../frontend', static_folder='../frontend/static')

    app.config.setdefault("SECRET_KEY", os.getenv("SECRET_KEY", "dev"))
    app.config.setdefault(
        "SQLALCHEMY_DATABASE_URI",
        os.getenv("DATABASE_URL", "sqlite:///kvizarena.db"),
    )
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)

    if config:
        app.config.update(config)

    init_database(app)
    register_blueprints(app)

    return app


def main() -> None:
    """Entry point for running the development server."""
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)


if __name__ == "__main__":
    main()
