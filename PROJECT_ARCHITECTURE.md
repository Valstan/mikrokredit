# Архитектура проекта "Записная книжка Валентина"

## 📋 Общее описание

**Записная книжка Валентина** (MikroKredit Manager) - комплексная веб-система для управления микрозаймами и личными задачами с интеграцией Telegram бота.

**Версия:** 2.0.0  
**Дата создания:** 09.10.2025  
**Стек:** Python 3.12, Flask, PostgreSQL, Telegram Bot API

---

## 🏗️ Структура проекта

```
/home/valstan/mikrokredit/
│
├── app/                          # Основная бизнес-логика
│   ├── __init__.py
│   ├── auth.py                   # Аутентификация и безопасность
│   ├── config.py                 # Конфигурация приложения
│   ├── db_sa.py                  # SQLAlchemy engine и сессии
│   ├── models_sa.py              # ORM модели (9 таблиц)
│   ├── integration.py            # Интеграции (Redis, API)
│   └── ui/                       # Старый desktop UI (не используется)
│
├── web/                          # Flask веб-приложение
│   ├── __init__.py               # Создание Flask app
│   ├── views.py                  # Маршруты для займов и dashboard
│   ├── auth_views.py             # Маршруты аутентификации
│   ├── tasks_views.py            # Маршруты органайзера задач
│   └── templates/                # HTML шаблоны
│       ├── base.html             # Базовый шаблон с navbar
│       ├── dashboard.html        # Главная страница
│       ├── index.html            # Список займов
│       ├── loan_edit.html        # Редактирование займа
│       ├── auth/                 # Шаблоны входа
│       │   ├── login.html
│       │   └── blocked.html
│       └── tasks/                # Шаблоны задач
│           ├── index.html
│           ├── edit.html
│           └── categories.html
│
├── logs/                         # Логи всех сервисов
│   ├── error.log                 # Ошибки Flask
│   ├── access.log                # Доступ к сайту
│   ├── backup.log                # Бэкапы
│   ├── telegram.log              # Уведомления о займах
│   ├── telegram_tasks.log        # Напоминания о задачах
│   ├── telegram_repeat.log       # Повторные напоминания
│   └── telegram_bot_fresh.log    # Telegram бот-сервер
│
├── backups/                      # Локальные бэкапы БД
│
├── scripts/                      # Утилиты
│
├── Telegram боты и сервисы:
│   ├── telegram_notifier.py      # Уведомления о горящих займах
│   ├── telegram_bot_tasks.py     # Отправка напоминаний о задачах
│   ├── telegram_bot_server.py    # Обработка callback кнопок (фоновый)
│   ├── telegram_repeat_reminders.py  # Повторные напоминания
│   └── init_reminder_templates.py    # Инициализация шаблонов
│
├── Скрипты управления:
│   ├── start_service.sh          # Запуск веб-сервера
│   ├── stop_service.sh           # Остановка веб-сервера
│   ├── start_telegram_bot.sh     # Запуск Telegram бота
│   ├── backup_to_yandex.sh       # Бэкап на Яндекс.Диск
│   ├── download_from_yandex.sh   # Скачать бэкап
│   └── fix_sequences.sh          # Исправление sequences БД
│
├── Конфигурация:
│   ├── gunicorn.conf.py          # Настройки Gunicorn
│   ├── nginx.conf                # Конфигурация Nginx
│   ├── mikrokredit.service       # Systemd service
│   └── mikrokredit.conf          # Nginx site config
│
├── Документация: (25 MD файлов)
│   ├── START_HERE_v2.md          # НАЧАТЬ ОТСЮДА ⭐
│   ├── COMPLETE_GUIDE_2025-10-09.md
│   ├── PROJECT_ARCHITECTURE.md   # Этот файл
│   └── ...остальные
│
└── Прочее:
    ├── requirements.txt          # Python зависимости
    ├── .gitignore                # Git ignore правила
    └── README.md                 # Основной README

```

