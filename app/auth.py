"""
Модуль аутентификации для многопользовательской системы
Поддержка регистрации, входа, восстановления пароля, email верификации
"""
from datetime import datetime, timedelta
from functools import wraps
from flask import session, request, redirect, url_for, flash, g
from typing import Dict, List, Optional, Tuple
import bcrypt
import secrets
import re

# Конфигурация
MAX_ATTEMPTS = 3
BLOCK_DURATION_MINUTES = 5
TOKEN_EXPIRY_HOURS = 24  # Для email verification и password reset
PASSWORD_MIN_LENGTH = 8

# Хранилище попыток входа (IP -> список попыток)
# В production лучше использовать Redis
login_attempts: Dict[str, List[datetime]] = {}
blocked_ips: Dict[str, datetime] = {}


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_client_ip() -> str:
    """Получить IP адрес клиента"""
    # Учитываем reverse proxy (nginx)
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    return request.remote_addr or 'unknown'


def is_valid_email(email: str) -> bool:
    """Проверка валидности email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_strong_password(password: str) -> Tuple[bool, Optional[str]]:
    """
    Проверка надежности пароля
    Returns: (is_valid, error_message)
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"Пароль должен содержать минимум {PASSWORD_MIN_LENGTH} символов"
    
    # Опционально: более строгие требования
    # if not re.search(r'[A-Z]', password):
    #     return False, "Пароль должен содержать заглавную букву"
    # if not re.search(r'[a-z]', password):
    #     return False, "Пароль должен содержать строчную букву"
    # if not re.search(r'[0-9]', password):
    #     return False, "Пароль должен содержать цифру"
    
    return True, None


# ==================== РАБОТА С ПАРОЛЯМИ ====================

