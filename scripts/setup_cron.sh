#!/bin/bash
# Скрипт для настройки cron задачи регенерации напоминаний

echo "🔧 Настройка cron задачи для регенерации напоминаний"

# Путь к скрипту
SCRIPT_PATH="/home/valstan/mikrokredit/scripts/regenerate_reminders.py"

# Проверяем что скрипт существует
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Ошибка: скрипт не найден: $SCRIPT_PATH"
    exit 1
fi

# Создаем временный файл с cron задачей
TEMP_CRON=$(mktemp)

# Получаем текущие cron задачи
crontab -l > "$TEMP_CRON" 2>/dev/null || true

# Проверяем есть ли уже такая задача
if grep -q "regenerate_reminders.py" "$TEMP_CRON"; then
    echo "⚠️  Задача уже существует в crontab"
    echo "Текущая задача:"
    grep "regenerate_reminders.py" "$TEMP_CRON"
else
    # Добавляем новую задачу (каждый день в 00:00)
    echo "" >> "$TEMP_CRON"
    echo "# Регенерация напоминаний для задач - каждый день в 00:00" >> "$TEMP_CRON"
    echo "0 0 * * * cd /home/valstan/mikrokredit && /usr/bin/python3 $SCRIPT_PATH >> /home/valstan/mikrokredit/logs/reminders.log 2>&1" >> "$TEMP_CRON"
    
    # Устанавливаем новый crontab
    crontab "$TEMP_CRON"
    
    echo "✅ Cron задача добавлена!"
    echo "Расписание: каждый день в 00:00"
fi

# Показываем текущий crontab
echo ""
echo "Текущий crontab:"
crontab -l

# Удаляем временный файл
rm "$TEMP_CRON"

echo ""
echo "📝 Логи будут сохраняться в: /home/valstan/mikrokredit/logs/reminders.log"
echo "🧪 Для тестирования запустите вручную:"
echo "    cd /home/valstan/mikrokredit && python3 scripts/regenerate_reminders.py"

