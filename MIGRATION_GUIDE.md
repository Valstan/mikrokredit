# Миграция данных в Render

## Шаг 1: Получите DATABASE_URL

1. Зайдите в панель Render
2. Откройте вашу PostgreSQL базу данных
3. В разделе "Connections" найдите "External Database URL"
4. Скопируйте URL (выглядит как `postgresql://user:password@host:port/database`)

## Шаг 2: Установите переменную окружения

### Windows (PowerShell):
```powershell
$env:DATABASE_URL = "postgresql://mikrokredit_user:password@dpg-xxxxx-a.oregon-postgres.render.com/mikrokredit"
```

### Windows (CMD):
```cmd
set DATABASE_URL=postgresql://mikrokredit_user:password@dpg-xxxxx-a.oregon-postgres.render.com/mikrokredit
```

### Linux/Mac:
```bash
export DATABASE_URL="postgresql://mikrokredit_user:password@dpg-xxxxx-a.oregon-postgres.render.com/mikrokredit"
```

## Шаг 3: Запустите миграцию

```bash
# Активируйте виртуальное окружение
.\.venv\Scripts\Activate.ps1  # Windows PowerShell
# или
source .venv/bin/activate      # Linux/Mac

# Установите зависимости (если нужно)
pip install -r requirements-web.txt

# Запустите миграцию
python scripts/migrate_to_render.py
```

## Шаг 4: Проверьте результат

1. Откройте ваше веб-приложение на Render
2. Проверьте, что все кредиты и платежи отображаются
3. Создайте тестовый кредит, чтобы убедиться, что данные сохраняются

## Устранение проблем

### Ошибка "No module named 'psycopg2'":
```bash
pip install psycopg2-binary
```

### Ошибка подключения к базе:
- Проверьте, что DATABASE_URL скопирован правильно
- Убедитесь, что база данных на Render запущена
- Проверьте, что IP адрес не заблокирован (Render обычно разрешает все IP)

### Ошибка "relation does not exist":
- Запустите миграцию еще раз - таблицы создадутся автоматически
