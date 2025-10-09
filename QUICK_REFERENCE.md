# MikroKredit - Быстрый справочник

## 🚀 Управление приложением

### Запуск
```bash
cd /home/valstan/mikrokredit
./start_service.sh
```

### Остановка
```bash
cd /home/valstan/mikrokredit
./stop_service.sh
```

### Перезапуск
```bash
cd /home/valstan/mikrokredit
./stop_service.sh && ./start_service.sh
```

### Исправление sequences (если ошибки при добавлении)
```bash
cd /home/valstan/mikrokredit
./fix_sequences.sh
```

### Проверка статуса
```bash
# Процессы
ps aux | grep gunicorn | grep mikrokredit

# Health check
curl http://localhost/healthz

# Логи (реального времени)
tail -f logs/error.log
tail -f logs/access.log
```

## 🔧 Конфигурация

### База данных
```
Хост:        localhost:5432
База:        mikrokredit
Пользователь: mikrokredit_user
Пароль:      mikrokredit_pass_2024
```

### Приложение
```
Порт:        8002 (Gunicorn)
Nginx:       80 (HTTP)
Workers:     4 (1 master + 3 workers)
Health:      /healthz
```

### Пути
```
Проект:      /home/valstan/mikrokredit
VirtualEnv:  /home/valstan/mikrokredit/.venv
Логи:        /home/valstan/mikrokredit/logs
Config:      /home/valstan/mikrokredit/app/config.py
```

## 📊 Мониторинг

### Проверка сервисов
```bash
systemctl status postgresql nginx docker redis-server
```

### Место на диске
```bash
df -h /
du -sh /var/log /var/cache/apt
```

### Подключения к БД
```bash
export PGPASSWORD="mikrokredit_pass_2024"
psql -U mikrokredit_user -d mikrokredit -h localhost
```

### Запросы к БД
```sql
-- Количество займов
SELECT COUNT(*) FROM loans;

-- Неоплаченные займы
SELECT COUNT(*) FROM loans WHERE is_paid = 0;

-- Общая сумма долга
SELECT SUM(amount_due) FROM loans WHERE is_paid = 0;
```

## 🔒 Безопасность

### Sudo
Пользователь `valstan` имеет sudo без пароля:
```bash
sudo whoami  # Работает без запроса пароля
```

### Файрвол (если нужен)
```bash
sudo ufw status
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

## 🛠️ Обслуживание

### Обновление системы
```bash
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get autoremove -y
```

### Очистка
```bash
sudo apt-get clean
sudo apt-get autoclean
sudo journalctl --vacuum-time=7d
```

### Бэкап БД
```bash
# Автоматический (настроен в cron, каждый день в 2:00 MSK)
# Бэкапы на Яндекс.Диск: https://disk.yandex.ru/d/LfNdyqUaDD8rWA

# Создать бэкап вручную
./backup_to_yandex.sh

# Просмотр бэкапов на Яндекс.Диске
./download_from_yandex.sh

# Скачать последний бэкап
./download_from_yandex.sh latest

# Ручной бэкап (если нужно)
export PGPASSWORD="mikrokredit_pass_2024"
pg_dump -U mikrokredit_user -h localhost mikrokredit > backup_$(date +%Y%m%d).sql
```

## 📚 Документация

- `FIXES_2025-10-09.md` - исправления проекта
- `STATUS_REPORT.md` - полный отчёт о состоянии
- `SERVER_MAINTENANCE_2025-10-09.md` - обслуживание сервера
- `QUICK_REFERENCE.md` - этот файл

## 🆘 Troubleshooting

### Ошибка при добавлении займа (duplicate key)
```bash
# Ошибка: "duplicate key value violates unique constraint"
# Причина: рассинхронизированы PostgreSQL sequences

# Исправление:
./fix_sequences.sh

# Проверка вручную:
export PGPASSWORD="mikrokredit_pass_2024"
psql -U mikrokredit_user -d mikrokredit -h localhost -c \
  "SELECT 'loans' as table, MAX(id) as max_id, 
   (SELECT last_value FROM loans_id_seq) as seq FROM loans;"
```

### Приложение не отвечает
```bash
# Проверить процессы
ps aux | grep gunicorn

# Проверить логи
tail -50 logs/error.log

# Перезапустить
./stop_service.sh && ./start_service.sh
```

### Ошибки БД
```bash
# Проверить PostgreSQL
systemctl status postgresql

# Перезапустить PostgreSQL
sudo systemctl restart postgresql

# Проверить подключение
psql -U mikrokredit_user -h localhost -d mikrokredit
```

### Nginx не отдаёт страницы
```bash
# Проверить конфигурацию
sudo nginx -t

# Перезапустить
sudo systemctl restart nginx

# Проверить логи
sudo tail -50 /var/log/nginx/mikrokredit_error.log
```

## 🎯 Быстрые команды

```bash
# Полная проверка системы
systemctl status postgresql nginx docker redis-server --no-pager | grep Active

# Статус MikroKredit
curl -s http://localhost/healthz && echo " ✓"

# Использование диска
df -h / | tail -1 | awk '{print "Диск: " $3 " из " $2 " (" $5 ")"}'

# Память
free -h | grep Mem | awk '{print "Память: " $3 " из " $2}'

# Uptime
uptime -p
```

## 📞 Версии компонентов

После обслуживания 09.10.2025:
- Python: 3.12.3
- Node.js: v22.20.0
- PostgreSQL: 18.0
- Nginx: 1.28.0
- Redis: 7.4.1
- Gunicorn: 21.2.0

**Примечание:** Docker удалён 09.10.2025 - не используется в проекте

---
**Последнее обновление:** 09.10.2025  
**Статус:** ✅ Всё работает

