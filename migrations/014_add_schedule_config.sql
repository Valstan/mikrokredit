-- Добавление поля schedule_config для календарного планировщика
-- Дата: 11 октября 2025

BEGIN;

ALTER TABLE tasks ADD COLUMN IF NOT EXISTS schedule_config TEXT;

COMMENT ON COLUMN tasks.schedule_config IS 'JSON конфигурация календарного расписания: {mode, months, days, weekdays, times}';

COMMIT;

SELECT 'Поле schedule_config добавлено' as status;
