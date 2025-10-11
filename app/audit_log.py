"""
Модуль логирования важных действий пользователей
Audit trail для безопасности и отслеживания действий
"""
import logging
from datetime import datetime
from typing import Optional
import os

# Настройка логгера
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

audit_logger = logging.getLogger('audit')
audit_logger.setLevel(logging.INFO)

# Файловый handler
handler = logging.FileHandler(os.path.join(log_dir, 'audit.log'), encoding='utf-8')
handler.setLevel(logging.INFO)

# Формат логов
formatter = logging.Formatter(
    '%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
handler.setFormatter(formatter)
audit_logger.addHandler(handler)


def log_user_registered(user_id: int, email: str, ip_address: str = None):
    """Логирование регистрации нового пользователя"""
    audit_logger.info(f"USER_REGISTERED | user_id={user_id} | email={email} | ip={ip_address or 'unknown'}")


def log_user_login(user_id: int, email: str, ip_address: str = None, success: bool = True):
    """Логирование входа пользователя"""
    status = "SUCCESS" if success else "FAILED"
    audit_logger.info(f"USER_LOGIN_{status} | user_id={user_id} | email={email} | ip={ip_address or 'unknown'}")


def log_user_logout(user_id: int, email: str):
    """Логирование выхода пользователя"""
    audit_logger.info(f"USER_LOGOUT | user_id={user_id} | email={email}")


def log_password_changed(user_id: int, email: str, ip_address: str = None):
    """Логирование смены пароля"""
    audit_logger.info(f"PASSWORD_CHANGED | user_id={user_id} | email={email} | ip={ip_address or 'unknown'}")


def log_password_reset_requested(email: str, ip_address: str = None):
    """Логирование запроса восстановления пароля"""
    audit_logger.info(f"PASSWORD_RESET_REQUESTED | email={email} | ip={ip_address or 'unknown'}")


def log_password_reset_completed(user_id: int, email: str, ip_address: str = None):
    """Логирование завершения восстановления пароля"""
    audit_logger.info(f"PASSWORD_RESET_COMPLETED | user_id={user_id} | email={email} | ip={ip_address or 'unknown'}")


def log_email_verified(user_id: int, email: str):
    """Логирование подтверждения email"""
    audit_logger.info(f"EMAIL_VERIFIED | user_id={user_id} | email={email}")


def log_telegram_linked(user_id: int, email: str, telegram_username: str = None):
    """Логирование привязки Telegram"""
    audit_logger.info(f"TELEGRAM_LINKED | user_id={user_id} | email={email} | telegram=@{telegram_username or 'unknown'}")


def log_telegram_unlinked(user_id: int, email: str):
    """Логирование отвязки Telegram"""
    audit_logger.info(f"TELEGRAM_UNLINKED | user_id={user_id} | email={email}")


def log_user_activated(admin_id: int, target_user_id: int, target_email: str):
    """Логирование активации пользователя"""
    audit_logger.info(f"USER_ACTIVATED | admin_id={admin_id} | target_user_id={target_user_id} | target_email={target_email}")


def log_user_deactivated(admin_id: int, target_user_id: int, target_email: str):
    """Логирование деактивации пользователя"""
    audit_logger.info(f"USER_DEACTIVATED | admin_id={admin_id} | target_user_id={target_user_id} | target_email={target_email}")


def log_admin_granted(admin_id: int, target_user_id: int, target_email: str):
    """Логирование назначения администратора"""
    audit_logger.info(f"ADMIN_GRANTED | admin_id={admin_id} | target_user_id={target_user_id} | target_email={target_email}")


def log_admin_revoked(admin_id: int, target_user_id: int, target_email: str):
    """Логирование снятия прав администратора"""
    audit_logger.info(f"ADMIN_REVOKED | admin_id={admin_id} | target_user_id={target_user_id} | target_email={target_email}")


def log_account_deleted(user_id: int, email: str, ip_address: str = None):
    """Логирование удаления аккаунта"""
    audit_logger.info(f"ACCOUNT_DELETED | user_id={user_id} | email={email} | ip={ip_address or 'unknown'}")


def log_security_event(event_type: str, details: str, ip_address: str = None):
    """Логирование событий безопасности"""
    audit_logger.warning(f"SECURITY_EVENT | type={event_type} | details={details} | ip={ip_address or 'unknown'}")


def log_ip_blocked(ip_address: str, attempts: int):
    """Логирование блокировки IP"""
    audit_logger.warning(f"IP_BLOCKED | ip={ip_address} | attempts={attempts}")

