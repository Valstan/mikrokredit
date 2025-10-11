-- Миграция: Создание таблицы шаблонов напоминаний
-- Дата: 10 октября 2025
-- PostgreSQL

CREATE TABLE IF NOT EXISTS reminder_rule_templates (
    id SERIAL PRIMARY KEY,
    
    -- Основная информация
    name VARCHAR(100) NOT NULL,
    description TEXT,
    category VARCHAR(50),  -- 'simple', 'sport', 'work', 'health', 'meeting', 'personal'
    icon VARCHAR(20),      -- emoji для отображения
    
    -- JSON с массивом правил
    -- Пример: [{"rule_type": "before_start", "offset_minutes": 60}, ...]
    rules_json TEXT NOT NULL,
    
    -- Для каких типов задач подходит
    suitable_for_task_types VARCHAR(100)[], -- ['simple', 'event', 'recurring_event']
    
    -- Метаданные
    is_system BOOLEAN DEFAULT FALSE,  -- Системный (неудаляемый)
    is_active BOOLEAN DEFAULT TRUE,
    usage_count INTEGER DEFAULT 0,
    
    -- Пользователь создатель (NULL для системных)
    created_by INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы
CREATE INDEX idx_reminder_templates_category ON reminder_rule_templates(category);
CREATE INDEX idx_reminder_templates_active ON reminder_rule_templates(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_reminder_templates_system ON reminder_rule_templates(is_system);

-- Комментарии
COMMENT ON TABLE reminder_rule_templates IS 'Шаблоны правил напоминаний для быстрого применения';
COMMENT ON COLUMN reminder_rule_templates.rules_json IS 'JSON массив с правилами напоминаний';
COMMENT ON COLUMN reminder_rule_templates.suitable_for_task_types IS 'Массив типов задач для которых подходит шаблон';
COMMENT ON COLUMN reminder_rule_templates.is_system IS 'Системный шаблон (создан по умолчанию, нельзя удалить)';