---

## 🗄️ База данных (PostgreSQL 18.0)

### Подключение:
```
Host:     localhost:5432
Database: mikrokredit
User:     mikrokredit_user
Password: mikrokredit_pass_2024
```

### Таблицы:

#### Займы (4 таблицы):
1. **loans** - основная таблица займов
   - id, org_name, website, loan_date, due_date
   - amount_borrowed, amount_due, is_paid
   - risky_org, notes, payment_methods

2. **installments** - платежи по рассрочке
   - id, loan_id, due_date, amount
   - paid, paid_date

#### Задачи (5 таблиц):
3. **tasks** - задачи
   - id, title, description
   - status (0/1), importance (1/2/3)
   - due_date, category_id
   - is_recurring, recurrence_rule

4. **task_categories** - категории задач
   - id, name, color, icon

5. **subtasks** - подзадачи (чеклисты)
   - id, task_id, title, completed, order

6. **task_reminders** - напоминания
   - id, task_id, reminder_time
   - sent, sent_at, telegram_message_id
   - acknowledged, acknowledged_at

7. **reminder_templates** - шаблоны напоминаний
   - id, name, description, rules (JSON)

---

## 🔄 Бизнес-логика

### Займы (МикроКредит)

#### Расчёт долга:
1. Для каждого займа проверяются **installments** (платежи)
2. Если есть платежи → сумма = SUM(unpaid installments)
3. Если нет платежей → сумма = amount_due
4. **Оплачен** = все installments.paid = 1

#### Критерий "горящий":
- Берётся ближайший неоплаченный installment
- Вычисляется days_left = (due_date - today).days
- **Горящий** если days_left < 5

#### Статистика:
- **Всего:** COUNT(loans)
- **Горящие:** COUNT где days_left < 5
- **Долг:** SUM(unpaid_total) по всем займам

### Задачи (Органайзер)

#### Важность (3 уровня):
- **1** = 🔴 Важная (критические, с дедлайном)
- **2** = 🟡 Нужная (плановые)
- **3** = ⚪ Хотелось бы (желательные)

#### Статусы:
- **0** = Не выполнено
- **1** = Выполнено

#### Напоминания:

**Шаблоны (5 готовых):**
1. За 1 день до срока
2. За день и в день
3. Интенсивные (3 напоминания)
4. Очень интенсивные (5 напоминаний)
5. Только в день дедлайна

**Кастомные:**
- Пользователь может добавить любые даты/время
- Хранятся в task_reminders

**Логика отправки:**
1. Cron запускает `telegram_bot_tasks.py` каждую минуту
2. Проверяются task_reminders где:
   - sent = 0
   - reminder_time <= NOW()
3. Отправляется в Telegram с inline кнопками
4. Сохраняется telegram_message_id
5. Помечается sent = 1

**Повторные напоминания:**
1. Cron запускает `telegram_repeat_reminders.py` каждые 15 минут
2. Проверяются task_reminders где:
   - sent = 1
   - acknowledged = 0
   - sent_at < NOW() - 15 минут
3. Отправляется повторно
4. Обновляется sent_at

**Рабочие часы:**
- Уведомления только с 7:00 до 22:00 MSK
- Ночью не беспокоит

---

## 🔐 Аутентификация

### Схема:
1. Пользователь открывает сайт → редирект на `/auth/login`
2. Вводит пароль (max 3 попытки)
3. При успехе → session['authenticated'] = True
4. Cookie на 30 дней

### Блокировка:
- По IP адресу (учитывается X-Forwarded-For)
- После 3 неудачных попыток → 5 минут блокировки
- Обратный отсчёт на странице блокировки
- Старые попытки очищаются через 10 минут

### Защита маршрутов:
```python
@login_required  # Декоратор на всех маршрутах кроме healthz и auth
```

---

## 📱 Telegram интеграция

