-- Добавление типа правила 'at_start' в constraint
-- Дата: 11 октября 2025

BEGIN;

-- Удаляем старый constraint
ALTER TABLE reminder_rules DROP CONSTRAINT IF EXISTS reminder_rules_rule_type_check;

-- Добавляем новый constraint с at_start
ALTER TABLE reminder_rules ADD CONSTRAINT reminder_rules_rule_type_check 
CHECK (rule_type IN (
    'before_start',
    'at_start',
    'before_end', 
    'periodic_before',
    'periodic_during',
    'after_end'
));

-- Обновляем комментарий
COMMENT ON COLUMN reminder_rules.rule_type IS 'before_start, at_start, before_end, periodic_before, periodic_during, after_end';

COMMIT;

-- Проверка
SELECT 'Constraint обновлён успешно' as status;
