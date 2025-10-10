-- Migration 008: Добавление гибких расписаний и правил напоминаний для задач (PostgreSQL)
-- Дата: 2025-10-10
-- Описание: Система гибких напоминаний с расписанием по дням недели и правилами

-- ============================================================================
-- 1. Расширение таблицы tasks
-- ============================================================================

-- Тип задачи
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS task_type VARCHAR(50) DEFAULT 'simple';

-- Для событий с длительностью
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS has_duration BOOLEAN DEFAULT FALSE;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS duration_minutes INTEGER;

-- Приостановка задачи
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS is_paused BOOLEAN DEFAULT FALSE;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS paused_until VARCHAR;  -- YYYY-MM-DD

-- ============================================================================
-- 2. Таблица расписаний (когда происходит задача)
-- ============================================================================

CREATE TABLE IF NOT EXISTS task_schedules (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL,
    
    -- День недели (1=Понедельник, 2=Вторник, ..., 7=Воскресенье)
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
    
    -- Время начала (HH:MM формат)
    start_time VARCHAR NOT NULL,
    
    -- Время окончания (HH:MM формат) - для событий с длительностью
    end_time VARCHAR,
    
    -- Активно ли это расписание
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    
    -- Метаданные
    created_at VARCHAR NOT NULL DEFAULT NOW()::TEXT,
    updated_at VARCHAR NOT NULL DEFAULT NOW()::TEXT,
    
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_task_schedules_task_id ON task_schedules(task_id);
CREATE INDEX IF NOT EXISTS idx_task_schedules_day ON task_schedules(day_of_week);
CREATE INDEX IF NOT EXISTS idx_task_schedules_active ON task_schedules(is_active);

-- ============================================================================
-- 3. Таблица правил напоминаний
-- ============================================================================

CREATE TABLE IF NOT EXISTS reminder_rules (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL,
    
    -- Тип правила напоминания
    rule_type VARCHAR(50) NOT NULL CHECK (rule_type IN (
        'before_start', 
        'before_end', 
        'periodic_before', 
        'periodic_during', 
        'after_end'
    )),
    
    -- Параметры для типов 'before_start' и 'before_end'
    -- Количество минут до начала/конца
    offset_minutes INTEGER,
    
    -- Параметры для периодических напоминаний
    -- Интервал в минутах между напоминаниями
    interval_minutes INTEGER,
    
    -- Для 'periodic_before': с какого времени начинать
    -- Может быть: "16:00" (фиксированное время) или "120" (минуты до начала)
    start_from VARCHAR,
    
    -- Для 'periodic_before': до какого момента напоминать
    -- Обычно: "30" означает "до 30 минут до начала"
    stop_at VARCHAR,
    
    -- Активно ли правило
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    
    -- Порядок отображения в UI
    order_index INTEGER DEFAULT 0 NOT NULL,
    
    -- Описание правила (для отображения)
    description TEXT,
    
    -- Метаданные
    created_at VARCHAR NOT NULL DEFAULT NOW()::TEXT,
    updated_at VARCHAR NOT NULL DEFAULT NOW()::TEXT,
    
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_reminder_rules_task_id ON reminder_rules(task_id);
CREATE INDEX IF NOT EXISTS idx_reminder_rules_type ON reminder_rules(rule_type);
CREATE INDEX IF NOT EXISTS idx_reminder_rules_active ON reminder_rules(is_active);

-- ============================================================================
-- 4. Обновление существующих данных
-- ============================================================================

-- Все существующие задачи по умолчанию - простые
UPDATE tasks SET task_type = 'simple' WHERE task_type IS NULL;
UPDATE tasks SET has_duration = FALSE WHERE has_duration IS NULL;
UPDATE tasks SET is_paused = FALSE WHERE is_paused IS NULL;

-- Создаем sequence для новых таблиц
CREATE SEQUENCE IF NOT EXISTS task_schedules_id_seq;
CREATE SEQUENCE IF NOT EXISTS reminder_rules_id_seq;

-- ============================================================================
-- Комментарии
-- ============================================================================

COMMENT ON TABLE task_schedules IS 'Расписание для задач - когда они происходят';
COMMENT ON TABLE reminder_rules IS 'Правила генерации напоминаний для задач';

COMMENT ON COLUMN task_schedules.day_of_week IS '1=Пн, 2=Вт, 3=Ср, 4=Чт, 5=Пт, 6=Сб, 7=Вс';
COMMENT ON COLUMN reminder_rules.rule_type IS 'before_start, before_end, periodic_before, periodic_during, after_end';

