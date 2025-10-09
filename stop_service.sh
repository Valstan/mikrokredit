#!/bin/bash
# Скрипт для остановки MikroKredit сервиса

echo "Останавливаем MikroKredit..."

# Останавливаем процессы
pkill -f "gunicorn.*mikrokredit" && echo "✓ Процессы остановлены" || echo "Процессы уже остановлены"

# Проверяем что всё остановлено
sleep 2
if pgrep -f "gunicorn.*mikrokredit" > /dev/null; then
    echo "Принудительная остановка..."
    pkill -9 -f "gunicorn.*mikrokredit"
    sleep 1
fi

if ! pgrep -f "gunicorn.*mikrokredit" > /dev/null; then
    echo "✓ MikroKredit полностью остановлен"
else
    echo "✗ Не удалось остановить все процессы"
    ps aux | grep gunicorn | grep mikrokredit | grep -v grep
    exit 1
fi

