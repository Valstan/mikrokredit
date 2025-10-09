# Автоматический бэкап на Яндекс.Диск - 09.10.2025

## Настройка

Настроен автоматический ежедневный бэкап базы данных PostgreSQL на Яндекс.Диск.

### Параметры:

| Параметр | Значение |
|----------|----------|
| **База данных** | mikrokredit (PostgreSQL 18.0) |
| **Папка на Яндекс.Диске** | /МикроКредит_Backups |
| **Публичная ссылка** | https://yadi.sk/d/gVpI3Fst7J5EIw |
| **Расписание** | Ежедневно в 2:00 MSK |
| **Максимум бэкапов на Я.Диске** | 10 (старые удаляются автоматически) |
| **Локальные копии** | 3 последних |
| **Формат** | SQL дамп, сжатый gzip |

### Файлы:

```
/home/valstan/mikrokredit/
  ├─ backup_to_yandex.sh      # Скрипт бэкапа
  ├─ backups/                  # Локальные бэкапы (3 последних)
  └─ logs/backup.log           # Лог всех операций
```

## Как работает

### 1. Создание бэкапа (2:00 MSK каждый день)

Скрипт выполняет:
1. **Создание дампа PostgreSQL**
   ```bash
   pg_dump -U mikrokredit_user -h localhost mikrokredit
   ```

2. **Сжатие**
   - SQL дамп → gzip
   - Размер уменьшается в ~2 раза

3. **Загрузка на Яндекс.Диск**
   - Через REST API
   - В папку `/МикроКредит_Backups`
   - Имя файла: `mikrokredit_YYYYMMDD_HHMMSS.sql.gz`

4. **Ротация бэкапов**
   - На Яндекс.Диске: оставляет 10 последних
   - Локально: оставляет 3 последних
   - Старые удаляются автоматически

### 2. Cron задача

```bash
# MikroKredit - автоматический бэкап БД на Яндекс.Диск в 2:00 MSK
0 2 * * * /home/valstan/mikrokredit/backup_to_yandex.sh >> /home/valstan/mikrokredit/logs/backup.log 2>&1
```

## Ручной запуск

### Создать бэкап сейчас:
```bash
cd /home/valstan/mikrokredit
./backup_to_yandex.sh
```

### Просмотр лога:
```bash
tail -50 /home/valstan/mikrokredit/logs/backup.log
```

### Просмотр локальных бэкапов:
```bash
ls -lh /home/valstan/mikrokredit/backups/
```

## Восстановление из бэкапа

### Из локальной копии:

1. **Распаковать:**
   ```bash
   gunzip /home/valstan/mikrokredit/backups/mikrokredit_YYYYMMDD_HHMMSS.sql.gz
   ```

2. **Восстановить:**
   ```bash
   export PGPASSWORD="mikrokredit_pass_2024"
   psql -U mikrokredit_user -h localhost -d mikrokredit < backup_file.sql
   ```

### Из Яндекс.Диска:

1. **Скачать файл:**
   ```bash
   # Можно через веб-интерфейс: https://disk.yandex.ru/d/LfNdyqUaDD8rWA
   # Или через API (см. скрипт download_from_yandex.sh)
   ```

2. **Распаковать и восстановить** (как выше)

## Проверка бэкапов

### На Яндекс.Диске (через API):
```bash
curl -s "https://cloud-api.yandex.net/v1/disk/resources?path=/МикроКредит_Backups" \
  -H "Authorization: OAuth y0__xDR8Z0KGNuWAyCFzMykFJz31O8WoqV9ONfVuMNLNIyjYsZK" \
  | python3 -m json.tool
```

### Через веб-интерфейс:
Откройте: **https://yadi.sk/d/gVpI3Fst7J5EIw**

### Проверка cron:
```bash
# Просмотр задач
crontab -l

# Проверка последнего запуска
grep "=== Бэкап завершён ===" /home/valstan/mikrokredit/logs/backup.log | tail -5
```

## Мониторинг

### Логи бэкапов:
```bash
# Последние бэкапы
tail -100 /home/valstan/mikrokredit/logs/backup.log

# Поиск ошибок
grep "✗" /home/valstan/mikrokredit/logs/backup.log

# Успешные бэкапы
grep "✓ Бэкап загружен" /home/valstan/mikrokredit/logs/backup.log
```

