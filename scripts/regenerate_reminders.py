#!/usr/bin/env python3
"""
Скрипт для регенерации напоминаний для всех активных задач
Запускать через cron раз в день, например в 00:00
"""
import sys
import os

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.reminder_generator import ReminderGenerator
from datetime import datetime


def main():
    print(f"🔄 Запуск регенерации напоминаний - {datetime.now().isoformat()}")
    
    try:
        result = ReminderGenerator.regenerate_all_tasks_reminders(days_ahead=14)
        
        print(f"✅ Обработано задач: {result['tasks_processed']}")
        print(f"✅ Создано напоминаний: {result['reminders_created']}")
        print(f"✅ Завершено - {datetime.now().isoformat()}")
        
        return 0
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

