#!/usr/bin/env python3
"""
Telegram бот для напоминаний о задачах
Отправляет уведомления с inline кнопками "Выполнил" и "Отложить"
"""

import sys
import os
from datetime import datetime, time as dt_time, timedelta
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
import asyncio

# Добавляем корень проекта в sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app.db_sa import get_session
from app.models_sa import TaskORM, TaskReminderORM
from sqlalchemy import select

# Конфигурация
TELEGRAM_TOKEN = "489021673:AAH7QDGmqzOMgT0W_wINvzWC1ihfljuFAKI"
TELEGRAM_CHAT_ID = 352096813

# Часы работы бота (MSK)
BOT_WORK_HOURS_START = 7   # 7:00
BOT_WORK_HOURS_END = 22     # 22:00


def is_work_hours() -> bool:
    """Проверка рабочих часов (7:00 - 22:00 MSK)"""
    now = datetime.now()
    current_hour = now.hour
    return BOT_WORK_HOURS_START <= current_hour < BOT_WORK_HOURS_END


def get_pending_reminders():
    """Получить напоминания которые нужно отправить"""
    if not is_work_hours():
        return []
    
    reminders = []
    now = datetime.now()
    
    with get_session() as session:
        # Находим неотправленные напоминания, время которых наступило
        pending = session.execute(
            select(TaskReminderORM)
            .where(
                TaskReminderORM.sent == 0,
                TaskReminderORM.reminder_time <= now.isoformat()
            )
        ).scalars().all()
        
        for reminder in pending:
            # Загружаем задачу
            task = session.get(TaskORM, reminder.task_id)
            if task and task.status == 0:  # Только для невыполненных
                reminders.append({
                    'reminder_id': reminder.id,
                    'task_id': task.id,
                    'task_title': task.title,
                    'task_description': task.description,
                    'importance': task.importance,
                    'due_date': task.due_date
                })
    
    return reminders


def format_task_message(task_data: dict) -> str:
    """Форматирование сообщения о задаче"""
    importance_emoji = {
        1: "🔴",
        2: "🟡",
        3: "⚪"
    }
    
    importance_text = {
        1: "Важная",
        2: "Нужная",
        3: "Хотелось бы"
    }
    
    emoji = importance_emoji.get(task_data['importance'], "⚪")
    imp_text = importance_text.get(task_data['importance'], "")
    
    message = f"{emoji} <b>НАПОМИНАНИЕ О ЗАДАЧЕ</b>\n\n"
    message += f"<b>{task_data['task_title']}</b>\n"
    
    if task_data.get('task_description'):
        desc = task_data['task_description']
        if len(desc) > 200:
            desc = desc[:200] + "..."
        message += f"\n{desc}\n"
    
    message += f"\n📌 Важность: {imp_text}"
    
    if task_data.get('due_date'):
        message += f"\n📅 Срок: {task_data['due_date'][:16]}"
    
    return message


def create_task_keyboard(task_id: int, reminder_id: int) -> InlineKeyboardMarkup:
    """Создать клавиатуру для задачи"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Выполнил", callback_data=f"task_complete_{task_id}_{reminder_id}"),
            InlineKeyboardButton("⏰ Отложить", callback_data=f"task_postpone_{task_id}_{reminder_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    parts = data.split('_')
    
    if data.startswith('task_complete_'):
        # Пометить задачу как выполненную
        task_id = int(parts[2])
        reminder_id = int(parts[3])
        
        with get_session() as session:
            task = session.get(TaskORM, task_id)
            if task:
                task.status = 1
                task.completed_at = datetime.now().isoformat()
                task.updated_at = datetime.now().isoformat()
                
                # Отмечаем напоминание как обработанное
                reminder = session.get(TaskReminderORM, reminder_id)
                if reminder:
                    reminder.acknowledged = 1
                    reminder.acknowledged_at = datetime.now().isoformat()
                
                session.commit()
                
                await query.edit_message_text(
                    text=f"✅ Задача выполнена!\n\n<b>{task.title}</b>\n\n<i>Отличная работа! 🎉</i>",
                    parse_mode='HTML'
                )
            else:
                await query.edit_message_text("❌ Задача не найдена")
    
    elif data.startswith('task_postpone_'):
        # Отложить задачу - открыть в браузере
        task_id = int(parts[2])
        reminder_id = int(parts[3])
        
        with get_session() as session:
            reminder = session.get(TaskReminderORM, reminder_id)
            if reminder:
                reminder.acknowledged = 1
                reminder.acknowledged_at = datetime.now().isoformat()
                session.commit()
        
        # URL к задаче
        task_url = f"http://73269587c9af.vps.myjino.ru/tasks/{task_id}"
        
        await query.edit_message_text(
            text=f"⏰ Задача отложена\n\nОткройте задачу для изменения напоминаний:\n{task_url}",
            parse_mode='HTML'
        )


async def send_task_reminder(reminder_data: dict, app: Application):
    """Отправить напоминание о задаче"""
    message_text = format_task_message(reminder_data)
    keyboard = create_task_keyboard(reminder_data['task_id'], reminder_data['reminder_id'])
    
    try:
        message = await app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message_text,
            parse_mode='HTML',
            reply_markup=keyboard
        )
        
        # Сохраняем ID сообщения и отмечаем как отправленное
        with get_session() as session:
            reminder = session.get(TaskReminderORM, reminder_data['reminder_id'])
            if reminder:
                reminder.sent = 1
                reminder.sent_at = datetime.now().isoformat()
                reminder.telegram_message_id = message.message_id
                session.commit()
        
        print(f"✓ Отправлено напоминание о задаче: {reminder_data['task_title']}")
        return True
        
    except Exception as e:
        print(f"✗ Ошибка отправки: {e}")
        return False


async def check_and_send_reminders():
    """Проверить и отправить все pending напоминания"""
    if not is_work_hours():
        print(f"Вне рабочих часов ({BOT_WORK_HOURS_START}:00 - {BOT_WORK_HOURS_END}:00 MSK)")
        return
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Проверка напоминаний...")
    
    reminders = get_pending_reminders()
    print(f"Найдено напоминаний для отправки: {len(reminders)}")
    
    if not reminders:
        return
    
    # Создаём приложение для отправки
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    await app.initialize()
    
    # Отправляем все напоминания
    for reminder in reminders:
        await send_task_reminder(reminder, app)
        await asyncio.sleep(0.5)  # Небольшая задержка между сообщениями
    
    await app.shutdown()
    print(f"✅ Отправлено {len(reminders)} напоминаний")


def main():
    """Основная функция"""
    try:
        asyncio.run(check_and_send_reminders())
        return 0
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

