# 🤖 Перезапуск Telegram бота

## Быстрый перезапуск

```bash
cd /home/valstan/mikrokredit

# Останавливаем старый бот
pkill -9 -f telegram_bot_server.py

# Запускаем новый бот
nohup ./.venv/bin/python scripts/telegram_bot_server.py > logs/telegram_bot.log 2>&1 &

# Проверяем что запустился
sleep 3
ps aux | grep telegram_bot_server | grep -v grep
```

## Проверка логов

```bash
# Последние 20 строк
tail -20 logs/telegram_bot.log

# Отслеживание в реальном времени
tail -f logs/telegram_bot.log
```

## Проверка работы

После перезапуска в логах должно появиться:
```
✓ Бот запущен и ожидает команды и callback...
✓ Команды: /start, /myaccount, /help
```

## Команды бота

После перезапуска бот понимает:
- `/start` - приветствие или `/start [код]` - привязка аккаунта
- `/myaccount` - информация об аккаунте
- `/help` - справка
- Callback кнопки в уведомлениях (Выполнил/Отложить)

## Тестирование

1. Откройте Telegram → @valstan_bot
2. Отправьте `/start`
3. Должен ответить приветствием
4. Попробуйте `/help`

Если бот не отвечает - проверьте логи!

