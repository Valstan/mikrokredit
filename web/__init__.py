from __future__ import annotations
from flask import Flask


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev"

    from .views import bp as views_bp
    app.register_blueprint(views_bp)

    return app
