#!/usr/bin/env python3
"""
Скрипт для отправки напоминаний о задачах через Telegram
Запускать каждую минуту через cron
"""
import sys
import os

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from sqlalchemy import select

from app.db_sa import get_session
from app.models_sa import TaskORM, TaskReminderORM
from app.telegram_notifier import send_task_reminder_notification


def send_pending_reminders():
    """
    Проверяет task_reminders и отправляет те, время которых наступило
    """
    now = datetime.now()
    # Берем напоминания за последние 2 минуты (на случай пропусков)
    time_window_start = (now - timedelta(minutes=2)).isoformat()
    time_window_end = now.isoformat()
    
    with get_session() as session:
        # Находим неотправленные напоминания, время которых наступило
        reminders = session.execute(
            select(TaskReminderORM).where(
                TaskReminderORM.sent == False,
                TaskReminderORM.reminder_time >= time_window_start,
                TaskReminderORM.reminder_time <= time_window_end
            ).order_by(TaskReminderORM.reminder_time.asc())
        ).scalars().all()
        
        if not reminders:
            print(f"ℹ️  Нет напоминаний для отправки - {now.strftime('%H:%M:%S')}")
            return 0
        
        print(f"📬 Найдено {len(reminders)} напоминаний для отправки")
        
        sent_count = 0
        failed_count = 0
        
        for reminder in reminders:
            # Получаем задачу
            task = session.get(TaskORM, reminder.task_id)
            if not task:
                print(f"⚠️  Задача {reminder.task_id} не найдена, пропускаем")
                # Помечаем как отправленное чтобы не пытаться снова
                reminder.sent = 1
                reminder.sent_at = now.isoformat()
                continue
            
            # Проверяем что задача не выполнена
            if task.status == 1:
                print(f"✅ Задача '{task.title}' уже выполнена, пропускаем")
                reminder.sent = 1
                reminder.sent_at = now.isoformat()
                continue
            
            # Проверяем приостановку
            if task.is_paused and task.paused_until:
                from datetime import date
                paused_until = date.fromisoformat(task.paused_until)
                if date.today() < paused_until:
                    print(f"⏸️  Задача '{task.title}' приостановлена до {task.paused_until}")
                    reminder.sent = 1
                    reminder.sent_at = now.isoformat()
                    continue
            
            # Отправляем уведомление
            print(f"📤 Отправка: '{task.title}' (ID: {task.id})")
            
            try:
                success = send_task_reminder_notification(
                    task_title=task.title,
                    task_id=task.id,
                    reminder_type="general"
                )
                
                if success:
                    print(f"   ✅ Отправлено")
                    reminder.sent = 1
                    reminder.sent_at = now.isoformat()
                    # Можно сохранить telegram_message_id если нужно
                    sent_count += 1
                else:
                    print(f"   ❌ Ошибка отправки")
                    failed_count += 1
            
            except Exception as e:
                print(f"   ❌ Исключение: {e}")
                failed_count += 1
        
        # Сохраняем изменения
        session.commit()
        
        print(f"\n📊 Итого:")
        print(f"   ✅ Отправлено: {sent_count}")
        print(f"   ❌ Ошибок: {failed_count}")
        
        return sent_count


def main():
    try:
        sent_count = send_pending_reminders()
        return 0
    
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

