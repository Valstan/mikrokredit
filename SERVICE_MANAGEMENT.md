# 🔧 Управление сервисом MikroKredit

MikroKredit настроен как systemd service для удобного и надёжного управления.

## 📋 Основные команды

### Запуск
```bash
sudo systemctl start mikrokredit
```

### Остановка
```bash
sudo systemctl stop mikrokredit
```

### Перезапуск
```bash
sudo systemctl restart mikrokredit
```

### Проверка статуса
```bash
sudo systemctl status mikrokredit
```

### Просмотр логов
```bash
# Последние логи
sudo journalctl -u mikrokredit -n 50

# Логи в реальном времени
sudo journalctl -u mikrokredit -f

# Логи приложения
tail -f logs/access.log
tail -f logs/error.log
```

### Автозапуск

Автозапуск уже **включён**. Сервис запустится автоматически при загрузке системы.

```bash
# Отключить автозапуск
sudo systemctl disable mikrokredit

# Включить автозапуск
sudo systemctl enable mikrokredit
```

## ✨ Преимущества systemd service

- ✅ **Автозапуск** при загрузке системы
- ✅ **Автоматический перезапуск** при падении приложения
- ✅ **Graceful shutdown** - корректное завершение запросов
- ✅ **Централизованное управление** через `systemctl`
- ✅ **Логирование** через `journalctl`
- ✅ **Безопасность** (PrivateTmp, NoNewPrivileges)
- ✅ **Простота** - одна команда вместо скриптов

## 🔄 Миграция со скриптов

Старые скрипты (`start_service.sh`, `stop_service.sh`) **удалены**.  
Теперь используйте только `systemctl`.

## 📊 Health Check

```bash
curl http://127.0.0.1:8002/healthz
# Ответ: {"status":"ok"}
```

## 🛠️ Конфигурация

- **Service file**: `/etc/systemd/system/mikrokredit.service`
- **Gunicorn config**: `/home/valstan/mikrokredit/gunicorn.conf.py`
- **Логи**: `/home/valstan/mikrokredit/logs/`
- **PID file**: `/home/valstan/mikrokredit/mikrokredit.pid`
- **Порт**: `8002`
- **Воркеры**: автоматически (CPU * 2 + 1)

## 🚨 Устранение неполадок

```bash
# Если сервис не запускается
sudo systemctl status mikrokredit
sudo journalctl -u mikrokredit -n 100

# Проверка PostgreSQL
sudo systemctl status postgresql

# Проверка Redis
sudo systemctl status redis-server

# Проверка порта
ss -tlnp | grep 8002

# Проверка процессов
ps aux | grep gunicorn
```

## 📝 Примеры

```bash
# Быстрый перезапуск после изменений в коде
sudo systemctl restart mikrokredit

# Проверка работы после перезапуска
curl http://127.0.0.1:8002/healthz

# Мониторинг логов в реальном времени
sudo journalctl -u mikrokredit -f

# Просмотр ошибок
tail -100 logs/error.log
```

---

**Дата миграции**: 10 октября 2025  
**Статус**: ✅ Работает, протестировано