### Боты и скрипты:

#### 1. telegram_notifier.py
**Назначение:** Уведомления о горящих займах  
**Расписание:** 10:00 и 20:00 MSK (cron)  
**Логика:**
- Проверяет займы с days_left <= 2
- Формирует сообщение со списком
- Отправляет в Telegram (без кнопок)

#### 2. telegram_bot_tasks.py
**Назначение:** Отправка напоминаний о задачах  
**Расписание:** Каждую минуту (cron)  
**Логика:**
- Проверяет task_reminders (sent=0, time<=NOW)
- Отправляет с inline кнопками
- Только в рабочие часы (7-22)

#### 3. telegram_repeat_reminders.py
**Назначение:** Повторные напоминания  
**Расписание:** Каждые 15 минут (cron)  
**Логика:**
- Проверяет неподтверждённые (acknowledged=0)
- Отправлено > 15 минут назад
- Отправляет повторно
- Только в рабочие часы

#### 4. telegram_bot_server.py
**Назначение:** Обработка callback кнопок  
**Режим:** Работает постоянно (фоновый процесс)  
**Логика:**
- Polling Telegram API
- Обрабатывает callback_query
- Кнопка "Выполнил" → task.status = 1
- Кнопка "Отложить" → открывает задачу в браузере

### Inline кнопки:

```python
callback_data="task_complete_{task_id}_{reminder_id}"  # Выполнил
callback_data="task_postpone_{task_id}_{reminder_id}"  # Отложить
```

---

## 🔄 Автоматизация (Cron)

```bash
# Напоминания о задачах
* * * * *       telegram_bot_tasks.py

# Повторные напоминания
*/15 * * * *    telegram_repeat_reminders.py

# Горящие займы
0 10,20 * * *   telegram_notifier.py

# Бэкап на Яндекс.Диск
0 2 * * *       backup_to_yandex.sh
```

---

## 🌐 Веб-приложение (Flask)

### Blueprints:

#### 1. auth (auth_views.py)
- `/auth/login` - страница входа
- `/auth/logout` - выход

#### 2. views (views.py)
- `/` - Dashboard
- `/loans` - список займов
- `/loan/new` - создание займа
- `/loan/<id>` - редактирование
- `/loan/<id>/installments/add` - добавить платёж
- `/loan/<id>/delete` - удалить

#### 3. tasks (tasks_views.py)
- `/tasks/` - список задач
- `/tasks/new` - создание
- `/tasks/<id>` - редактирование
- `/tasks/<id>/complete` - пометить выполненной
- `/tasks/<id>/delete` - удалить
- `/tasks/categories` - категории

### Middleware:
- ProxyFix - для работы за Nginx
- Session - 30 дней cookie

---

## 🚀 Deployment

### Архитектура:

```
Internet
    ↓
Nginx :80 (reverse proxy)
    ↓
Gunicorn :8002 (4 workers)
    ↓
Flask Application
    ↓
PostgreSQL :5432
    ↓
Redis :6379 (cache)
```

### Процессы:

1. **Gunicorn** - веб-сервер
   - 1 master + 3 workers
   - Порт: 8002
   - Config: gunicorn.conf.py

2. **Telegram Bot Server** - обработка callback
   - Фоновый процесс
   - Polling API
   - Логи: logs/telegram_bot_fresh.log

3. **PostgreSQL** - база данных
   - Version: 18.0
   - Pool: 10 + 20 overflow
   - Pre-ping: enabled

4. **Nginx** - reverse proxy
   - Version: 1.28.0
   - SSL: ready (не настроен)
   - Config: /etc/nginx/conf.d/mikrokredit.conf

5. **Redis** - кэширование
   - Version: 7.4.1
   - Используется для cache_manager

---

## 🔧 Конфигурация

### Переменные окружения:
```bash
MIKROKREDIT_DATABASE_URL=postgresql://mikrokredit_user:mikrokredit_pass_2024@localhost:5432/mikrokredit
```

