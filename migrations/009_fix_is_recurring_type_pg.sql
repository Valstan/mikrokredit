-- Миграция: Исправление типа поля is_recurring с INTEGER на BOOLEAN
-- Дата: 10 октября 2025
-- PostgreSQL

-- Изменяем тип is_recurring на BOOLEAN
ALTER TABLE tasks 
ALTER COLUMN is_recurring TYPE BOOLEAN 
USING CASE WHEN is_recurring = 1 THEN TRUE ELSE FALSE END;

-- Устанавливаем значение по умолчанию
ALTER TABLE tasks 
ALTER COLUMN is_recurring SET DEFAULT FALSE;

-- Комментарий
COMMENT ON COLUMN tasks.is_recurring IS 'Является ли задача повторяющейся (TRUE/FALSE)';

