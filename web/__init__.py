from __future__ import annotations
from flask import Flask


def create_app() -> Flask:
    import os
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
    app = Flask(__name__, template_folder=template_dir)
    app.config["SECRET_KEY"] = "dev"
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    
    # Настройка для работы с reverse proxy
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1)

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