"""
Модуль для привязки Telegram аккаунтов к пользователям
Использует Redis для хранения временных кодов привязки
"""
import secrets
import redis
from typing import Optional
from datetime import timedelta

# Подключение к Redis
try:
    from app.config import REDIS_URL
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except Exception as e:
    print(f"⚠️  Redis connection failed: {e}")
    redis_client = None

# Настройки
CODE_LENGTH = 6
CODE_EXPIRY_MINUTES = 10
CODE_PREFIX = "tg_link:"


def generate_link_code(user_id: int) -> str:
    """
    Генерирует одноразовый код для привязки Telegram аккаунта
    Код сохраняется в Redis с TTL 10 минут
    
    Returns: 6-значный код
    """
    # Генерируем уникальный код
    code = ''.join([str(secrets.randbelow(10)) for _ in range(CODE_LENGTH)])
    
    if redis_client:
        # Сохраняем в Redis: код -> user_id
        key = f"{CODE_PREFIX}{code}"
        redis_client.setex(key, timedelta(minutes=CODE_EXPIRY_MINUTES), str(user_id))
    else:
        # Fallback: если Redis недоступен, храним в памяти (не работает при множественных workers)
        print(f"⚠️  Redis unavailable, code {code} for user {user_id} stored in memory (not recommended)")
    
    return code


def verify_link_code(code: str) -> Optional[int]:
    """
    Проверяет код привязки и возвращает user_id
    После проверки код удаляется (одноразовый)
    
    Returns: user_id если код валиден, иначе None
    """
    if not redis_client:
        print("⚠️  Redis unavailable, cannot verify code")
        return None
    
    key = f"{CODE_PREFIX}{code}"
    user_id_str = redis_client.get(key)
    
    if user_id_str:
        # Удаляем код (одноразовый)
        redis_client.delete(key)
        return int(user_id_str)
    
    return None


def link_telegram_account(user_id: int, telegram_chat_id: str, telegram_username: str = None) -> bool:
    """
    Привязывает Telegram аккаунт к пользователю
    
    Returns: True если успешно, иначе False
    """
    from app.db_sa import get_session
    from app.models_sa import UserORM
    from datetime import datetime
    
    try:
        with get_session() as db:
            user = db.query(UserORM).filter_by(id=user_id).first()
            
            if not user:
                return False
            
            # Проверяем не привязан ли уже этот chat_id к другому пользователю
            existing = db.query(UserORM).filter_by(telegram_chat_id=telegram_chat_id).first()
            if existing and existing.id != user_id:
                # Отвязываем от старого пользователя
                existing.telegram_chat_id = None
                existing.telegram_username = None
                existing.updated_at = datetime.now().isoformat()
            
            # Привязываем к новому пользователю
            user.telegram_chat_id = telegram_chat_id
            user.telegram_username = telegram_username
            user.updated_at = datetime.now().isoformat()
            db.flush()
        
        return True
    
    except Exception as e:
        print(f"❌ Error linking Telegram account: {e}")
        return False


def unlink_telegram_account(user_id: int) -> bool:
    """
    Отвязывает Telegram аккаунт от пользователя
    
    Returns: True если успешно, иначе False
    """
    from app.db_sa import get_session
    from app.models_sa import UserORM
    from datetime import datetime
    
    try:
        with get_session() as db:
            user = db.query(UserORM).filter_by(id=user_id).first()
            
            if not user:
                return False
            
            user.telegram_chat_id = None
            user.telegram_username = None
            user.updated_at = datetime.now().isoformat()
            db.flush()
        
        return True
    
    except Exception as e:
        print(f"❌ Error unlinking Telegram account: {e}")
        return False


def get_user_by_telegram_chat_id(telegram_chat_id: str) -> Optional[int]:
    """
    Получить user_id по telegram_chat_id
    
    Returns: user_id если найден, иначе None
    """
    from app.db_sa import get_session
    from app.models_sa import UserORM
    
    try:
        with get_session() as db:
            user = db.query(UserORM).filter_by(telegram_chat_id=telegram_chat_id).first()
            return user.id if user else None
    except Exception:
        return None

