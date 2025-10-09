# Исправление проблемы с PostgreSQL Sequences - 09.10.2025

## Проблема

При добавлении нового кредита возникала ошибка:
```
(psycopg2.errors.UniqueViolation) duplicate key value violates unique constraint "loans_pkey"
DETAIL: Key (id)=(2) already exists.
```

## Причина

PostgreSQL sequences (счетчики для автоинкремента) были рассинхронизированы с реальными данными в таблицах:

### Было:
| Таблица       | MAX(id) | Sequence | Проблема |
|---------------|---------|----------|----------|
| loans         | 28      | 2        | ❌ Sequence отстаёт на 26! |
| installments  | 64      | 1        | ❌ Sequence отстаёт на 63! |

Sequence пытался выдать ID, который уже существовал в таблице, вызывая ошибку уникальности ключа.

## Решение

Синхронизированы sequences с максимальными ID в таблицах:

```sql
-- Для таблицы loans
SELECT setval('loans_id_seq', (SELECT MAX(id) FROM loans));

-- Для таблицы installments  
SELECT setval('installments_id_seq', (SELECT MAX(id) FROM installments));
```

### Стало:
| Таблица       | MAX(id) | Sequence | Статус |
|---------------|---------|----------|--------|
| loans         | 29      | 29       | ✅ Синхронизировано |
| installments  | 64      | 64       | ✅ Синхронизировано |

## Как это произошло?

Возможные причины рассинхронизации:
1. **Импорт данных** - если данные были импортированы с явными ID без обновления sequence
2. **Прямые INSERT** - SQL команды с явным указанием ID
3. **Восстановление из бэкапа** - если sequence не был восстановлен корректно
4. **Миграция данных** - при переносе данных из другой БД

## Тест

После исправления была создана тестовая запись:
- ✅ ID=29 создан успешно
- ✅ Ошибка больше не возникает
- ✅ Автоинкремент работает корректно

## Автоматическая проверка

Создан скрипт `fix_sequences.sh` для автоматической проверки и исправления:

```bash
./fix_sequences.sh
```

Скрипт:
- Проверяет все sequences в базе данных
- Сравнивает с максимальными ID в таблицах
- Автоматически синхронизирует при необходимости
- Выводит подробный отчёт

### Пример вывода:
```
🔧 Синхронизация PostgreSQL sequences...
  Проверка loans... ✅ OK (значение: 29)
  Проверка installments... ✅ OK (значение: 64)
✅ Синхронизация завершена!
```

## Рекомендации

### 1. Регулярная проверка
Рекомендуется проверять sequences после:
- Импорта данных
- Восстановления из бэкапа
- Миграций
- Прямых SQL операций

```bash
cd /home/valstan/mikrokredit
./fix_sequences.sh
```

### 2. Правильный импорт данных
При импорте данных с явными ID всегда синхронизируйте sequences:

```sql
-- После импорта в таблицу loans
SELECT setval('loans_id_seq', (SELECT MAX(id) FROM loans), true);

-- После импорта в таблицу installments
SELECT setval('installments_id_seq', (SELECT MAX(id) FROM installments), true);
```

### 3. Бэкапы
При создании бэкапа используйте флаг для сохранения sequences:

```bash
pg_dump -U mikrokredit_user -h localhost mikrokredit > backup.sql
# pg_dump автоматически сохраняет sequences
```

При восстановлении sequences должны восстановиться автоматически, но всё равно проверьте:

```bash
psql -U mikrokredit_user -h localhost mikrokredit < backup.sql
./fix_sequences.sh  # Проверка
```

## Проверка вручную

### Проверка одной таблицы:
```sql
SELECT 
    'loans' as table_name,
    MAX(id) as max_id,
    (SELECT last_value FROM loans_id_seq) as seq_value,
    (SELECT is_called FROM loans_id_seq) as is_called
FROM loans;
```

### Проверка всех таблиц:
```sql
SELECT 
    'loans' as table_name,
    COALESCE(MAX(id), 0) as max_id,
    (SELECT last_value FROM loans_id_seq) as sequence_value
FROM loans
UNION ALL
SELECT 
    'installments' as table_name,
    COALESCE(MAX(id), 0) as max_id,
    (SELECT last_value FROM installments_id_seq) as sequence_value
FROM installments;
```

### Ручная синхронизация:
```bash
export PGPASSWORD="mikrokredit_pass_2024"

# Loans
psql -U mikrokredit_user -d mikrokredit -h localhost -c \
  "SELECT setval('loans_id_seq', COALESCE((SELECT MAX(id) FROM loans), 1), true);"

# Installments
psql -U mikrokredit_user -d mikrokredit -h localhost -c \
  "SELECT setval('installments_id_seq', COALESCE((SELECT MAX(id) FROM installments), 1), true);"
```

## Добавление в документацию

Скрипт `fix_sequences.sh` добавлен в проект:
```
/home/valstan/mikrokredit/
  ├─ start_service.sh         # Запуск приложения
  ├─ stop_service.sh          # Остановка приложения
  └─ fix_sequences.sh         # ⭐ Синхронизация sequences (НОВЫЙ)
```

## Предотвращение в будущем

### В коде приложения
SQLAlchemy модель уже настроена правильно:
```python
id: Mapped[int] = mapped_column(
    Integer, 
    Sequence('loans_id_seq'),  # Явное указание sequence
    primary_key=True, 
    autoincrement=True         # Автоинкремент
)
```

### При миграциях
Если используются миграции (Alembic), всегда включайте проверку sequences:
```python
# В миграции после изменения данных
op.execute("SELECT setval('loans_id_seq', (SELECT MAX(id) FROM loans), true);")
```

### Мониторинг
Можно добавить проверку в cron для автоматического мониторинга:
```bash
# Добавить в crontab (каждый день в 3:00)
0 3 * * * /home/valstan/mikrokredit/fix_sequences.sh >> /home/valstan/mikrokredit/logs/sequences.log 2>&1
```

## Итог

✅ **Проблема решена**
- Sequences синхронизированы
- Добавление новых записей работает
- Создан скрипт для автоматической проверки
- Документация обновлена

🔧 **Для проверки в будущем:**
```bash
./fix_sequences.sh
```

---
**Дата исправления:** 09.10.2025 08:45 MSK  
**Затронутые таблицы:** loans, installments  
**Статус:** ✅ Исправлено и протестировано

