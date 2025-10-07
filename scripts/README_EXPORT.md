# Скрипты экспорта и импорта данных микрокредита

Этот набор скриптов позволяет экспортировать данные из базы данных микрокредита и импортировать их в другую базу данных.

## Скрипты

### 1. export_data.py - Экспорт данных

Экспортирует все данные из таблиц `loans` и `installments` в JSON или SQL файл.

#### Использование:

```bash
# Экспорт в JSON (по умолчанию)
python export_data.py

# Экспорт в JSON с указанным именем файла
python export_data.py my_export.json

# Экспорт в SQL формат
python export_data.py --sql

# Экспорт в SQL с указанным именем файла
python export_data.py --sql my_export.sql

# Показать справку
python export_data.py --help
```

#### Формат JSON файла:

```json
{
  "export_info": {
    "export_date": "2024-01-01T12:00:00",
    "database_url": "dpg-d308623e5dus73dfrrsg-a.oregon-postgres.render.com/mikrokredit",
    "total_loans": 10,
    "total_installments": 25
  },
  "loans": [
    {
      "id": 1,
      "website": "example.com",
      "loan_date": "2024-01-01",
      "amount_borrowed": 1000.0,
      "amount_due": 1200.0,
      "due_date": "2024-02-01",
      "risky_org": false,
      "notes": "Заметки",
      "payment_methods": "Карта",
      "reminded_pre_due": false,
      "created_at": "2024-01-01 10:00:00",
      "is_paid": false,
      "org_name": "Название организации"
    }
  ],
  "installments": [
    {
      "id": 1,
      "loan_id": 1,
      "due_date": "2024-01-15",
      "amount": 600.0,
      "paid": false,
      "paid_date": null,
      "created_at": "2024-01-01 10:00:00"
    }
  ]
}
```

### 2. import_data.py - Импорт данных

Импортирует данные из JSON файла в базу данных.

#### Использование:

```bash
# Импорт с добавлением к существующим данным
python import_data.py mikrokredit_export_20240101_120000.json

# Импорт с очисткой существующих данных
python import_data.py mikrokredit_export_20240101_120000.json --clear
```

## Настройка

Скрипты автоматически используют настройки подключения к базе данных из `app/config.py`. 

По умолчанию подключаются к PostgreSQL базе на Render.com:
- URL: `postgresql://mikrokredit_user:***@dpg-d308623e5dus73dfrrsg-a.oregon-postgres.render.com/mikrokredit`

## Требования

Убедитесь, что установлены все необходимые зависимости:

```bash
pip install -r requirements.txt
```

Основные зависимости:
- SQLAlchemy >= 2.0
- psycopg2-binary >= 2.9.0

## Примеры использования

### Полный цикл миграции данных:

1. **Экспорт данных из старой базы:**
   ```bash
   python scripts/export_data.py backup_old_data.json
   ```

2. **Импорт данных в новую базу:**
   ```bash
   python scripts/import_data.py backup_old_data.json --clear
   ```

### Экспорт в SQL для прямого импорта:

```bash
python scripts/export_data.py --sql migration.sql
```

Затем выполните SQL файл в новой базе данных.

## Безопасность

- Скрипты не показывают полные учетные данные в логах
- При импорте с флагом `--clear` запрашивается подтверждение
- Создаются резервные копии с временными метками

## Устранение неполадок

### Ошибка подключения к базе данных:
- Проверьте настройки в `app/config.py`
- Убедитесь, что база данных доступна
- Проверьте правильность учетных данных

### Ошибки при импорте:
- Убедитесь, что JSON файл не поврежден
- Проверьте, что в базе данных есть необходимые таблицы
- Используйте флаг `--clear` для полной очистки перед импортом

