"""
Конфигурация для десктопного приложения.
"""

import os
from pathlib import Path

# База данных - импортируем из secrets
try:
    from app.secrets import DATABASE_URL as SECRETS_DATABASE_URL
    DEFAULT_DATABASE_URL = SECRETS_DATABASE_URL
except ImportError:
    # Fallback если secrets.py недоступен (не должно случиться)
    DEFAULT_DATABASE_URL = "postgresql://user:pass@localhost:5432/mikrokredit"

# Получаем URL базы данных из переменной окружения или используем по умолчанию
DATABASE_URL = os.environ.get("MIKROKREDIT_DATABASE_URL", DEFAULT_DATABASE_URL)

# Redis конфигурация для кэширования и очередей
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

# API Gateway для межпроектного взаимодействия
API_GATEWAY_URL = os.environ.get("API_GATEWAY_URL", "http://localhost:8000")

# Название проекта для идентификации в общей сети
PROJECT_NAME = os.environ.get("PROJECT_NAME", "mikrokredit")

# Если нужно использовать SQLite (для отладки)
USE_SQLITE = os.environ.get("MIKROKREDIT_USE_SQLITE", "").lower() in ("1", "true", "yes")

if USE_SQLITE:
    # Используем локальную SQLite базу
    local_db_path = Path(__file__).parent.parent / "mikrokredit.db"
    DATABASE_URL = f"sqlite:///{local_db_path.absolute()}"
