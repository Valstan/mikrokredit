"""
ПРИМЕР ФАЙЛА СЕКРЕТОВ
Скопируйте в app/secrets.py и заполните своими данными
"""
import os
from pathlib import Path

# === БАЗА ДАННЫХ ===
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "mikrokredit")
DB_USER = os.getenv("DB_USER", "mikrokredit_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "YOUR_DB_PASSWORD_HERE")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# === АУТЕНТИФИКАЦИЯ ===
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "YOUR_AUTH_PASSWORD_HERE")

# === TELEGRAM ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID_HERE")

# === YANDEX.DISK ===
YANDEX_DISK_TOKEN = os.getenv("YANDEX_DISK_TOKEN", "YOUR_YANDEX_TOKEN_HERE")

# === ПРИЛОЖЕНИЕ ===
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "change-this-secret-key-in-production")
WEB_URL = os.getenv("WEB_URL", "http://localhost")

# === TELEGRAM (дополнительно) ===
BOT_WORK_HOURS_START = int(os.getenv("BOT_WORK_HOURS_START", "7"))
BOT_WORK_HOURS_END = int(os.getenv("BOT_WORK_HOURS_END", "22"))
