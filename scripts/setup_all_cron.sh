#!/bin/bash
# Скрипт для настройки всех cron задач для MikroKredit

echo "🔧 Настройка всех cron задач для MikroKredit"
echo ""

# Пути
PROJECT_DIR="/home/valstan/mikrokredit"
REMINDERS_SCRIPT="$PROJECT_DIR/scripts/send_task_reminders.py"
REGENERATE_SCRIPT="$PROJECT_DIR/scripts/regenerate_reminders.py"
LOG_DIR="$PROJECT_DIR/logs"

# Проверяем скрипты
if [ ! -f "$REMINDERS_SCRIPT" ]; then
    echo "❌ Ошибка: $REMINDERS_SCRIPT не найден"
    exit 1
fi

if [ ! -f "$REGENERATE_SCRIPT" ]; then
    echo "❌ Ошибка: $REGENERATE_SCRIPT не найден"
    exit 1
fi

# Создаем директорию для логов если нет
mkdir -p "$LOG_DIR"

# Создаем временный файл с cron задачами
TEMP_CRON=$(mktemp)

# Получаем текущие cron задачи
crontab -l > "$TEMP_CRON" 2>/dev/null || true

# Удаляем старые задачи MikroKredit (если есть)
sed -i '/mikrokredit/d' "$TEMP_CRON"
sed -i '/send_task_reminders.py/d' "$TEMP_CRON"
sed -i '/regenerate_reminders.py/d' "$TEMP_CRON"

# Добавляем новые задачи
echo "" >> "$TEMP_CRON"
echo "# ===================== MikroKredit =====================" >> "$TEMP_CRON"
echo "" >> "$TEMP_CRON"

# 1. Отправка напоминаний - каждую минуту
echo "# Отправка напоминаний о задачах - каждую минуту" >> "$TEMP_CRON"
echo "* * * * * cd $PROJECT_DIR && /usr/bin/python3 $REMINDERS_SCRIPT >> $LOG_DIR/reminders_send.log 2>&1" >> "$TEMP_CRON"
echo "" >> "$TEMP_CRON"

# 2. Регенерация напоминаний - каждый день в 00:00
echo "# Регенерация напоминаний для всех задач - каждый день в 00:00" >> "$TEMP_CRON"
echo "0 0 * * * cd $PROJECT_DIR && /usr/bin/python3 $REGENERATE_SCRIPT >> $LOG_DIR/reminders_regenerate.log 2>&1" >> "$TEMP_CRON"
echo "" >> "$TEMP_CRON"

# Устанавливаем новый crontab
crontab "$TEMP_CRON"

echo "✅ Cron задачи настроены!"
echo ""
echo "📋 Установленные задачи:"
echo "  1️⃣  Отправка напоминаний: каждую минуту"
echo "  2️⃣  Регенерация: каждый день в 00:00"
echo ""
echo "📝 Логи:"
echo "  - Отправка: $LOG_DIR/reminders_send.log"
echo "  - Регенерация: $LOG_DIR/reminders_regenerate.log"
echo ""
echo "Текущий crontab:"
crontab -l | grep -A 10 "MikroKredit"
echo ""
echo "🧪 Тестирование:"
echo "  cd $PROJECT_DIR && python3 scripts/send_task_reminders.py"
echo "  cd $PROJECT_DIR && python3 scripts/regenerate_reminders.py"

# Удаляем временный файл
rm "$TEMP_CRON"

