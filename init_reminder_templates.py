#!/usr/bin/env python3
"""
Инициализация системных шаблонов напоминаний
"""
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db_sa import get_session
from app.models_sa import ReminderTemplateORM

SYSTEM_TEMPLATES = [
    {
        "name": "За 1 день до срока",
        "description": "Одно напоминание за 1 день (24 часа) до дедлайна",
        "rules": json.dumps({"type": "before", "intervals": [1440]})  # 1440 минут = 24 часа
    },
    {
        "name": "За день и в день",
        "description": "За 1 день до срока и утром в день дедлайна",
        "rules": json.dumps({"type": "before", "intervals": [1440, 0]})
    },
    {
        "name": "Интенсивные (3 раза)",
        "description": "За 1 день, за 1 час и в момент дедлайна",
        "rules": json.dumps({"type": "before", "intervals": [1440, 60, 0]})
    },
    {
        "name": "Очень интенсивные",
        "description": "За 2 дня, за 1 день, за 3 часа, за 1 час, в момент",
        "rules": json.dumps({"type": "before", "intervals": [2880, 1440, 180, 60, 0]})
    },
    {
        "name": "Только в день дедлайна",
        "description": "Одно напоминание утром в день дедлайна",
        "rules": json.dumps({"type": "before", "intervals": [0]})
    },
]

def init_templates():
    """Инициализация шаблонов"""
    with get_session() as session:
        # Проверяем существующие шаблоны
        from sqlalchemy import select
        existing = session.execute(select(ReminderTemplateORM)).scalars().all()
        
        if existing:
            print(f"Найдено существующих шаблонов: {len(existing)}")
            response = input("Перезаписать? (y/N): ")
            if response.lower() != 'y':
                print("Отменено")
                return
            
            # Удаляем старые системные шаблоны
            for template in existing:
                if template.is_system:
                    session.delete(template)
        
        # Создаём новые
        now = datetime.now().isoformat()
        for template_data in SYSTEM_TEMPLATES:
            template = ReminderTemplateORM(
                name=template_data["name"],
                description=template_data["description"],
                rules=template_data["rules"],
                is_system=1,
                created_at=now
            )
            session.add(template)
            print(f"✓ Создан шаблон: {template_data['name']}")
        
        session.commit()
        print(f"\n✅ Инициализировано {len(SYSTEM_TEMPLATES)} шаблонов")

if __name__ == "__main__":
    init_templates()

