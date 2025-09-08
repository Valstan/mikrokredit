from __future__ import annotations
from flask import Flask


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev"

    # Ensure DB schema exists (Postgres/SQLite via DATABASE_URL)
    try:
        from app.db_sa import engine
        from app.models_sa import Base
        Base.metadata.create_all(bind=engine)
    except Exception:
        # If creation fails, app will still start; requests may error until DB is ready
        pass

    from .views import bp as views_bp
    app.register_blueprint(views_bp)

    return app
