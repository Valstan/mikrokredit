from __future__ import annotations
from flask import Flask
from datetime import timedelta


def create_app() -> Flask:
    import os
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
    app = Flask(__name__, template_folder=template_dir)
    app.config["SECRET_KEY"] = "mikrokredit_secret_key_2025_secure_random_string"
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
    
    # Настройка для работы с reverse proxy
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1, x_for=1, x_host=1, x_proto=1)

    # Ensure DB schema exists (Postgres/SQLite via DATABASE_URL)
    try:
        from app.db_sa import engine
        from app.models_sa import Base
        Base.metadata.create_all(bind=engine)
        print("✓ Database tables created/verified")
    except Exception as e:
        print(f"⚠ Database initialization warning: {e}")
        pass

    # Регистрация blueprints
    from .auth_views import bp as auth_bp
    app.register_blueprint(auth_bp)
    
    from .views import bp as views_bp
    app.register_blueprint(views_bp)
    
    from .tasks_views import bp as tasks_bp
    app.register_blueprint(tasks_bp)

    return app