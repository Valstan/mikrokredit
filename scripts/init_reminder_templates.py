#!/usr/bin/env python3
"""
Скрипт для инициализации системных шаблонов напоминаний
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
import json
from app.db_sa import get_session
from app.models_sa import ReminderRuleTemplateORM
from sqlalchemy import select


# Библиотека системных шаблонов
SYSTEM_TEMPLATES = [
    {
        "name": "Простая задача - Стандарт",
        "description": "За день и за час до дедлайна",
        "category": "simple",
        "icon": "📌",
        "suitable_for": ["simple"],
        "rules": [
            {"rule_type": "before_start", "offset_minutes": 1440},  # За 1 день
            {"rule_type": "before_start", "offset_minutes": 60},    # За 1 час
        ]
    },
    {
        "name": "Простая задача - Активная",
        "description": "Частые напоминания перед дедлайном",
        "category": "simple",
        "icon": "📌",
        "suitable_for": ["simple"],
        "rules": [
            {"rule_type": "before_start", "offset_minutes": 4320},  # За 3 дня
            {"rule_type": "before_start", "offset_minutes": 1440},  # За 1 день
            {"rule_type": "before_start", "offset_minutes": 180},   # За 3 часа
            {"rule_type": "before_start", "offset_minutes": 60},    # За 1 час
            {"rule_type": "before_start", "offset_minutes": 15},    # За 15 мин
        ]
    },
    {
        "name": "Событие - Классическое",
        "description": "Напоминание утром и за час до начала",
        "category": "event",
        "icon": "📅",
        "suitable_for": ["event", "recurring_event"],
        "rules": [
            {"rule_type": "before_start", "offset_minutes": 60},    # За 1 час
            {"rule_type": "at_start", "offset_minutes": 0},         # В момент начала
        ]
    },
    {
        "name": "Тренировка (Футбол)",
        "description": "Периодические напоминания с 16:00, как в примере",
        "category": "sport",
        "icon": "⚽",
        "suitable_for": ["recurring_event"],
        "rules": [
            {
                "rule_type": "periodic_before",
                "interval_minutes": 30,
                "start_from": "16:00",
                "stop_at": "30"  # 30 минут до начала
            },
            {
                "rule_type": "before_end",
                "offset_minutes": 20
            }
        ]
    },
    {
        "name": "Важная встреча",
        "description": "Многоуровневые напоминания для подготовки",
        "category": "meeting",
        "icon": "💼",
        "suitable_for": ["event"],
        "rules": [
            {"rule_type": "before_start", "offset_minutes": 4320},  # За 3 дня (подготовиться)
            {"rule_type": "before_start", "offset_minutes": 120},   # За 2 часа
            {"rule_type": "before_start", "offset_minutes": 30},    # За 30 мин (проверить место)
            {"rule_type": "before_start", "offset_minutes": 10},    # За 10 мин (выходить)
            {"rule_type": "at_start", "offset_minutes": 0},         # В момент начала
        ]
    },
    {
        "name": "Онлайн-встреча/Созвон",
        "description": "Подготовка к виртуальной встрече",
        "category": "meeting",
        "icon": "📞",
        "suitable_for": ["event"],
        "rules": [
            {"rule_type": "before_start", "offset_minutes": 15},    # За 15 мин (подготовить документы)
            {"rule_type": "before_start", "offset_minutes": 2},     # За 2 мин (открыть Zoom)
            {"rule_type": "at_start", "offset_minutes": 0},         # В момент начала
        ]
    },
    {
        "name": "Прием лекарств",
        "description": "Ежедневное напоминание в установленное время",
        "category": "health",
        "icon": "💊",
        "suitable_for": ["recurring_event"],
        "rules": [
            {"rule_type": "at_start", "offset_minutes": 0},         # В точное время
            {"rule_type": "after_end", "offset_minutes": 10},       # Повтор через 10 мин
        ]
    },
    {
        "name": "День рождения",
        "description": "Напоминания купить подарок и поздравить",
        "category": "personal",
        "icon": "🎂",
        "suitable_for": ["event"],
        "rules": [
            {"rule_type": "before_start", "offset_minutes": 10080},  # За неделю (купить подарок)
            {"rule_type": "before_start", "offset_minutes": 4320},   # За 3 дня (оформить)
            {"rule_type": "before_start", "offset_minutes": 1440},   # За день (поздравить)
        ]
    },
    {
        "name": "Спортзал/Тренировка",
        "description": "Напоминания для регулярных тренировок",
        "category": "sport",
        "icon": "🏋️",
        "suitable_for": ["recurring_event"],
        "rules": [
            {"rule_type": "before_start", "offset_minutes": 120},   # За 2 часа (подготовиться)
            {"rule_type": "before_start", "offset_minutes": 30},    # За 30 мин (собрать сумку)
            {"rule_type": "before_start", "offset_minutes": 10},    # За 10 мин (выходить)
        ]
    },
    {
        "name": "Оплата счета",
        "description": "Напоминания не забыть оплатить",
        "category": "finance",
        "icon": "💳",
        "suitable_for": ["simple", "event"],
        "rules": [
            {"rule_type": "before_start", "offset_minutes": 4320},  # За 3 дня
            {"rule_type": "before_start", "offset_minutes": 1440},  # За 1 день
            {"rule_type": "before_start", "offset_minutes": 60},    # За 1 час
        ]
    },
]


def init_templates():
    """Инициализация системных шаблонов"""
    
    with get_session() as session:
        # Проверяем есть ли уже системные шаблоны
        existing = session.execute(
            select(ReminderRuleTemplateORM).where(
                ReminderRuleTemplateORM.is_system == True
            )
        ).scalars().all()
        
        if existing:
            print(f"⚠️  Найдено {len(existing)} существующих системных шаблонов")
            response = input("Удалить и пересоздать? (yes/no): ")
            if response.lower() != 'yes':
                print("Отменено")
                return
            
            # Удаляем старые
            for template in existing:
                session.delete(template)
            session.commit()
            print(f"✅ Удалено {len(existing)} старых шаблонов")
        
        # Создаем новые
        now = datetime.now().isoformat()
        created_count = 0
        
        for template_data in SYSTEM_TEMPLATES:
            template = ReminderRuleTemplateORM(
                name=template_data["name"],
                description=template_data["description"],
                category=template_data["category"],
                icon=template_data["icon"],
                rules_json=json.dumps(template_data["rules"], ensure_ascii=False),
                suitable_for_task_types=json.dumps(template_data["suitable_for"]),
                is_system=True,
                is_active=True,
                usage_count=0,
                created_at=now,
                updated_at=now
            )
            session.add(template)
            created_count += 1
            print(f"  {template_data['icon']} {template_data['name']}")
        
        session.commit()
        print(f"\n✅ Создано {created_count} системных шаблонов!")
        
        # Статистика
        print("\n📊 Статистика по категориям:")
        categories = {}
        for t in SYSTEM_TEMPLATES:
            cat = t["category"]
            categories[cat] = categories.get(cat, 0) + 1
        
        for cat, count in sorted(categories.items()):
            print(f"  {cat}: {count}")


if __name__ == '__main__':
    try:
        print("🎨 Инициализация библиотеки системных шаблонов\n")
        init_templates()
        print("\n🎉 Готово!")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
