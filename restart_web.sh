#!/bin/bash
# Скрипт перезапуска веб-сервера

cd /home/valstan/mikrokredit

echo "Останавливаем gunicorn..."
pkill -f gunicorn
sleep 2

echo "Запускаем gunicorn..."
./.venv/bin/gunicorn --config gunicorn.conf.py "web:create_app()" --daemon

sleep 2

echo "Проверяем статус..."
curl -s http://localhost/healthz

echo ""
echo "✅ Готово!"

