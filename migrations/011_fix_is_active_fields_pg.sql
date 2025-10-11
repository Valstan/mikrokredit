-- Миграция: Исправление типов полей is_active в таблицах расписаний и правил
-- Дата: 10 октября 2025
-- PostgreSQL

-- Исправляем is_active в task_schedules
ALTER TABLE task_schedules 
ALTER COLUMN is_active TYPE BOOLEAN 
USING CASE WHEN is_active = 1 THEN TRUE ELSE FALSE END;

ALTER TABLE task_schedules 
ALTER COLUMN is_active SET DEFAULT TRUE;

-- Исправляем is_active в reminder_rules
ALTER TABLE reminder_rules 
ALTER COLUMN is_active TYPE BOOLEAN 
USING CASE WHEN is_active = 1 THEN TRUE ELSE FALSE END;

ALTER TABLE reminder_rules 
ALTER COLUMN is_active SET DEFAULT TRUE;

-- Исправляем is_system в reminder_templates
ALTER TABLE reminder_templates 
ALTER COLUMN is_system TYPE BOOLEAN 
USING CASE WHEN is_system = 1 THEN TRUE ELSE FALSE END;

ALTER TABLE reminder_templates 
ALTER COLUMN is_system SET DEFAULT FALSE;

-- Комментарии
COMMENT ON COLUMN task_schedules.is_active IS 'Активно ли расписание (TRUE/FALSE)';
COMMENT ON COLUMN reminder_rules.is_active IS 'Активно ли правило (TRUE/FALSE)';
COMMENT ON COLUMN reminder_templates.is_system IS 'Системный ли шаблон (TRUE/FALSE)';

