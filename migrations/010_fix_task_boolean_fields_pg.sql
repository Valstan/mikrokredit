-- Миграция: Исправление типов boolean полей для модуля задач
-- Дата: 10 октября 2025
-- PostgreSQL

-- Исправляем поле completed в subtasks
ALTER TABLE subtasks 
ALTER COLUMN completed TYPE BOOLEAN 
USING CASE WHEN completed = 1 THEN TRUE ELSE FALSE END;

ALTER TABLE subtasks 
ALTER COLUMN completed SET DEFAULT FALSE;

-- Исправляем поля sent и acknowledged в task_reminders
ALTER TABLE task_reminders 
ALTER COLUMN sent TYPE BOOLEAN 
USING CASE WHEN sent = 1 THEN TRUE ELSE FALSE END;

ALTER TABLE task_reminders 
ALTER COLUMN sent SET DEFAULT FALSE;

ALTER TABLE task_reminders 
ALTER COLUMN acknowledged TYPE BOOLEAN 
USING CASE WHEN acknowledged = 1 THEN TRUE ELSE FALSE END;

ALTER TABLE task_reminders 
ALTER COLUMN acknowledged SET DEFAULT FALSE;

-- Комментарии
COMMENT ON COLUMN subtasks.completed IS 'Выполнена ли подзадача (TRUE/FALSE)';
COMMENT ON COLUMN task_reminders.sent IS 'Отправлено ли напоминание (TRUE/FALSE)';
COMMENT ON COLUMN task_reminders.acknowledged IS 'Подтверждено ли напоминание пользователем (TRUE/FALSE)';

