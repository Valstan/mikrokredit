# 📖 Записная книжка Валентина - Полная документация

**Версия:** 2.0.0  
**Дата:** 09.10.2025  
**Статус:** Production Ready

---

## 🎯 Содержание

1. [Быстрый старт](#быстрый-старт)
2. [Архитектура системы](#архитектура-системы)
3. [Модули и функции](#модули-и-функции)
4. [Telegram интеграция](#telegram-интеграция)
5. [Управление системой](#управление-системой)
6. [Troubleshooting](#troubleshooting)

---

## 🚀 Быстрый старт

### Доступ к системе:

```
URL:     http://73269587c9af.vps.myjino.ru/
Пароль:  [см. .env файл]
```

**Первый вход:**
1. Откройте URL
2. Введите пароль (3 попытки)
3. Увидите Dashboard со статистикой

### Основные действия:

**Добавить займ:**
- Dashboard → "💳 Добавить займ"
- Заполните данные
- Добавьте график платежей (опционально)

**Создать задачу:**
- Dashboard → "✅ Добавить задачу"
- Выберите важность и срок
- Выберите шаблон напоминаний или добавьте свои
- Получите уведомления в Telegram!

---

## 🏗️ Архитектура системы

### Структура проекта:

```
mikrokredit/
├── app/                    # Бизнес-логика
│   ├── auth.py            # Аутентификация
│   ├── db_sa.py           # SQLAlchemy
│   ├── models_sa.py       # ORM модели (9 таблиц)
│   └── config.py          # Конфигурация
│
├── web/                    # Flask приложение
│   ├── views.py           # Займы + Dashboard
│   ├── auth_views.py      # Вход/выход
│   ├── tasks_views.py     # Задачи
│   └── templates/         # HTML шаблоны
│
├── Telegram боты:
│   ├── telegram_notifier.py          # Горящие займы
│   ├── telegram_bot_tasks.py         # Напоминания о задачах
│   ├── telegram_repeat_reminders.py  # Повторы
│   └── telegram_bot_server.py        # Callback (фоновый)
│
├── Скрипты:
│   ├── start_service.sh              # Запуск веб
│   ├── stop_service.sh               # Остановка
│   ├── start_telegram_bot.sh         # Запуск бота
│   ├── backup_to_yandex.sh           # Бэкап
│   ├── download_from_yandex.sh       # Скачать бэкап
│   └── fix_sequences.sh              # Исправить sequences
│
└── logs/                   # Логи всех сервисов
```

### Технологии:

- **Backend:** Python 3.12, Flask 3.1, SQLAlchemy 2.0
- **Database:** PostgreSQL 18.0 (mikrokredit)
- **Cache:** Redis 7.4
- **Frontend:** Bootstrap 5.3, Alpine.js
- **Telegram:** python-telegram-bot 20.8
- **Server:** Gunicorn 21.2, Nginx 1.28

### Deployment:

```
Internet → Nginx:80 → Gunicorn:8002 → Flask App
                                         ↓
                                   PostgreSQL:5432
                                         ↓
                                   Redis:6379
                                         ↑
                               Telegram Bot Server
                                         ↑
                                   Telegram API
                                         ↑
                                   User (Telegram)
```

---

## 🗄️ База данных

### Подключение:
```
Host:     localhost:5432
Database: mikrokredit
User:     mikrokredit_user
Password: [см. .env файл]
```

### Таблицы:

#### Займы (4 таблицы):

**1. loans** - микрозаймы
- id, org_name, website
- loan_date, due_date, amount_borrowed, amount_due
- is_paid, risky_org, notes, payment_methods

**2. installments** - платежи по рассрочке
- id, loan_id, due_date, amount
- paid, paid_date

#### Задачи (5 таблиц):

**3. tasks** - задачи
- id, title, description
- status (0=не выполнено, 1=выполнено)
- importance (1=важная, 2=нужная, 3=хотелось бы)
- due_date, category_id
- is_recurring, recurrence_rule

**4. task_categories** - категории
- id, name, color, icon

**5. subtasks** - подзадачи
- id, task_id, title, completed, order

**6. task_reminders** - напоминания
- id, task_id, reminder_time
- sent, sent_at, telegram_message_id
- acknowledged, acknowledged_at

**7. reminder_templates** - шаблоны
- id, name, description, rules (JSON)
- is_system (0/1)

---

## 💳 Модуль МикроКредит

### Функционал:
- Учёт займов с графиком платежей
- Автоматический расчёт долга
- Уведомления о горящих кредитах
- Статистика

### Логика расчёта долга:

```python
# Для каждого займа:
unpaid_total = SUM(installments.amount WHERE paid = 0)

if unpaid_total > 0:
    debt = unpaid_total  # Есть рассрочка
else:
    debt = loan.amount_due  # Нет рассрочки

# Займ оплачен если unpaid_total == 0
```

### Критерий "горящий":

```python
# Берётся ближайший неоплаченный installment
next_payment = installments.where(paid=0).order_by(due_date).first()

if next_payment:
    days_left = (next_payment.due_date - today).days
    is_urgent = days_left < 5  # Горящий если < 5 дней
```

### Статистика:
- **Всего:** COUNT(loans)
- **Горящие:** COUNT(loans с days_left < 5)
- **Долг:** SUM(unpaid_total) по всем займам

---

## ✅ Модуль Органайзер задач

### Функционал:
- Создание/редактирование/удаление задач
- 3 уровня важности (🔴🟡⚪)
- Категории с цветовой кодировкой
- Подзадачи (чеклисты)
- Гибкая система напоминаний
- Фильтры и сортировка

### Важность задач:

| Уровень | Иконка | Описание |
|---------|--------|----------|
| 1 | 🔴 Важная | Критические, с дедлайном |
| 2 | 🟡 Нужная | Плановые задачи |
| 3 | ⚪ Хотелось бы | Желательные |

### Шаблоны напоминаний:

**1. За 1 день до срока**
- Одно напоминание за 24 часа

**2. За день и в день**
- За 24 часа
- Утром в день дедлайна

**3. Интенсивные** ⭐ Рекомендуется
- За 24 часа
- За 1 час
- В момент дедлайна

**4. Очень интенсивные**
- За 2 дня, день, 3 часа, час, момент

**5. Только в день дедлайна**
- Утром в день выполнения

### Кастомные напоминания:

Можно добавить любые точки времени вручную:
```
2025-10-15 09:00
2025-10-15 14:00
2025-10-15 18:00
```

---

## 📱 Telegram интеграция

### Конфигурация:
```
Бот:        @valstanbot
Token:      [см. .env файл - TELEGRAM_BOT_TOKEN]
Chat ID:    [см. .env файл - TELEGRAM_CHAT_ID]
```

### Компоненты:

#### 1. telegram_notifier.py
**Назначение:** Уведомления о горящих займах  
**Расписание:** 10:00 и 20:00 MSK

**Формат:**
```
🔥 ГОРЯЩИЕ КРЕДИТЫ 🔥

📊 Всего: 5 кредитов
💰 Сумма: 123,456 ₽

🔴 ПРОСРОЧЕН МаниМен (13 дн. назад)
💳 Сумма: 5,056 ₽
🔗 Перейти в личный кабинет
```

#### 2. telegram_bot_tasks.py
**Назначение:** Отправка напоминаний о задачах  
**Расписание:** Каждую минуту (cron)

**Формат:**
```
🔴 НАПОМИНАНИЕ О ЗАДАЧЕ

Оплатить счёт

📌 Важность: Важная
📅 Срок: 2025-10-15 18:00

[✅ Выполнил]  [⏰ Отложить]
```

#### 3. telegram_repeat_reminders.py
**Назначение:** Повторные напоминания  
**Расписание:** Каждые 15 минут

**Логика:**
- Если не нажата кнопка → повтор через 15 мин
- До тех пор пока не отреагирует
- Только в рабочие часы (7-22)

#### 4. telegram_bot_server.py
**Назначение:** Обработка callback кнопок  
**Режим:** Фоновый процесс (постоянно)

**Действия:**
- **"✅ Выполнил"** → task.status = 1, все будущие напоминания удаляются
- **"⏰ Отложить"** → открывается задача в браузере

### Рабочие часы:
**7:00 - 22:00 MSK**

Ночью уведомления не отправляются, накапливаются до утра.

---

## 🔐 Аутентификация

### Параметры:
- **Пароль:** [см. .env - AUTH_PASSWORD] (фиксированный)
- **Попытки:** 3
- **Блокировка:** 5 минут по IP
- **Cookie:** 30 дней

### Процесс входа:

```
1. Пользователь открывает сайт
   ↓
2. Редирект на /auth/login
   ↓
3. Вводит пароль
   ↓
4. Если правильный → session['authenticated'] = True
   ↓
5. Cookie на 30 дней
   ↓
6. Доступ ко всем разделам
```

### Блокировка:

```
Неверный пароль (1 раз) → осталось 2 попытки
Неверный пароль (2 раз) → осталось 1 попытка
Неверный пароль (3 раз) → блокировка IP на 5 минут
```

- Блокировка только для вашего IP
- Обратный отсчёт на экране
- Автоматическая разблокировка

---

## 🔄 Автоматизация (Cron)

### Расписание:

```bash
# Напоминания о задачах
* * * * *           telegram_bot_tasks.py

# Повторные напоминания (если нет реакции)
*/15 * * * *        telegram_repeat_reminders.py

# Горящие займы
0 10,20 * * *       telegram_notifier.py

# Бэкап на Яндекс.Диск
0 2 * * *           backup_to_yandex.sh
```

### Проверка cron:
```bash
crontab -l                           # Список задач
grep CRON /var/log/syslog | tail    # Логи запусков
```

---

## 💾 Бэкапы

### Автоматические:
- **Когда:** Ежедневно в 02:00 MSK
- **Куда:** Яндекс.Диск (папка /МикроКредит_Backups)
- **Формат:** SQL dump + gzip (~8 KB)
- **Хранение:** 10 на Я.Диске, 3 локально
- **Ссылка:** https://yadi.sk/d/gVpI3Fst7J5EIw

### Команды:

```bash
# Создать бэкап сейчас
./backup_to_yandex.sh

# Список бэкапов на Я.Диске
./download_from_yandex.sh

# Скачать последний
./download_from_yandex.sh latest

# Восстановление
gunzip mikrokredit_*.sql.gz
export PGPASSWORD="[см. .env - DB_PASSWORD]"
psql -U mikrokredit_user -d mikrokredit -h localhost < backup.sql
```

---

## 🛠️ Управление системой

### Запуск:

```bash
cd /home/valstan/mikrokredit

# Веб-сервер
./start_service.sh

# Telegram бот (callback)
./start_telegram_bot.sh
```

### Остановка:

```bash
# Веб-сервер
./stop_service.sh

# Telegram бот
pkill -f telegram_bot_server.py
```

### Проверка:

```bash
# Health check
curl http://localhost/healthz

# Процессы
ps aux | grep -E "(gunicorn|telegram)" | grep -v grep

# Логи
tail -f logs/error.log              # Ошибки веб-приложения
tail -f logs/telegram_tasks.log     # Напоминания о задачах
tail -f logs/telegram_bot_fresh.log # Telegram бот (callback)
tail -f logs/backup.log             # Бэкапы
```

---

## 📊 Работа с займами

### Добавление займа:

1. Займы → "Добавить займ"
2. Заполните:
   - Банк (название)
   - Сайт (URL личного кабинета)
   - Дата оформления
   - Дата возврата
   - Сумма взята
3. Сохраните

### График платежей:

После создания займа:
1. Откройте займ для редактирования
2. Раздел "График платежей"
3. Добавьте каждый платёж:
   - Дата платежа
   - Сумма
4. "Добавить платеж"

**Важно:** Система автоматически:
- Суммирует общую сумму к возврату
- Вычисляет остаток долга
- Определяет ближайший платёж
- Помечает горящие (< 5 дней)

### Статистика:

Dashboard показывает:
- **Всего займов:** COUNT(loans)
- **Горящие:** займы с ближайшим платежом < 5 дней
- **Долг:** сумма всех неоплаченных installments

---

## ✅ Работа с задачами

### Создание задачи:

1. Задачи → "Добавить задачу"
2. Заполните:
   - **Название** (обязательно)
   - **Важность:** Важная/Нужная/Хотелось бы
   - **Срок:** дата и время
   - **Категория** (опционально)
   - **Описание** (опционально)
3. Добавьте подзадачи (опционально)
4. Выберите шаблон напоминаний ИЛИ добавьте свои
5. Сохраните

### Подзадачи (чеклисты):

Используйте для разбивки большой задачи:

```
Задача: Организовать день рождения

Подзадачи:
├─ ⬜ Забронировать ресторан
├─ ⬜ Заказать торт
├─ ⬜ Купить подарок
└─ ⬜ Пригласить гостей

Прогресс: 0/4
```

### Категории:

**Управление:**
- Задачи → "Управление категориями"
- Добавьте: название + цвет

**Примеры:**
- 🔴 Работа (#dc3545)
- 🟢 Личное (#28a745)
- 🔵 Семья (#007bff)

### Фильтры:

- Все задачи
- На сегодня
- Просроченные
- Важные
- Выполненные
- По категориям

---

## 📱 Telegram уведомления

### Типы сообщений:

#### Напоминание о задаче:
```
🔴 НАПОМИНАНИЕ О ЗАДАЧЕ

Название задачи

Описание

📌 Важность: Важная
📅 Срок: 2025-10-15 18:00

[✅ Выполнил]  [⏰ Отложить]
```

#### Повторное напоминание:
```
🔴 🔔 ПОВТОРНОЕ НАПОМИНАНИЕ

Название задачи

⏰ Первое было: 10:00
💡 Следующее через 15 минут

[✅ Выполнил]  [⏰ Отложить]
```

#### Горящие займы:
```
🔥 ГОРЯЩИЕ КРЕДИТЫ 🔥

📊 Всего: 5 кредитов
💰 Сумма: 123,456 ₽

🔴 ПРОСРОЧЕН МаниМен (13 дн.)
💳 Сумма: 5,056 ₽
🔗 Перейти в личный кабинет
```

### Кнопки в Telegram:

**"✅ Выполнил":**
- Задача → status = 1 (выполнено)
- Все будущие напоминания удаляются
- Сообщение обновляется: "Задача выполнена! 🎉"

**"⏰ Отложить":**
- Напоминание отмечается как обработанное
- Открывается ссылка на задачу для редактирования

### Рабочие часы:

**7:00 - 22:00 MSK**

- Уведомления отправляются только в это время
- Ночью бот не беспокоит
- Накопленные напоминания придут в 7:00

---

## 🔧 Конфигурация

### Секреты:

**НЕ коммитить в Git:**
- Auth password: [см. .env - AUTH_PASSWORD]
- Telegram token: [см. .env файл - TELEGRAM_BOT_TOKEN]
- DB password: [см. .env - DB_PASSWORD]
- Yandex token: [см. .env файл - YANDEX_DISK_TOKEN]

### Изменяемые параметры:

**Рабочие часы бота:**
```python
# В файлах telegram_*.py
BOT_WORK_HOURS_START = 7   # Начало
BOT_WORK_HOURS_END = 22    # Конец
```

**Интервал повторов:**
```python
# В telegram_repeat_reminders.py
REPEAT_INTERVAL_MINUTES = 15
```

**Критерий горящего займа:**
```python
# В web/views.py
urgent = days_left < 5  # Изменить на нужное
```

---

## 🐛 Troubleshooting

### Проблема: Internal Server Error

**Симптомы:** Белая страница с ошибкой

**Решение:**
```bash
# 1. Проверьте логи
tail -50 logs/error.log

# 2. Проверьте PostgreSQL
systemctl status postgresql

# 3. Исправьте sequences (если ошибка duplicate key)
./fix_sequences.sh

# 4. Перезапустите
./stop_service.sh && ./start_service.sh
```

### Проблема: Не работают кнопки в Telegram

**Причины:**
- Telegram бот не запущен
- Старые кнопки (callback истёк)
- Ошибка в обработчике

**Решение:**
```bash
# 1. Проверьте процесс
ps aux | grep telegram_bot_server

# 2. Логи
tail -20 logs/telegram_bot_fresh.log

# 3. Перезапуск
pkill -f telegram_bot_server.py
./start_telegram_bot.sh

# 4. Создайте НОВУЮ задачу для свежих кнопок
```

### Проблема: Не приходят напоминания

**Проверьте:**
```bash
# 1. Cron настроен?
crontab -l

# 2. Рабочие часы (7-22 MSK)?
date +%H

# 3. Есть ли напоминания в БД?
export PGPASSWORD="[см. .env - DB_PASSWORD]"
psql -U mikrokredit_user -d mikrokredit -h localhost -c \
  "SELECT * FROM task_reminders WHERE sent = 0;"

# 4. Запустите вручную
python3 telegram_bot_tasks.py
```

### Проблема: Не сохраняется платёж

**Решение:**
- Формы теперь обычные POST (без HTMX)
- Проверьте логи: `tail -20 logs/error.log`
- Убедитесь что заполнены дата И сумма

### Проблема: Duplicate key (sequences)

**Ошибка:**
```
duplicate key value violates unique constraint "loans_pkey"
```

**Решение:**
```bash
./fix_sequences.sh
```

Скрипт автоматически синхронизирует все sequences.

---

## 📈 Частые задачи

### Добавить категорию задач:

1. Задачи → "Управление категориями"
2. Введите название и выберите цвет
3. "Добавить"

### Добавить свой шаблон напоминаний:

1. Отредактируйте `init_reminder_templates.py`
2. Добавьте в SYSTEM_TEMPLATES
3. Запустите: `python3 init_reminder_templates.py`

### Посмотреть статистику:

```sql
-- Статистика по задачам
SELECT 
    importance,
    COUNT(*) as total,
    SUM(CASE WHEN status = 0 THEN 1 ELSE 0 END) as pending,
    SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) as completed
FROM tasks
GROUP BY importance;

-- Горящие займы
SELECT 
    l.org_name,
    MIN(i.due_date) as next_payment,
    SUM(i.amount) FILTER (WHERE i.paid = 0) as debt
FROM loans l
LEFT JOIN installments i ON i.loan_id = l.id
WHERE l.is_paid = 0
GROUP BY l.id, l.org_name
HAVING MIN(i.due_date) < CURRENT_DATE + INTERVAL '5 days';
```

---

## 🔒 Безопасность

### Уровни защиты:

1. **Аутентификация**
   - Единый пароль
   - Блокировка брутфорса (3 попытки)
   - Защита по IP
   - Безопасная сессия (httponly cookie)

2. **База данных**
   - Dedicated user (не postgres)
   - Локальное подключение только
   - Сильный пароль
   - Connection pooling с pre-ping

3. **Telegram**
   - Проверка chat_id
   - Токен не в git (в .gitignore)
   - Только авторизованные callback

4. **Веб-сервер**
   - За Nginx reverse proxy
   - Security headers
   - CSRF protection (Flask)
   - ProxyFix для правильного IP

---

## 💡 Советы по использованию

### Ежедневная работа:

**Утром:**
1. Откройте Dashboard
2. Посмотрите задачи на сегодня
3. Проверьте горящие займы
4. Расставьте приоритеты

**В течение дня:**
- Реагируйте на Telegram уведомления
- Нажимайте кнопки "Выполнил"/"Отложить"
- Не игнорируйте - будут повторы

**Вечером:**
- Отметьте выполненное
- Добавьте задачи на завтра
- Проверьте платежи

### Организация:

**Задачи:**
- Важные → для дедлайнов
- Нужные → для плановых дел
- Хотелось бы → когда будет время
- Используйте подзадачи для проектов
- Категории для разных сфер жизни

**Напоминания:**
- "Интенсивные" для важных задач
- "За день и в день" для обычных
- Кастомные для особых случаев

---

## 🎯 Алгоритмы работы

### Жизненный цикл задачи:

```
1. Создание задачи
   ↓
2. Выбор шаблона напоминаний
   ↓
3. Генерация task_reminders
   ↓
4. Cron проверка (каждую минуту)
   ↓
5. Время наступило → отправка в Telegram
   ↓
6. Пользователь нажимает "Выполнил"
   ↓
7. Callback → task.status = 1
   ↓
8. Удаление будущих напоминаний
   ↓
9. Обновление сообщения "Выполнена!"
```

### Сценарий с игнорированием:

```
1. Отправлено напоминание
   ↓
2. Нет реакции 15 минут
   ↓
3. Повторное напоминание
   ↓
4. Снова нет реакции 15 минут
   ↓
5. Ещё повтор (цикл до реакции)
   ↓
6. Только в рабочие часы (7-22)
```

---

## 📚 Конфигурационные файлы

### База данных:
```
Host:     localhost:5432
Database: mikrokredit
User:     mikrokredit_user
Password: [см. .env файл]
```

### Gunicorn (gunicorn.conf.py):
```python
bind = "127.0.0.1:8002"
workers = 4
timeout = 30
pool_size = 10
max_overflow = 20
pool_pre_ping = True  # Решает SSL SYSCALL errors
```

### Nginx (nginx.conf):
```nginx
location / {
    proxy_pass http://127.0.0.1:8002;
    # Headers для правильного IP
}
```

---

## 🔍 Диагностика

### Проверка всех компонентов:

```bash
# === СЕРВИСЫ ===
systemctl status postgresql nginx redis-server

# === ПРОЦЕССЫ ===
ps aux | grep gunicorn | grep mikrokredit
ps aux | grep telegram_bot_server

# === БАЗА ДАННЫХ ===
export PGPASSWORD="[см. .env - DB_PASSWORD]"
psql -U mikrokredit_user -d mikrokredit -h localhost -c "\dt"

# === CRON ===
crontab -l

# === ЛОГИ ===
ls -lh logs/

# === ДИСК ===
df -h /
du -sh backups/ logs/

# === HEALTH ===
curl http://localhost/healthz
```

---

## 🚨 Критические команды

### При падении сервера:

```bash
# Полная перезагрузка
./stop_service.sh
pkill -f telegram_bot_server.py
sleep 2
./start_service.sh
./start_telegram_bot.sh

# Проверка
curl http://localhost/healthz
ps aux | grep -E "(gunicorn|telegram)"
```

### При проблемах с БД:

```bash
# Проверка подключения
export PGPASSWORD="[см. .env - DB_PASSWORD]"
psql -U mikrokredit_user -d mikrokredit -h localhost -c "SELECT 1;"

# Исправление sequences
./fix_sequences.sh

# Перезапуск PostgreSQL (если нужно)
sudo systemctl restart postgresql
```

### Экстренное восстановление:

```bash
# Скачать последний бэкап
./download_from_yandex.sh latest

# Восстановить
gunzip mikrokredit_*.sql.gz
export PGPASSWORD="[см. .env - DB_PASSWORD]"
psql -U mikrokredit_user -d mikrokredit -h localhost < backup.sql

# Исправить sequences
./fix_sequences.sh

# Перезапустить
./stop_service.sh && ./start_service.sh
```

---

## 📞 Контакты и ссылки

**Доступ:**
- Веб: http://73269587c9af.vps.myjino.ru/
- GitHub: github.com/Valstan/mikrokredit
- Бэкапы: https://yadi.sk/d/gVpI3Fst7J5EIw

**Telegram:**
- Бот: @valstanbot
- Chat ID: [см. .env файл - TELEGRAM_CHAT_ID]

**Поддержка:**
- Вся информация в этом файле
- Для технических деталей: PROJECT_ARCHITECTURE.md (в docs/)

---

**Последнее обновление:** 09.10.2025  
**Версия:** 2.0.0  
**Статус:** ✅ Production Ready

**Приятной работы!** 🎯