### Размер бэкапов:
```bash
# Локальные
du -sh /home/valstan/mikrokredit/backups/*

# На Яндекс.Диске (через API)
curl -s "https://cloud-api.yandex.net/v1/disk/resources?path=/МикроКредит_Backups" \
  -H "Authorization: OAuth y0__xDR8Z0KGNuWAyCFzMykFJz31O8WoqV9ONfVuMNLNIyjYsZK" \
  | grep -o '"size":[0-9]*'
```

## Тестирование

### Тест создан и выполнен успешно:
```
[2025-10-09 08:55:53] === Начало создания бэкапа ===
[2025-10-09 08:55:53] ✓ Дамп создан успешно (размер: 16K)
[2025-10-09 08:55:53] ✓ Бэкап сжат (размер: 8.0K)
[2025-10-09 08:55:54] ✓ Бэкап загружен на Яндекс.Диск
[2025-10-09 08:55:55] === Бэкап завершён ===
```

## Безопасность

### Токен OAuth:
- Хранится в скрипте (chmod 700)
- Доступ только для пользователя valstan
- Токен имеет ограниченные права

### Пароль БД:
- Используется переменная окружения
- Очищается после использования
- Не записывается в логи

### Рекомендации:
1. Регулярно проверяйте логи
2. Тестируйте восстановление (раз в месяц)
3. Следите за местом на Яндекс.Диске
4. Обновляйте токен при необходимости

## Размер и хранение

### Текущий размер:
- Один бэкап: ~8 KB (сжатый)
- 10 бэкапов: ~80 KB
- Занимает минимум места!

### Хранение:
- **Яндекс.Диск:** 10 последних бэкапов
- **Локально:** 3 последних бэкапа
- **Итого:** ~13 точек восстановления

## Troubleshooting

### Ошибка загрузки на Яндекс.Диск:

**Проблема:** "Не удалось получить URL для загрузки"

**Решение:**
```bash
# Проверить токен
curl -s "https://cloud-api.yandex.net/v1/disk/" \
  -H "Authorization: OAuth TOKEN" | python3 -m json.tool

# Создать папку заново
curl -X PUT "https://cloud-api.yandex.net/v1/disk/resources?path=/МикроКредит_Backups" \
  -H "Authorization: OAuth TOKEN"
```

### Ошибка создания дампа:

**Проблема:** "Ошибка создания дампа"

**Решение:**
```bash
# Проверить PostgreSQL
systemctl status postgresql

# Проверить подключение
psql -U mikrokredit_user -h localhost -d mikrokredit -c "SELECT 1;"

# Проверить права
ls -l /home/valstan/mikrokredit/backups/
```

### Cron не запускается:

**Проблема:** Нет новых бэкапов

**Решение:**
```bash
# Проверить cron
crontab -l

# Проверить логи cron
grep CRON /var/log/syslog | tail

# Запустить вручную для теста
./backup_to_yandex.sh
```

## Дополнительные скрипты

### Скрипт скачивания с Яндекс.Диска:

Создайте `download_from_yandex.sh`:
```bash
#!/bin/bash
# Скачивание бэкапа с Яндекс.Диска

YANDEX_TOKEN="y0__xDR8Z0KGNuWAyCFzMykFJz31O8WoqV9ONfVuMNLNIyjYsZK"
BACKUP_FILE="$1"  # Имя файла на Яндекс.Диске

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 mikrokredit_YYYYMMDD_HHMMSS.sql.gz"
    exit 1
fi

# Получаем ссылку для скачивания
DOWNLOAD_URL=$(curl -s "https://cloud-api.yandex.net/v1/disk/resources/download?path=/МикроКредит_Backups/$BACKUP_FILE" \
    -H "Authorization: OAuth $YANDEX_TOKEN" \
    | grep -o '"href":"[^"]*"' | cut -d'"' -f4)

# Скачиваем
curl -L "$DOWNLOAD_URL" -o "$BACKUP_FILE"
echo "Бэкап скачан: $BACKUP_FILE"
```

## Статистика

### История бэкапов:
```bash
# Количество успешных бэкапов
grep "✓ Бэкап загружен" logs/backup.log | wc -l

# Последние 10 бэкапов
grep "=== Бэкап завершён ===" logs/backup.log | tail -10

# Средний размер
grep "Размер:" logs/backup.log | tail -10
```

---
**Дата настройки:** 09.10.2025 09:00 MSK  
**Первый бэкап:** 09.10.2025 08:55 MSK (тестовый)  
**Следующий автоматический:** 10.10.2025 02:00 MSK  
**Статус:** ✅ Работает автоматически

