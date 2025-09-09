"""
Конфигурация для десктопного приложения.
"""

import os
from pathlib import Path

# База данных по умолчанию - PostgreSQL на Render
DEFAULT_DATABASE_URL = "postgresql://mikrokredit_user:6xoKkR0wfL1Zc0YcmqcE4GSjBSXlQ8Rv@dpg-d308623e5dus73dfrrsg-a.oregon-postgres.render.com/mikrokredit"

# Получаем URL базы данных из переменной окружения или используем по умолчанию
DATABASE_URL = os.environ.get("MIKROKREDIT_DATABASE_URL", DEFAULT_DATABASE_URL)

# Если нужно использовать локальную SQLite базу (для отладки)
USE_LOCAL_SQLITE = os.environ.get("MIKROKREDIT_USE_LOCAL", "").lower() in ("1", "true", "yes")

if USE_LOCAL_SQLITE:
    # Используем локальную SQLite базу
    local_db_path = Path(__file__).parent.parent / "mikrokredit.db"
    DATABASE_URL = f"sqlite:///{local_db_path.absolute()}"
