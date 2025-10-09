#!/bin/bash
# Скрипт для запуска MikroKredit сервиса

set -e

# Переходим в директорию проекта
cd /home/valstan/mikrokredit

# Останавливаем старые процессы
echo "Останавливаем старые процессы..."
pkill -f "gunicorn.*mikrokredit" || true
sleep 2

# Проверяем что PostgreSQL запущен
if ! systemctl is-active --quiet postgresql; then
    echo "Ошибка: PostgreSQL не запущен!"
    exit 1
fi

# Устанавливаем переменную окружения для базы данных
export MIKROKREDIT_DATABASE_URL="postgresql://mikrokredit_user:mikrokredit_pass_2024@localhost:5432/mikrokredit"

# Запускаем Gunicorn
echo "Запускаем Gunicorn..."
nohup .venv/bin/gunicorn --config /home/valstan/mikrokredit/gunicorn.conf.py "web:create_app()" > /dev/null 2>&1 &

# Ждём запуска
sleep 3

# Проверяем что запустилось
if pgrep -f "gunicorn.*mikrokredit" > /dev/null; then
    echo "✓ MikroKredit успешно запущен!"
    echo "  - Порт: 8002"
    echo "  - PID: $(pgrep -f 'gunicorn.*mikrokredit' | head -1)"
    echo "  - Воркеры: $(pgrep -f 'gunicorn.*mikrokredit' | wc -l)"
    
    # Проверяем доступность
    if curl -s http://127.0.0.1:8002/healthz > /dev/null; then
        echo "  - Health check: OK"
    else
        echo "  - Health check: FAILED"
        exit 1
    fi
else
    echo "✗ Ошибка запуска MikroKredit"
    tail -20 /home/valstan/mikrokredit/logs/error.log
    exit 1
fi

