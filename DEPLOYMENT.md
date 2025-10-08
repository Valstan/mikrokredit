# MikroKredit - Развертывание на сервере

## Обзор

Проект MikroKredit успешно развернут на сервере и настроен для работы в production режиме. Приложение использует Flask веб-фреймворк с PostgreSQL базой данных, запущенной в Docker контейнере.

## Структура проекта

```
/home/valstan/development/mikrokredit/
├── app/                    # Основное приложение
│   ├── config.py          # Конфигурация
│   ├── db_sa.py           # Подключение к БД
│   ├── models_sa.py       # Модели данных
│   └── ...
├── web/                   # Веб-интерфейс
│   ├── __init__.py        # Flask приложение
│   ├── views.py           # Маршруты
│   ├── templates/         # HTML шаблоны
│   └── run_web.py         # Запуск для разработки
├── .venv/                 # Виртуальное окружение Python
├── logs/                  # Логи приложения
├── postgres.sh            # Скрипт управления PostgreSQL
├── start.sh               # Скрипт управления приложением
├── gunicorn.conf.py       # Конфигурация Gunicorn
├── mikrokredit.service     # Systemd сервис
└── nginx.conf             # Конфигурация Nginx
```

## Управление приложением

### PostgreSQL база данных

```bash
cd /home/valstan/development/mikrokredit

# Управление PostgreSQL контейнером
./postgres.sh start      # Запустить PostgreSQL
./postgres.sh stop       # Остановить PostgreSQL
./postgres.sh restart    # Перезапустить PostgreSQL
./postgres.sh status     # Показать статус
./postgres.sh backup     # Создать резервную копию
./postgres.sh connect    # Подключиться к БД через psql
```

### Веб-приложение

```bash
# Запуск
./start.sh start

# Остановка
./start.sh stop

# Перезапуск
./start.sh restart

# Статус
./start.sh status
```

### Проверка работы

- **Health check**: http://localhost:8000/healthz
- **Главная страница**: http://localhost:8000/
- **API**: http://localhost:8000/export/json

## Конфигурация

### База данных

По умолчанию используется PostgreSQL база данных в Docker контейнере. Для переключения на SQLite (для отладки):

1. Установите переменную окружения:
   ```bash
   export MIKROKREDIT_USE_SQLITE=1
   ```

2. Перезапустите приложение:
   ```bash
   ./start.sh restart
   ```

**PostgreSQL подключение:**
- Host: localhost
- Port: 5433
- Database: mikrokredit
- User: mikrokredit_user
- Password: mikrokredit_pass

### Настройка Nginx (опционально)

Для использования Nginx как reverse proxy:

1. Скопируйте конфигурацию:
   ```bash
   sudo cp nginx.conf /etc/nginx/sites-available/mikrokredit
   sudo ln -s /etc/nginx/sites-available/mikrokredit /etc/nginx/sites-enabled/
   ```

2. Перезапустите Nginx:
   ```bash
   sudo systemctl restart nginx
   ```

## Systemd сервис

Для автозапуска приложения при загрузке системы:

1. Скопируйте сервис:
   ```bash
   sudo cp mikrokredit.service /etc/systemd/system/
   ```

2. Включите автозапуск:
   ```bash
   sudo systemctl enable mikrokredit
   sudo systemctl start mikrokredit
   ```

## Мониторинг

### Логи

- **Access log**: `/home/valstan/development/mikrokredit/logs/access.log`
- **Error log**: `/home/valstan/development/mikrokredit/logs/error.log`

### Мониторинг процессов

```bash
# Проверка статуса
./start.sh status

# Проверка через systemctl (если настроен)
sudo systemctl status mikrokredit

# Проверка портов
netstat -tlnp | grep :8000
```

## Разработка

### Локальная разработка

```bash
cd /home/valstan/development/mikrokredit
source .venv/bin/activate
python -m web.run_web
```

### Обновление зависимостей

```bash
cd /home/valstan/development/mikrokredit
source .venv/bin/activate
pip install -r requirements-web.txt
./start.sh restart
```

## Безопасность

- Приложение запускается от пользователя `valstan`
- Используется локальный интерфейс (127.0.0.1:8000)
- Для внешнего доступа рекомендуется использовать Nginx с SSL
- База данных SQLite защищена правами доступа файловой системы

## Резервное копирование

### База данных PostgreSQL

```bash
# Создание резервной копии PostgreSQL
./postgres.sh backup

# Восстановление из резервной копии
./postgres.sh restore mikrokredit_postgres_backup_YYYYMMDD_HHMMSS.sql
```

### Экспорт данных через веб-интерфейс

Перейдите на http://localhost:8000/export/json для скачивания всех данных в JSON формате.

### Миграция данных

```bash
# Миграция из Render PostgreSQL в локальный PostgreSQL
python scripts/migrate_to_local_postgres.py

# Миграция из SQLite в PostgreSQL (если нужно)
python scripts/migrate_to_postgres.py
```

## Устранение неполадок

### Приложение не запускается

1. Проверьте логи:
   ```bash
   tail -f logs/error.log
   ```

2. Проверьте права доступа:
   ```bash
   ls -la mikrokredit.db
   ls -la logs/
   ```

3. Проверьте виртуальное окружение:
   ```bash
   source .venv/bin/activate
   python -c "import flask; print('Flask OK')"
   ```

### Проблемы с базой данных

1. Проверьте статус PostgreSQL:
   ```bash
   ./postgres.sh status
   ```

2. Перезапустите PostgreSQL:
   ```bash
   ./postgres.sh restart
   ```

3. Проверьте подключение к БД:
   ```bash
   ./postgres.sh connect
   ```

4. Если PostgreSQL не запускается, проверьте Docker:
   ```bash
   docker ps -a | grep mikrokredit-postgres
   docker logs mikrokredit-postgres
   ```

## Контакты

Проект разработан для управления микрокредитами с веб-интерфейсом для доступа с любых устройств.
