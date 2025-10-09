#!/bin/bash
# Запуск Telegram бота для обработки callback кнопок

cd /home/valstan/mikrokredit

# Останавливаем старый процесс если есть
pkill -f "telegram_bot_server.py" || true
sleep 1

# Запускаем бота в фоне
echo "Запуск Telegram бота..."
nohup .venv/bin/python3 telegram_bot_server.py > logs/telegram_bot.log 2>&1 &

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

