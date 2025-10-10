-- Migration 008: Добавление гибких расписаний и правил напоминаний для задач
-- Дата: 2025-10-10
-- Описание: Система гибких напоминаний с расписанием по дням недели и правилами

-- ============================================================================
-- 1. Расширение таблицы tasks
-- ============================================================================

-- Тип задачи
ALTER TABLE tasks ADD COLUMN task_type VARCHAR(50) DEFAULT 'simple';
-- Возможные значения: 'simple', 'event', 'recurring_event'

-- Для событий с длительностью
ALTER TABLE tasks ADD COLUMN has_duration BOOLEAN DEFAULT 0;
ALTER TABLE tasks ADD COLUMN duration_minutes INTEGER;

-- Приостановка задачи
ALTER TABLE tasks ADD COLUMN is_paused BOOLEAN DEFAULT 0;
ALTER TABLE tasks ADD COLUMN paused_until TEXT;  -- YYYY-MM-DD

-- ============================================================================
-- 2. Таблица расписаний (когда происходит задача)
-- ============================================================================

CREATE TABLE IF NOT EXISTS task_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    
    -- День недели (1=Понедельник, 2=Вторник, ..., 7=Воскресенье)
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
    
    -- Время начала (HH:MM формат)
    start_time TEXT NOT NULL,
    
    -- Время окончания (HH:MM формат) - для событий с длительностью
    end_time TEXT,
    
    -- Активно ли это расписание
    is_active BOOLEAN DEFAULT 1 NOT NULL,
    
    -- Метаданные
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    
    -- Тип правила напоминания
    -- 'before_start' - За X минут до начала (одноразово)
    -- 'before_end' - За X минут до конца (одноразово)
    -- 'periodic_before' - Периодически до начала события
    -- 'periodic_during' - Периодически во время события
    -- 'after_end' - После окончания события
    rule_type TEXT NOT NULL CHECK (rule_type IN (
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
    start_from TEXT,
    
    -- Для 'periodic_before': до какого момента напоминать
    -- Обычно: "30" означает "до 30 минут до начала"
    stop_at TEXT,
    
    -- Активно ли правило
    is_active BOOLEAN DEFAULT 1 NOT NULL,
    
    -- Порядок отображения в UI
    order_index INTEGER DEFAULT 0 NOT NULL,
    
    -- Описание правила (для отображения)
    description TEXT,
    
    -- Метаданные
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    
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
UPDATE tasks SET has_duration = 0 WHERE has_duration IS NULL;
UPDATE tasks SET is_paused = 0 WHERE is_paused IS NULL;

-- ============================================================================
-- Комментарии и примеры использования
-- ============================================================================

-- Пример 1: Футбол по понедельникам и средам с 20:00 до 21:00
-- 
-- task_schedules:
--   task_id=1, day_of_week=1, start_time="20:00", end_time="21:00"
--   task_id=1, day_of_week=3, start_time="20:00", end_time="21:00"
--
-- reminder_rules:
--   task_id=1, rule_type='periodic_before', interval_minutes=30, 
--   start_from="16:00", stop_at="30"
--   
--   task_id=1, rule_type='before_end', offset_minutes=20

-- Пример 2: Напомнить оплатить счёт за день и за час до дедлайна
--
-- tasks: due_date="2025-10-15 18:00"
--
-- reminder_rules:
--   task_id=2, rule_type='before_start', offset_minutes=1440  -- 24 часа
--   task_id=2, rule_type='before_start', offset_minutes=60    -- 1 час

