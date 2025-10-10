"""
Модуль аутентификации
Простая система входа с паролем и блокировкой по IP
"""
from datetime import datetime, timedelta
from functools import wraps
from flask import session, request, redirect, url_for, flash
from typing import Dict, List
from app.secrets import AUTH_PASSWORD

# Конфигурация
MAX_ATTEMPTS = 3
BLOCK_DURATION_MINUTES = 5

# Хранилище попыток входа (IP -> список попыток)
# В production лучше использовать Redis
login_attempts: Dict[str, List[datetime]] = {}
blocked_ips: Dict[str, datetime] = {}


def get_client_ip() -> str:
    """Получить IP адрес клиента"""
    # Учитываем reverse proxy (nginx)
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    return request.remote_addr or 'unknown'


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


def verify_password(password: str) -> bool:
    """Проверить пароль"""
    return password == AUTH_PASSWORD


def clear_login_attempts(ip: str):
    """Очистить попытки входа для IP"""
    if ip in login_attempts:
        del login_attempts[ip]


def login_required(f):
    """Декоратор для защиты маршрутов"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def get_block_time_remaining(ip: str) -> int:
    """Получить оставшееся время блокировки в секундах"""
    if ip in blocked_ips:
        remaining = (blocked_ips[ip] - datetime.now()).total_seconds()
        return max(0, int(remaining))
    return 0