def hash_password(password: str) -> str:
    """Хеширование пароля с использованием bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Проверка пароля"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False


# ==================== РАБОТА С ПОЛЬЗОВАТЕЛЯМИ ====================

def create_user(email: str, password: str, full_name: str = None) -> Optional[int]:
    """
    Создание нового пользователя
    Returns: user_id если успешно, иначе None
    """
    from app.db_sa import get_session
    from app.models_sa import UserORM
    
    # Валидация
    if not is_valid_email(email):
        return None
    
    is_strong, error = is_strong_password(password)
    if not is_strong:
        return None
    
    # Проверка существования
    with get_session() as db:
        existing = db.query(UserORM).filter_by(email=email).first()
        if existing:
            return None
        
        # Создаем пользователя
        now = datetime.now().isoformat()
        user = UserORM(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            is_active=True,
            is_admin=False,
            email_verified=False,
            email_notifications=True,
            telegram_notifications=True,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        db.flush()
        user_id = user.id
        
    return user_id


def authenticate_user(email: str, password: str) -> Optional[int]:
    """
    Аутентификация пользователя
    Returns: user_id если успешно, иначе None
    """
    from app.db_sa import get_session
    from app.models_sa import UserORM
    
    with get_session() as db:
        user = db.query(UserORM).filter_by(email=email).first()
        
        if not user:
            return None
        
        if not user.is_active:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        # Обновляем время последнего входа
        user.last_login_at = datetime.now().isoformat()
        db.flush()
        
        return user.id


def get_user_by_id(user_id: int):
    """Получить пользователя по ID"""
    from app.db_sa import get_session
    from app.models_sa import UserORM
    
    with get_session() as db:
        user = db.query(UserORM).filter_by(id=user_id).first()
        if user:
            # Отделяем объект от сессии, чтобы он был доступен вне контекста
            db.expunge(user)
        return user


def get_user_by_email(email: str):
    """Получить пользователя по email"""
    from app.db_sa import get_session
    from app.models_sa import UserORM
    
    with get_session() as db:
        user = db.query(UserORM).filter_by(email=email).first()
        if user:
            # Отделяем объект от сессии, чтобы он был доступен вне контекста
            db.expunge(user)
        return user


def get_current_user():
    """
    Получить текущего пользователя из сессии
    Используется в декораторе login_required и в шаблонах
    """
    if not hasattr(g, 'user'):
        user_id = session.get('user_id')
        if user_id:
            g.user = get_user_by_id(user_id)
        else:
            g.user = None
    return g.user


def update_user_password(user_id: int, new_password: str) -> bool:
    """Обновление пароля пользователя"""
    from app.db_sa import get_session
    from app.models_sa import UserORM
    
    is_strong, error = is_strong_password(new_password)
    if not is_strong:
        return False
    
    with get_session() as db:
        user = db.query(UserORM).filter_by(id=user_id).first()
        if not user:
            return False
        
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.now().isoformat()
        db.flush()
    
    return True


# ==================== EMAIL ВЕРИФИКАЦИЯ ====================

def generate_verification_token(user_id: int) -> str:
    """Создать токен для верификации email"""
    from app.db_sa import get_session
    from app.models_sa import EmailVerificationTokenORM
    
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=TOKEN_EXPIRY_HOURS)
    
    with get_session() as db:
        token_obj = EmailVerificationTokenORM(
            user_id=user_id,
            token=token,
            expires_at=expires_at.isoformat(),
            used=False,
            created_at=datetime.now().isoformat(),
        )
        db.add(token_obj)
        db.flush()
    
    return token


def verify_email_token(token: str) -> Optional[int]:
    """
    Проверить токен верификации email
    Returns: user_id если успешно, иначе None
    """
    from app.db_sa import get_session
    from app.models_sa import EmailVerificationTokenORM, UserORM
    
    with get_session() as db:
        token_obj = db.query(EmailVerificationTokenORM).filter_by(token=token).first()
        
        if not token_obj:
            return None
        
        if token_obj.used:
            return None
        
        # Проверка срока действия
        expires_at = datetime.fromisoformat(token_obj.expires_at)
        if datetime.now() > expires_at:
            return None
        
        # Отмечаем как использованный
        token_obj.used = True
        token_obj.used_at = datetime.now().isoformat()
        
        # Верифицируем email пользователя
        user = db.query(UserORM).filter_by(id=token_obj.user_id).first()
        if user:
            user.email_verified = True
            user.email_verified_at = datetime.now().isoformat()
            user.updated_at = datetime.now().isoformat()
            db.flush()
            return user.id
        
    return None


# ==================== СБРОС ПАРОЛЯ ====================

def generate_password_reset_token(email: str) -> Optional[str]:
    """
    Создать токен для сброса пароля
    Returns: token если пользователь найден, иначе None
    """
    from app.db_sa import get_session
    from app.models_sa import PasswordResetTokenORM, UserORM
    
    with get_session() as db:
        user = db.query(UserORM).filter_by(email=email).first()
        if not user:
            return None
        
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=TOKEN_EXPIRY_HOURS)
        
        token_obj = PasswordResetTokenORM(
            user_id=user.id,
            token=token,
            expires_at=expires_at.isoformat(),
            used=False,
            created_at=datetime.now().isoformat(),
        )
        db.add(token_obj)
        db.flush()
        
        return token


def reset_password(token: str, new_password: str) -> bool:
    """
    Сбросить пароль по токену
    Returns: True если успешно, иначе False
    """
    from app.db_sa import get_session
    from app.models_sa import PasswordResetTokenORM, UserORM
    
    is_strong, error = is_strong_password(new_password)
    if not is_strong:
        return False
    
    with get_session() as db:
        token_obj = db.query(PasswordResetTokenORM).filter_by(token=token).first()
        
        if not token_obj:
            return False
        
        if token_obj.used:
            return False
        
        # Проверка срока действия
        expires_at = datetime.fromisoformat(token_obj.expires_at)
        if datetime.now() > expires_at:
            return False
        
        # Отмечаем как использованный
        token_obj.used = True
        token_obj.used_at = datetime.now().isoformat()
        
        # Обновляем пароль
        user = db.query(UserORM).filter_by(id=token_obj.user_id).first()
        if user:
            user.password_hash = hash_password(new_password)
            user.updated_at = datetime.now().isoformat()
            db.flush()
            return True
    
    return False


# ==================== ЗАЩИТА ОТ БРУТФОРСА ====================

def is_ip_blocked(ip: str) -> bool:
    """Проверить заблокирован ли IP"""
    if ip in blocked_ips:
        block_time = blocked_ips[ip]
        if datetime.now() < block_time:
            return True
        else:
            # Блокировка истекла
            del blocked_ips[ip]
            if ip in login_attempts:
                del login_attempts[ip]
    return False


def add_login_attempt(ip: str) -> int:
    """
    Добавить попытку входа
    Возвращает количество оставшихся попыток
    """
    now = datetime.now()
    
    # Инициализируем список попыток для IP
    if ip not in login_attempts:
        login_attempts[ip] = []
    
    # Добавляем текущую попытку
    login_attempts[ip].append(now)
    
    # Убираем старые попытки (старше 10 минут)
    login_attempts[ip] = [
        attempt for attempt in login_attempts[ip]
        if now - attempt < timedelta(minutes=10)
    ]
    
    attempts_count = len(login_attempts[ip])
    
    # Если превышено количество попыток - блокируем
    if attempts_count >= MAX_ATTEMPTS:
        blocked_ips[ip] = now + timedelta(minutes=BLOCK_DURATION_MINUTES)
        return 0
    
    return MAX_ATTEMPTS - attempts_count


def clear_login_attempts(ip: str):
    """Очистить попытки входа для IP"""
    if ip in login_attempts:
        del login_attempts[ip]


def get_block_time_remaining(ip: str) -> int:
    """Получить оставшееся время блокировки в секундах"""
    if ip in blocked_ips:
        remaining = (blocked_ips[ip] - datetime.now()).total_seconds()
        return max(0, int(remaining))
    return 0


# ==================== ДЕКОРАТОРЫ ====================

def login_required(f):
    """Декоратор для защиты маршрутов - требуется вход в систему"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        
        # Проверяем существование пользователя
        user = get_user_by_id(user_id)
        if not user or not user.is_active:
            session.clear()
            flash('Ваша сессия истекла. Пожалуйста, войдите снова', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        
        # Сохраняем пользователя в g для доступа из view
        g.user = user
        
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Декоратор для защиты admin маршрутов"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        
        user = get_user_by_id(user_id)
        if not user or not user.is_active:
            session.clear()
            flash('Ваша сессия истекла', 'warning')
            return redirect(url_for('auth.login'))
        
        if not user.is_admin:
            flash('У вас нет доступа к этой странице', 'danger')
            return redirect(url_for('views.dashboard'))
        
        g.user = user
        
        return f(*args, **kwargs)
    return decorated_function
