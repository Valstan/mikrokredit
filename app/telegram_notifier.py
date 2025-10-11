"""
Сервис отправки уведомлений в Telegram
"""
import requests
from typing import Optional
from datetime import datetime

from app.secrets import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


class TelegramNotifier:
    """Отправка уведомлений в Telegram"""
    
    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token or TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_to_user(self, user_id: int, text: str, parse_mode: str = "HTML", reply_markup=None) -> Optional[int]:
        """
        Отправляет сообщение конкретному пользователю
        
        Args:
            user_id: ID пользователя в системе
            text: Текст сообщения
            parse_mode: Режим парсинга (HTML/Markdown)
            reply_markup: Клавиатура для интерактивных кнопок
            
        Returns:
            message_id если успешно, иначе None
        """
        # Получаем telegram_chat_id пользователя из БД
        from app.db_sa import get_session
        from app.models_sa import UserORM
        
        with get_session() as session:
            user = session.query(UserORM).filter_by(id=user_id).first()
            
            if not user or not user.telegram_chat_id:
                print(f"⚠️  User {user_id} has no Telegram linked")
                return None
            
            if not user.telegram_notifications:
                print(f"⚠️  User {user_id} has Telegram notifications disabled")
                return None
            
            chat_id = user.telegram_chat_id
        
        # Отправляем сообщение
        return self._send_to_chat(chat_id, text, parse_mode, reply_markup)
    
    def _send_to_chat(self, chat_id: str, text: str, parse_mode: str = "HTML", reply_markup=None) -> Optional[int]:
        """
        Внутренний метод отправки сообщения в конкретный чат
        
        Returns:
            message_id если успешно, иначе None
        """
        if not self.bot_token or not chat_id:
            print("⚠️  Telegram credentials not configured")
            return None
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            
            if reply_markup:
                payload["reply_markup"] = reply_markup
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    return result["result"]["message_id"]
            else:
                print(f"❌ Telegram API error: {response.status_code}")
                print(response.text)
            
            return None
        
        except Exception as e:
            print(f"❌ Telegram send error: {e}")
            return None
    
    def send_message(self, text: str, parse_mode: str = "HTML") -> Optional[int]:
        """
        Отправляет сообщение в Telegram на дефолтный chat_id
        УСТАРЕЛО: Используйте send_to_user() для персональных уведомлений
        
        Returns:
            message_id если успешно, иначе None
        """
        if not self.chat_id:
            print("⚠️  Default chat_id not configured")
            return None
        
        return self._send_to_chat(self.chat_id, text, parse_mode)
    
    def send_task_reminder_to_user(
        self,
        user_id: int,
        task_title: str,
        task_id: int,
        reminder_id: int,
        reminder_type: str = "general"
    ) -> Optional[int]:
        """
        Отправляет напоминание о задаче конкретному пользователю с интерактивными кнопками
        
        Args:
            user_id: ID пользователя
            task_title: Название задачи
            task_id: ID задачи
            reminder_id: ID напоминания
            reminder_type: Тип напоминания
        """
        from app.secrets import WEB_URL
        
        # Форматируем сообщение
        icon = "🔔"
        type_text = ""
        
        if reminder_type == "before_start":
            icon = "⏰"
            type_text = "скоро начнется"
        elif reminder_type == "before_end":
            icon = "⏱️"
            type_text = "скоро закончится"
        elif reminder_type == "periodic_before":
            icon = "🔔"
            type_text = "напоминание"
        elif reminder_type == "periodic_during":
            icon = "▶️"
            type_text = "в процессе"
        elif reminder_type == "after_end":
            icon = "✅"
            type_text = "завершено"
        
        now = datetime.now().strftime("%H:%M")
        
        message = f"{icon} <b>Напоминание о задаче</b>\n\n"
        message += f"📋 {task_title}\n"
        if type_text:
            message += f"ℹ️ {type_text}\n"
        message += f"🕐 {now}\n"
        message += f"\n<a href='{WEB_URL}/tasks/{task_id}'>Открыть задачу</a>"
        
        # Создаем интерактивные кнопки
        reply_markup = {
            "inline_keyboard": [[
                {"text": "✅ Выполнил", "callback_data": f"task_complete_{task_id}_{reminder_id}"},
                {"text": "⏰ Отложить", "callback_data": f"task_postpone_{task_id}_{reminder_id}"}
            ]]
        }
        
        return self.send_to_user(user_id, message, reply_markup=reply_markup)
    
    def send_task_reminder(
        self,
        task_title: str,
        task_id: int,
        reminder_type: str = "general"
    ) -> Optional[int]:
        """
        Отправляет напоминание о задаче
        
        Args:
            task_title: Название задачи
            task_id: ID задачи
            reminder_type: Тип напоминания (before_start, before_end, etc)
        """
        # Форматируем сообщение
        icon = "🔔"
        type_text = ""
        
        if reminder_type == "before_start":
            icon = "⏰"
            type_text = "скоро начнется"
        elif reminder_type == "before_end":
            icon = "⏱️"
            type_text = "скоро закончится"
        elif reminder_type == "periodic_before":
            icon = "🔔"
            type_text = "напоминание"
        elif reminder_type == "periodic_during":
            icon = "▶️"
            type_text = "в процессе"
        elif reminder_type == "after_end":
            icon = "✅"
            type_text = "завершено"
        
        now = datetime.now().strftime("%H:%M")
        
        message = f"{icon} <b>Напоминание о задаче</b>\n\n"
        message += f"📋 {task_title}\n"
        if type_text:
            message += f"ℹ️ {type_text}\n"
        message += f"🕐 {now}\n"
        message += f"\n<a href='http://ваш-домен/tasks/{task_id}/edit/v2'>Открыть задачу</a>"
        
        return self.send_message(message)
    
    def send_loan_reminder(
        self,
        org_name: str,
        amount: float,
        date_str: str,
        days_left: int,
        loan_id: int
    ) -> Optional[int]:
        """
        Отправляет напоминание о платеже по займу
        
        Args:
            org_name: Название банка
            amount: Сумма платежа
            date_str: Дата платежа
            days_left: Дней до платежа
            loan_id: ID займа
        """
        # Определяем иконку по срочности
        if days_left < 0:
            icon = "🔴"
            urgency = "ПРОСРОЧЕНО"
        elif days_left == 0:
            icon = "🔴"
            urgency = "СЕГОДНЯ"
        elif days_left == 1:
            icon = "🟠"
            urgency = "ЗАВТРА"
        elif days_left <= 2:
            icon = "🟡"
            urgency = f"через {days_left} дня"
        elif days_left <= 5:
            icon = "🟡"
            urgency = f"через {days_left} дней"
        else:
            icon = "🔵"
            urgency = f"через {days_left} дней"
        
        message = f"{icon} <b>Напоминание о платеже</b>\n\n"
        message += f"🏦 {org_name}\n"
        message += f"💰 {amount:.2f} ₽\n"
        message += f"📅 {date_str}\n"
        message += f"⏰ {urgency}\n"
        message += f"\n<a href='http://ваш-домен/loan/{loan_id}/v2'>Открыть займ</a>"
        
        return self.send_message(message)


# Глобальный экземпляр
telegram_notifier = TelegramNotifier()


def send_task_reminder_notification(task_title: str, task_id: int, reminder_type: str = "general") -> bool:
    """
    Удобная функция для отправки напоминания о задаче
    
    Returns:
        True если успешно отправлено
    """
    message_id = telegram_notifier.send_task_reminder(task_title, task_id, reminder_type)
    return message_id is not None


def send_loan_reminder_notification(
    org_name: str,
    amount: float,
    date_str: str,
    days_left: int,
    loan_id: int
) -> bool:
    """
    Удобная функция для отправки напоминания о платеже
    
    Returns:
        True если успешно отправлено
    """
    message_id = telegram_notifier.send_loan_reminder(org_name, amount, date_str, days_left, loan_id)
    return message_id is not None

