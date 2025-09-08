# MikroKredit Organizer

Небольшое приложение-органайзер на Python + PyQt6 для учета микрокредитов с локальной БД (SQLite) и напоминаниями (отключены по умолчанию), а также веб-интерфейс на Flask.

## Возможности
- Хранение записей по кредитам, график платежей, статусы оплат
- Цветовая индикация срочности
- Редактирование с правой панели (десктоп)
- Веб-интерфейс (Flask): список, редактирование, график платежей

## Запуск (десктоп)
1. Создайте и активируйте окружение
2. `pip install -r requirements.txt`
3. `python -m app.main`

## Миграция в Postgres
1. Установите Postgres и создайте БД (например `mikrokredit`)
2. Получите строку подключения вида `postgresql+psycopg://user:pass@host:5432/mikrokredit`
3. Установите переменную окружения:
   - PowerShell: `setx DATABASE_URL "postgresql+psycopg://user:pass@host:5432/mikrokredit"`
   - Перезапустите терминал
4. Запустите миграцию (прочитает текущий `mikrokredit.db` и перенесет данные):
   ```powershell
   python scripts\migrate_to_postgres.py
   ```

## Запуск веб-интерфейса в облаке
- Подходит любой PaaS (Render, Fly.io, Railway, Яндекс Облако). Нужны:
  - Переменная `DATABASE_URL` (строка подключения к Postgres)
  - Команда запуска `gunicorn 'web:create_app()' --bind 0.0.0.0:$PORT`

Пример `Procfile` (Heroku/Render):
```
web: gunicorn "web:create_app()" --bind 0.0.0.0:$PORT
```

Проверка локально:
```powershell
$env:DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/mikrokredit"
python -m web.run_web
```

Если требуется доступ с телефона по Wi‑Fi, запустите на локальном IP (замените 127.0.0.1 на IP машины) и разрешите брандмауэр:
```powershell
$IP=(Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "Wi-Fi").IPAddress
$env:FLASK_RUN_HOST=$IP
python -m web.run_web
```
И далее откройте `http://<IP>:5000/` с другого устройства в той же сети.

## Требования
- Windows 11
- Python 3.10+ (рекомендуется 3.11)

## Установка и запуск (локально)
1. Создайте и активируйте виртуальное окружение:
   - PowerShell:
     ```powershell
     py -3 -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
2. Установите зависимости:
   ```powershell
   pip install -r requirements.txt
   ```
3. Запустите приложение:
   ```powershell
   python -m app.main
   ```

База данных `mikrokredit.db` создастся автоматически в корне проекта при первом запуске.

## Сборка exe (PyInstaller)
1. Убедитесь, что окружение активно и зависимости установлены
2. Выполните:
   ```powershell
   python build_exe.py
   ```
   Готовый exe-файл появится в папке `dist/`.

Альтернатива: используйте сценарий PowerShell:
```powershell
./make_exe.ps1
```

## Структура проекта (основное)
```
app/
  main.py
  db.py
  repository.py
  reminder.py
  ui/
    main_window.py
    dialogs.py
```

## Примечания по данным
- Даты хранятся как ISO-строки `YYYY-MM-DD`
- Напоминание срабатывает однажды за 7 дней до даты возврата (помечается в БД)

## Лицензия
MIT (по умолчанию). Измените при необходимости.
