#!/usr/bin/env python3
"""
Сервис повторных напоминаний
Проверяет неподтверждённые напоминания и отправляет их повторно каждые 15 минут
Работает только с 7:00 до 22:00 MSK
"""

import sys
import os
from datetime import datetime, timedelta
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db_sa import get_session
from app.models_sa import TaskORM, TaskReminderORM
from sqlalchemy import select

# Конфигурация
TELEGRAM_TOKEN = "489021673:AAH7QDGmqzOMgT0W_wINvzWC1ihfljuFAKI"
TELEGRAM_CHAT_ID = 352096813
WEB_URL = "http://73269587c9af.vps.myjino.ru"

REPEAT_INTERVAL_MINUTES = 15
BOT_WORK_HOURS_START = 7
BOT_WORK_HOURS_END = 22


def is_work_hours() -> bool:
    """Проверка рабочих часов"""
    now = datetime.now()
    return BOT_WORK_HOURS_START <= now.hour < BOT_WORK_HOURS_END


def get_unacknowledged_reminders():
    """Получить неподтверждённые напоминания"""
    reminders = []
    now = datetime.now()
    repeat_threshold = now - timedelta(minutes=REPEAT_INTERVAL_MINUTES)
    
    with get_session() as session:
        # Находим отправленные, но неподтвержденные напоминания
        # которые были отправлены более 15 минут назад
        unack = session.execute(
            select(TaskReminderORM)
            .where(
                TaskReminderORM.sent == 1,
                TaskReminderORM.acknowledged == 0,
                TaskReminderORM.sent_at < repeat_threshold.isoformat()
            )
        ).scalars().all()
        
        for reminder in unack:
            task = session.get(TaskORM, reminder.task_id)
            if task and task.status == 0:  # Только для невыполненных
                reminders.append({
                    'reminder_id': reminder.id,
                    'task_id': task.id,
                    'task_title': task.title,
                    'task_description': task.description,
                    'importance': task.importance,
                    'due_date': task.due_date,
                    'sent_at': reminder.sent_at
                })
    
    return reminders


def format_repeat_message(task_data: dict) -> str:
    """Форматирование повторного напоминания"""
    importance_emoji = {1: "🔴", 2: "🟡", 3: "⚪"}
    emoji = importance_emoji.get(task_data['importance'], "⚪")
    
    message = f"{emoji} <b>🔔 ПОВТОРНОЕ НАПОМИНАНИЕ</b>\n\n"
    message += f"<b>{task_data['task_title']}</b>\n"
    
    if task_data.get('task_description'):
        desc = task_data['task_description']
        if len(desc) > 150:
            desc = desc[:150] + "..."
        message += f"\n{desc}\n"
    
    if task_data.get('due_date'):
        message += f"\n📅 Срок: {task_data['due_date'][:16]}"
    
    message += f"\n\n⏰ Первое напоминание было: {task_data['sent_at'][:16]}"
    message += f"\n💡 Следующее напоминание через {REPEAT_INTERVAL_MINUTES} минут"
    
    return message


def create_task_keyboard(task_id: int, reminder_id: int) -> InlineKeyboardMarkup:
    """Создать клавиатуру"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Выполнил", callback_data=f"task_complete_{task_id}_{reminder_id}"),
            InlineKeyboardButton("⏰ Отложить", callback_data=f"task_postpone_{task_id}_{reminder_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def send_repeat_reminder(reminder_data: dict, app: Application):
    """Отправить повторное напоминание"""
    message_text = format_repeat_message(reminder_data)
    keyboard = create_task_keyboard(reminder_data['task_id'], reminder_data['reminder_id'])
    
    try:
        message = await app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message_text,
            parse_mode='HTML',
            reply_markup=keyboard
        )
        
        # Обновляем время отправки
        with get_session() as session:
            reminder = session.get(TaskReminderORM, reminder_data['reminder_id'])
            if reminder:
                reminder.sent_at = datetime.now().isoformat()
                reminder.telegram_message_id = message.message_id
                session.commit()
        
        print(f"✓ Повторное напоминание: {reminder_data['task_title']}")
        return True
        
    except Exception as e:
        print(f"✗ Ошибка отправки: {e}")
        return False


async def check_and_send_repeats():
    """Проверить и отправить повторные напоминания"""
    if not is_work_hours():
        print(f"Вне рабочих часов ({BOT_WORK_HOURS_START}:00 - {BOT_WORK_HOURS_END}:00 MSK)")
        return
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Проверка неподтверждённых напоминаний...")
    
    reminders = get_unacknowledged_reminders()
    print(f"Найдено неподтверждённых напоминаний: {len(reminders)}")
    
    if not reminders:
        return
    
    # Создаём приложение
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    await app.initialize()
    
    # Отправляем повторные напоминания
    for reminder in reminders:
        await send_repeat_reminder(reminder, app)
        await asyncio.sleep(0.5)
    
    await app.shutdown()
    print(f"✅ Отправлено {len(reminders)} повторных напоминаний")


def main():
    """Основная функция"""
    try:
        asyncio.run(check_and_send_repeats())
        return 0
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

