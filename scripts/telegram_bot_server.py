#!/usr/bin/env python3
"""
Telegram бот сервер для обработки callback кнопок
Работает постоянно в фоне и обрабатывает нажатия на кнопки
"""

import sys
import os
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

# Добавляем корень проекта в sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app.db_sa import get_session
from app.models_sa import TaskORM, TaskReminderORM, UserORM
from app.secrets import TELEGRAM_BOT_TOKEN, WEB_URL, BOT_WORK_HOURS_START, BOT_WORK_HOURS_END
from app.telegram_auth import verify_link_code, link_telegram_account, get_user_by_telegram_chat_id
from sqlalchemy import select

# Конфигурация
TELEGRAM_TOKEN = TELEGRAM_BOT_TOKEN


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


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    chat_id = str(update.effective_chat.id)
    username = update.effective_user.username
    
    # Проверяем есть ли код привязки в аргументах
    if context.args and len(context.args) > 0:
        code = context.args[0]
        print(f"[{datetime.now()}] Получен код привязки: {code} от chat_id: {chat_id}")
        
        # Проверяем код
        user_id = verify_link_code(code)
        
        if user_id:
            # Привязываем аккаунт
            success = link_telegram_account(user_id, chat_id, username)
            
            if success:
                # Получаем информацию о пользователе
                with get_session() as session:
                    user = session.get(UserORM, user_id)
                    user_name = user.full_name or user.email if user else "пользователь"
                
                await update.message.reply_text(
                    f"✅ <b>Telegram успешно подключен!</b>\n\n"
                    f"👤 Аккаунт: {user_name}\n"
                    f"💬 Ваш Telegram: @{username or 'ID: ' + chat_id}\n\n"
                    f"Теперь вы будете получать уведомления о займах и задачах прямо в Telegram!\n\n"
                    f"📱 Доступные команды:\n"
                    f"/myaccount - информация о вашем аккаунте\n"
                    f"/help - справка",
                    parse_mode='HTML'
                )
                print(f"✓ Успешно привязан user_id {user_id} к chat_id {chat_id}")
            else:
                await update.message.reply_text(
                    "❌ Ошибка при привязке аккаунта. Попробуйте сгенерировать новый код."
                )
        else:
            await update.message.reply_text(
                "❌ <b>Код недействителен или истек</b>\n\n"
                "Код действителен только 10 минут.\n"
                "Пожалуйста, сгенерируйте новый код в личном кабинете:\n"
                f"{WEB_URL}/profile/notifications",
                parse_mode='HTML'
            )
    else:
        # Проверяем привязан ли уже пользователь
        user_id = get_user_by_telegram_chat_id(chat_id)
        
        if user_id:
            # Уже привязан
            with get_session() as session:
                user = session.get(UserORM, user_id)
                user_name = user.full_name or user.email if user else "пользователь"
            
            await update.message.reply_text(
                f"👋 <b>Привет, {user_name}!</b>\n\n"
                f"Ваш Telegram уже подключен к системе МикроКредит.\n\n"
                f"📱 Доступные команды:\n"
                f"/myaccount - информация о вашем аккаунте\n"
                f"/help - справка\n\n"
                f"🌐 Веб-интерфейс: {WEB_URL}",
                parse_mode='HTML'
            )
        else:
            # Не привязан
            await update.message.reply_text(
                f"👋 <b>Добро пожаловать в МикроКредит бот!</b>\n\n"
                f"Этот бот отправляет уведомления о займах и задачах.\n\n"
                f"🔗 <b>Для подключения:</b>\n"
                f"1. Зарегистрируйтесь на сайте: {WEB_URL}\n"
                f"2. Зайдите в Профиль → Уведомления\n"
                f"3. Нажмите 'Подключить Telegram'\n"
                f"4. Используйте полученный код с командой:\n"
                f"   <code>/start [ваш_код]</code>\n\n"
                f"📱 После подключения вы будете получать:\n"
                f"• Уведомления о займах\n"
                f"• Напоминания о задачах\n"
                f"• Важные события",
                parse_mode='HTML'
            )


async def myaccount_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /myaccount"""
    chat_id = str(update.effective_chat.id)
    
    # Получаем user_id по chat_id
    user_id = get_user_by_telegram_chat_id(chat_id)
    
    if not user_id:
        await update.message.reply_text(
            "❌ <b>Telegram не подключен</b>\n\n"
            f"Для подключения используйте команду /start с кодом из личного кабинета:\n"
            f"{WEB_URL}/profile/notifications",
            parse_mode='HTML'
        )
        return
    
    # Получаем информацию о пользователе
    with get_session() as session:
        user = session.get(UserORM, user_id)
        
        if not user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        # Статистика
        from app.models_sa import LoanORM, TaskORM
        from sqlalchemy import func
        
        loans_count = session.query(func.count(LoanORM.id)).filter_by(user_id=user_id).scalar() or 0
        tasks_count = session.query(func.count(TaskORM.id)).filter_by(user_id=user_id).scalar() or 0
        tasks_pending = session.query(func.count(TaskORM.id)).filter_by(user_id=user_id, status=0).scalar() or 0
        
        # Формируем ответ
        message = f"👤 <b>Ваш аккаунт</b>\n\n"
        message += f"📧 Email: {user.email}\n"
        message += f"👤 Имя: {user.full_name or '—'}\n"
        message += f"💬 Telegram: @{user.telegram_username or 'ID: ' + chat_id}\n"
        message += f"📅 Регистрация: {user.created_at[:10]}\n\n"
        message += f"📊 <b>Статистика:</b>\n"
        message += f"💳 Займов: {loans_count}\n"
        message += f"✅ Задач: {tasks_count} (активных: {tasks_pending})\n\n"
        message += f"🌐 Личный кабинет: {WEB_URL}/profile\n\n"
        message += f"📱 <b>Настройки уведомлений:</b>\n"
        message += f"Email: {'✅' if user.email_notifications else '❌'}\n"
        message += f"Telegram: {'✅' if user.telegram_notifications else '❌'}"
        
        await update.message.reply_text(message, parse_mode='HTML')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    message = (
        "📱 <b>Доступные команды:</b>\n\n"
        "/start [код] - подключить Telegram к аккаунту\n"
        "/myaccount - информация о вашем аккаунте\n"
        "/help - эта справка\n\n"
        f"🌐 Веб-интерфейс: {WEB_URL}\n\n"
        "💡 <b>Что умеет бот:</b>\n"
        "• Отправляет уведомления о займах\n"
        "• Напоминает о задачах\n"
        "• Интерактивные кнопки (Выполнил/Отложить)"
    )
    
    await update.message.reply_text(message, parse_mode='HTML')


def main():
    """Основная функция - запуск бота"""
    print(f"Запуск Telegram бота...")
    print(f"Токен: {TELEGRAM_TOKEN[:20]}...")
    print(f"Рабочие часы: {BOT_WORK_HOURS_START}:00 - {BOT_WORK_HOURS_END}:00 MSK")
    
    # Создаём приложение
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Добавляем обработчики команд
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("myaccount", myaccount_command))
    app.add_handler(CommandHandler("help", help_command))
    
    # Добавляем обработчик callback кнопок
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # Запускаем polling
    print("✓ Бот запущен и ожидает команды и callback...")
    print("✓ Команды: /start, /myaccount, /help")
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