### Секреты:
- **Auth password:** Nitro@1941
- **Telegram token:** 489021673:AAH7QDGmqzOMgT0W_wINvzWC1ihfljuFAKI
- **Telegram chat_id:** 352096813
- **Yandex token:** y0__xDR8Z0KGNuWAyCFzMykFJz31O8WoqV9ONfVuMNLNIyjYsZK

### Flask config:
```python
SECRET_KEY = "mikrokredit_secret_key_2025_secure_random_string"
PERMANENT_SESSION_LIFETIME = 30 days
```

---

## 📊 Важные алгоритмы

### 1. Расчёт долга по займу

```python
def get_loan_debt(loan_id):
    # Сумма неоплаченных платежей
    unpaid = SUM(installments.amount WHERE paid = 0)
    
    if unpaid > 0:
        return unpaid
    else:
        return loan.amount_due  # Если рассрочки нет
```

### 2. Проверка "горящего" займа

```python
def is_urgent(loan):
    # Ближайший неоплаченный платёж
    next_payment = installments.where(paid=0).order_by(due_date).first()
    
    if next_payment:
        days_left = (next_payment.due_date - today).days
        return days_left < 5
    
    return False
```

### 3. Отправка напоминания о задаче

```python
def send_task_reminder():
    # 1. Проверка рабочих часов
    if not (7 <= hour < 22):
        return
    
    # 2. Найти напоминания
    reminders = TaskReminder.where(
        sent=0, 
        reminder_time <= NOW()
    )
    
    # 3. Для каждого напоминания
    for reminder in reminders:
        # Отправить с кнопками
        keyboard = [
            ["✅ Выполнил", "⏰ Отложить"]
        ]
        send_message(text, keyboard)
        
        # Пометить отправленным
        reminder.sent = 1
        reminder.sent_at = NOW()
```

### 4. Обработка кнопки "Выполнил"

```python
def handle_callback(callback_query):
    task_id, reminder_id = parse_callback_data()
    
    # 1. Пометить задачу выполненной
    task.status = 1
    task.completed_at = NOW()
    
    # 2. Отметить напоминание как обработанное
    reminder.acknowledged = 1
    
    # 3. Удалить все будущие напоминания для этой задачи
    TaskReminder.where(task_id=task_id, sent=0).delete()
    
    # 4. Обновить сообщение
    edit_message("✅ Задача выполнена! 🎉")
```

---

## 🔄 Жизненный цикл задачи

```
1. Пользователь создаёт задачу
   ↓
2. Выбирает шаблон или кастомные напоминания
   ↓
3. Генерируются записи в task_reminders
   ↓
4. Cron (каждую минуту) проверяет напоминания
   ↓
5. Когда время наступает → отправка в Telegram
   ↓
6. Пользователь нажимает "Выполнил"
   ↓
7. Callback → task.status = 1
   ↓
8. Будущие напоминания удаляются
   ↓
9. Сообщение обновляется "Задача выполнена!"
```

### Альтернативный сценарий (игнорирование):

```
5. Отправлено напоминание
   ↓
6. Нет реакции 15 минут
   ↓
7. telegram_repeat_reminders.py отправляет повторно
   ↓
8. Снова нет реакции 15 минут
   ↓
9. Повтор (бесконечно пока не нажмёт кнопку)
   ↓
10. Только в рабочие часы (7-22)
```

---

## 🛡️ Безопасность

### Уровни защиты:

1. **Аутентификация**
   - Единый пароль (нельзя изменить)
   - 3 попытки + блокировка IP
   - Session cookie (httponly)

2. **База данных**
   - Dedicated user (не postgres)
   - Локальное подключение
   - Сильный пароль

3. **Telegram**
   - Проверка chat_id
   - Токен не в git
   - Только авторизованные callback

