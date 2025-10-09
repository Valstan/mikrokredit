#!/usr/bin/env python3
"""
Telegram бот сервер для обработки callback кнопок
Работает постоянно в фоне и обрабатывает нажатия на кнопки
"""

import sys
import os
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db_sa import get_session
from app.models_sa import TaskORM, TaskReminderORM
from sqlalchemy import select

# Конфигурация
TELEGRAM_TOKEN = "489021673:AAH7QDGmqzOMgT0W_wINvzWC1ihfljuFAKI"
WEB_URL = "http://73269587c9af.vps.myjino.ru"
BOT_WORK_HOURS_START = 7
BOT_WORK_HOURS_END = 22


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    log_msg = f"[{datetime.now()}] Получен callback: {data}"
    print(log_msg)
    
    try:
        parts = data.split('_')
        print(f"[{datetime.now()}] Разбор callback: {parts}")
        
        if data.startswith('task_complete_'):
            # Пометить задачу как выполненную
            task_id = int(parts[2])
            reminder_id = int(parts[3])
            print(f"[{datetime.now()}] Выполнение задачи {task_id}, напоминание {reminder_id}")
            
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
                    
                    # Отменяем все будущие напоминания для этой задачи
                    future_reminders = session.execute(
                        select(TaskReminderORM).where(
                            TaskReminderORM.task_id == task_id,
                            TaskReminderORM.sent == 0
                        )
                    ).scalars().all()
                    
                    for fr in future_reminders:
                        session.delete(fr)
                    
                    session.commit()
                    
                    await query.edit_message_text(
                        text=f"✅ <b>Задача выполнена!</b>\n\n{task.title}\n\n<i>Отличная работа! 🎉</i>",
                        parse_mode='HTML'
                    )
                    print(f"✓ Задача {task_id} отмечена как выполненная")
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
            task_url = f"{WEB_URL}/tasks/{task_id}"
            
            await query.edit_message_text(
                text=f"⏰ <b>Задача отложена</b>\n\nОткройте задачу для изменения напоминаний:\n\n{task_url}",
                parse_mode='HTML'
            )
            print(f"✓ Задача {task_id} отложена")
    
    except Exception as e:
        error_msg = f"[{datetime.now()}] ОШИБКА callback: {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        await query.edit_message_text(f"❌ Произошла ошибка: {str(e)[:100]}")


def main():
    """Основная функция - запуск бота"""
    print(f"Запуск Telegram бота...")
    print(f"Токен: {TELEGRAM_TOKEN[:20]}...")
    print(f"Рабочие часы: {BOT_WORK_HOURS_START}:00 - {BOT_WORK_HOURS_END}:00 MSK")
    
    # Создаём приложение
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Добавляем обработчик callback
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # Запускаем polling
    print("✓ Бот запущен и ожидает callback...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n✓ Бот остановлен")
        sys.exit(0)
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)

