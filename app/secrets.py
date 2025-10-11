"""
Управление секретами и конфигурацией
Читает переменные окружения из .env файла или системных переменных
"""
import os
from pathlib import Path
from typing import Optional


def load_env_file(env_path: Optional[str] = None) -> None:
    """
    Загружает переменные из .env файла
    Простая реализация без внешних зависимостей
    """
    if env_path is None:
        # Ищем .env в корне проекта
        project_root = Path(__file__).parent.parent
        env_path = project_root / ".env"
    else:
        env_path = Path(env_path)
    
    if not env_path.exists():
        return
    
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Пропускаем пустые строки и комментарии
            if not line or line.startswith('#'):
                continue
            
            # Парсим KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                # Убираем кавычки если есть
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                # Устанавливаем только если ещё не установлено
                if key not in os.environ:
                    os.environ[key] = value


def get_secret(key: str, default: Optional[str] = None) -> str:
    """
    Получает секрет из переменных окружения
    """
    value = os.environ.get(key, default)
    if value is None:
        raise ValueError(f"Secret '{key}' not found in environment variables or .env file")
    return value


# Загружаем .env при импорте модуля
load_env_file()

# Загружаем SMTP настройки из .env.smtp (если есть)
project_root = Path(__file__).parent.parent
smtp_env_path = project_root / ".env.smtp"
if smtp_env_path.exists():
    load_env_file(smtp_env_path)


# === БАЗА ДАННЫХ ===
DB_HOST = get_secret("DB_HOST", "localhost")
DB_PORT = get_secret("DB_PORT", "5432")
DB_NAME = get_secret("DB_NAME", "mikrokredit")
DB_USER = get_secret("DB_USER", "mikrokredit_user")
DB_PASSWORD = get_secret("DB_PASSWORD")

# Строка подключения к БД
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


# === АУТЕНТИФИКАЦИЯ ===
AUTH_PASSWORD = get_secret("AUTH_PASSWORD")


# === TELEGRAM ===
TELEGRAM_BOT_TOKEN = get_secret("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = get_secret("TELEGRAM_CHAT_ID")


# === YANDEX.DISK ===
YANDEX_DISK_TOKEN = get_secret("YANDEX_DISK_TOKEN")


# === ПРИЛОЖЕНИЕ ===
FLASK_SECRET_KEY = get_secret("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")
WEB_URL = get_secret("WEB_URL", "http://localhost")
SITE_URL = get_secret("SITE_URL", WEB_URL)  # URL для ссылок в email


# === EMAIL (SMTP) ===
SMTP_HOST = get_secret("SMTP_HOST", "smtp.yandex.ru")
SMTP_PORT = int(get_secret("SMTP_PORT", "587"))
SMTP_USER = get_secret("SMTP_USER", "")
SMTP_PASSWORD = get_secret("SMTP_PASSWORD", "")
EMAIL_FROM = get_secret("EMAIL_FROM", "noreply@mikrokredit.local")
EMAIL_NAME = get_secret("EMAIL_NAME", "МикроКредит")


# === TELEGRAM (дополнительно) ===
BOT_WORK_HOURS_START = int(get_secret("BOT_WORK_HOURS_START", "7"))
BOT_WORK_HOURS_END = int(get_secret("BOT_WORK_HOURS_END", "22"))


if __name__ == "__main__":
    # Для тестирования
    print("=== Секреты загружены ===")
    print(f"DATABASE_URL: postgresql://{DB_USER}:***@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print(f"AUTH_PASSWORD: {'*' * len(AUTH_PASSWORD)}")
    print(f"TELEGRAM_BOT_TOKEN: {TELEGRAM_BOT_TOKEN[:10]}***")
    print(f"TELEGRAM_CHAT_ID: {TELEGRAM_CHAT_ID}")
    print(f"YANDEX_DISK_TOKEN: {YANDEX_DISK_TOKEN[:10]}***")
    print(f"WEB_URL: {WEB_URL}")
    print("✓ Все секреты загружены успешно")

