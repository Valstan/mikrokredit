#!/bin/bash
# Запуск Telegram бота для обработки callback кнопок

# Определяем директорию проекта (родительская от scripts/)
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

# Останавливаем старый процесс если есть
pkill -f "telegram_bot_server.py" || true
sleep 1

# Запускаем бота в фоне
echo "Запуск Telegram бота..."
nohup .venv/bin/python3 scripts/telegram_bot_server.py > logs/telegram_bot.log 2>&1 &

PID=$!
sleep 2

# Проверяем что запустилось
if pgrep -f "telegram_bot_server.py" > /dev/null; then
    echo "✓ Telegram бот запущен!"
    echo "  - PID: $(pgrep -f 'telegram_bot_server.py')"
    echo "  - Лог: logs/telegram_bot.log"
else
    echo "✗ Ошибка запуска бота"
    tail -20 logs/telegram_bot.log
    exit 1
fi