4. **Веб-сервер**
   - За Nginx proxy
   - Security headers
   - CSRF protection (Flask)

---

## 💾 Бэкапы

### Автоматические:
- **Когда:** Каждый день в 02:00 MSK
- **Куда:** Яндекс.Диск
- **Формат:** SQL dump + gzip (~8 KB)
- **Хранение:** 10 копий на Я.Диске, 3 локально
- **Ссылка:** https://yadi.sk/d/gVpI3Fst7J5EIw

### Восстановление:
```bash
./download_from_yandex.sh latest
gunzip mikrokredit_*.sql.gz
psql -U mikrokredit_user -d mikrokredit -h localhost < backup.sql
```

---

## 🧪 Тестирование

### Проверка компонентов:

```bash
# Health check
curl http://localhost/healthz
# {"status":"ok"}

# Веб-сервер
ps aux | grep gunicorn | grep mikrokredit

# Telegram бот
ps aux | grep telegram_bot_server

# База данных
psql -U mikrokredit_user -d mikrokredit -h localhost -c "SELECT COUNT(*) FROM tasks;"

# Cron
crontab -l
```

---

## 📝 Частые задачи

### Добавить новый шаблон напоминаний:

1. Отредактируйте `init_reminder_templates.py`
2. Добавьте в SYSTEM_TEMPLATES
3. Запустите: `python3 init_reminder_templates.py`

### Изменить рабочие часы бота:

В файлах `telegram_*.py`:
```python
BOT_WORK_HOURS_START = 7  # Начало
BOT_WORK_HOURS_END = 22    # Конец
```

### Добавить получателя в Telegram:

В файлах `telegram_*.py`:
```python
TELEGRAM_CHAT_ID = 352096813  # Замените на нужный ID
```

---

## 🐛 Troubleshooting

### Проблема: Internal Server Error

**Проверьте:**
1. Логи: `tail -50 logs/error.log`
2. PostgreSQL: `systemctl status postgresql`
3. Sequences: `./fix_sequences.sh`

### Проблема: Не работают кнопки в Telegram

**Причины:**
- Telegram бот не запущен
- Старые кнопки (> 48 часов)
- Ошибка в callback

**Решение:**
1. Проверьте процесс: `ps aux | grep telegram_bot_server`
2. Логи: `tail -20 logs/telegram_bot_fresh.log`
3. Перезапуск: `pkill -f telegram_bot_server && ./start_telegram_bot.sh`
4. Создайте НОВУЮ задачу для свежих кнопок

### Проблема: Не приходят напоминания

**Проверьте:**
1. Cron: `crontab -l`
2. Рабочие часы (7-22 MSK)
3. Логи: `tail -20 logs/telegram_tasks.log`
4. Запустите вручную: `python3 telegram_bot_tasks.py`

---

## 📚 Для следующих сессий

### Важные файлы для понимания:

1. **PROJECT_ARCHITECTURE.md** - этот файл
2. **app/models_sa.py** - структура БД
3. **web/views.py** - логика займов
4. **web/tasks_views.py** - логика задач
5. **telegram_bot_server.py** - обработка кнопок

### Ключевые концепции:

- Займы используют **installments** для рассрочки
- Задачи используют **task_reminders** для напоминаний
- Telegram бот работает в **2 режимах**: cron (отправка) + фоновый (callback)
- SQLAlchemy объекты нужно **преобразовывать в dict** перед передачей в шаблоны
- Горящие займы = **days_left < 5** от ближайшего платежа

### Потенциальные расширения:

1. REST API для мобильного приложения
2. Webhook для Telegram (вместо polling)
3. Повторяющиеся задачи (recurrence_rule)
4. Календарное представление
5. Статистика и графики
6. Экспорт данных

---

**Документ актуален на:** 09.10.2025  
**Версия проекта:** 2.0.0  
**Статус:** Production Ready

**Контакт:** Telegram @valstanbot

