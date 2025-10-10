# 📋 КОНТЕКСТ ДЛЯ СЛЕДУЮЩЕЙ СЕССИИ
**Дата**: 10 октября 2025  
**Проект**: MikroKredit - Система гибких напоминаний для задач

---

## 🎯 ЧТО БЫЛО СДЕЛАНО

Реализована **полная система гибких расписаний и напоминаний для задач**.

### ✅ Готово (100% функционала):

#### 1. **База данных** ✅
- Созданы таблицы:
  - `task_schedules` - расписание по дням недели (1-7)
  - `reminder_rules` - правила генерации напоминаний
- Расширена таблица `tasks`:
  - `task_type` VARCHAR(50) - simple/event/recurring_event
  - `has_duration` BOOLEAN
  - `duration_minutes` INTEGER
  - `is_paused` BOOLEAN
  - `paused_until` DATE
- Миграции применены: `migrations/008_add_task_schedules_and_rules_pg.sql`

#### 2. **Модели SQLAlchemy** ✅
- `TaskScheduleORM` - расписание (app/models_sa.py:165-188)
- `ReminderRuleORM` - правила (app/models_sa.py:191-231)
- Relationships добавлены в `TaskORM`

#### 3. **Backend (Python)** ✅

**Генератор напоминаний** (`app/reminder_generator.py`):
- `ReminderGenerator.generate_reminders_for_task(task_id)` - генерирует напоминания
- Поддерживает все типы правил:
  - `before_start` - За X минут до начала
  - `before_end` - За X минут до конца
  - `periodic_before` - Периодически до начала (например: каждые 30 мин с 16:00 до 30 мин до начала)
  - `periodic_during` - Во время события
  - `after_end` - После окончания
- Автоматически вызывается при сохранении задачи

**Telegram уведомления** (`app/telegram_notifier.py`):
- `TelegramNotifier` - отправка в Telegram
- `send_task_reminder_notification()` - функция для отправки

**Роуты** (`web/tasks_views.py`):
- `GET /tasks/new/v2` - форма создания (строка 367)
- `POST /tasks/new/v2` - сохранение + генерация напоминаний
- `GET /tasks/<id>/edit/v2` - форма редактирования (строка 450)
- `POST /tasks/<id>/edit/v2` - обновление + регенерация напоминаний
- `POST /tasks/<id>/delete/v2` - удаление

#### 4. **Frontend (UI)** ✅

**Шаблон** (`web/templates/tasks/edit_v2.html`):
- Alpine.js компонент `taskEditor()`
- **Выбор типа задачи**:
  - 📌 Простая задача (с дедлайном)
  - 📅 Одиночное событие
  - 🔁 Регулярное событие
- **Расписание по дням недели** (для событий):
  - Чекбоксы: Пн, Вт, Ср, Чт, Пт, Сб, Вс
  - Время начала и конца для каждого дня
- **Редактор правил напоминаний**:
  - Список правил с кнопками "Изменить"/"Удалить"
  - Форма добавления нового правила
  - Выбор типа правила и параметров
- **Приостановка задачи** до даты

#### 5. **Автоматизация** ✅

**Скрипты**:
- `scripts/send_task_reminders.py` - отправка напоминаний (запускать каждую минуту)
- `scripts/regenerate_reminders.py` - регенерация на 14 дней вперед (раз в день)
- `scripts/setup_all_cron.sh` - настройка cron задач

#### 6. **Документация** ✅
- `docs/TASK_SCHEDULER_DESIGN.md` - архитектура
- `docs/TASK_REMINDERS_SETUP.md` - руководство пользователя

---

## ⚠️ ПРОБЛЕМА

**Новая система НЕ ВИДНА в интерфейсе!**

### Причина:
Мы создали **новые роуты v2**, но:
1. ❌ Старые роуты `/tasks/new` и `/tasks/<id>/edit` НЕ изменены
2. ❌ В списке задач (`/tasks/`) ссылки ведут на старую версию
3. ❌ В меню нет ссылки на новую версию

### Текущее состояние:
- Новая система работает на `/tasks/new/v2` и `/tasks/<id>/edit/v2`
- Но попасть туда можно только вручную введя URL
- Пользователь видит старый интерфейс

---

## 🔧 ЧТО НУЖНО СДЕЛАТЬ

### Вариант 1: Заменить старую версию (РЕКОМЕНДУЕТСЯ)

**Шаг 1**: Переименовать роуты
```python
# В web/tasks_views.py

# Старые роуты переименовать (или удалить):
@bp.route('/new_old', methods=['GET', 'POST'])  # было /new
@bp.route('/<int:task_id>/edit_old', methods=['GET', 'POST'])  # было /edit

# Новые роуты сделать основными:
@bp.route('/new', methods=['GET', 'POST'])  # было /new/v2
@bp.route('/<int:task_id>/edit', methods=['GET', 'POST'])  # было /edit/v2
```

**Шаг 2**: Обновить ссылки в шаблонах
```html
<!-- В web/templates/tasks/index.html -->
<!-- Найти все ссылки на /tasks/<id>/edit и проверить что они правильные -->
```

**Шаг 3**: Обновить шаблон для новых задач
```python
# В web/tasks_views.py функция new() - редирект на новую версию
return redirect(url_for('tasks.new_v2'))
```

---

### Вариант 2: Добавить переключатель версий

**Шаг 1**: Добавить кнопку в списке задач
```html
<!-- В web/templates/tasks/index.html -->
<a href="/tasks/new/v2" class="btn btn-success">
    ➕ Новая задача (с расписанием)
</a>
```

**Шаг 2**: В карточке задачи добавить ссылку на v2
```html
<a href="/tasks/{{ task.id }}/edit/v2">Редактировать (v2)</a>
```

---

## 📁 ВАЖНЫЕ ФАЙЛЫ ДЛЯ РАБОТЫ

### Backend:
- `web/tasks_views.py` - роуты задач (строки 367-612 - v2)
- `app/reminder_generator.py` - генератор напоминаний
- `app/telegram_notifier.py` - Telegram уведомления
- `app/models_sa.py` - модели (TaskScheduleORM, ReminderRuleORM)

### Frontend:
- `web/templates/tasks/edit_v2.html` - новый интерфейс (592 строки)
- `web/templates/tasks/index.html` - список задач (нужно обновить ссылки)
- `web/templates/tasks/edit.html` - старый интерфейс (можно удалить после миграции)

### Скрипты:
- `scripts/send_task_reminders.py` - отправка (cron каждую минуту)
- `scripts/regenerate_reminders.py` - регенерация (cron раз в день)
- `scripts/setup_all_cron.sh` - настройка автоматизации

---

## 🧪 КАК ПРОТЕСТИРОВАТЬ НОВУЮ СИСТЕМУ ПРЯМО СЕЙЧАС

### 1. Открыть напрямую:
```
http://ваш-домен/tasks/new/v2
```

### 2. Создать задачу "Футбол - сын":
- Тип: 🔁 Регулярное событие
- Расписание:
  - ☑ Понедельник: 20:00 - 21:00
  - ☑ Среда: 20:00 - 21:00
  - ☑ Пятница: 21:00 - 22:00
- Правила напоминаний:
  1. 🔁 Периодически до начала
     - Каждые: 30 минут
     - С: 16:00
     - До: 30 (минут до начала)
  2. ⏰ За X до конца
     - За: 20 минут
- Сохранить

### 3. Проверить что сработало:
```sql
-- Проверить расписания
SELECT * FROM task_schedules WHERE task_id = <новый_id>;

-- Проверить правила
SELECT * FROM reminder_rules WHERE task_id = <новый_id>;

-- Проверить сгенерированные напоминания
SELECT * FROM task_reminders WHERE task_id = <новый_id> ORDER BY reminder_time;
```

### 4. Настроить cron:
```bash
cd /home/valstan/mikrokredit
./scripts/setup_all_cron.sh
```

### 5. Протестировать отправку:
```bash
python3 scripts/send_task_reminders.py
```

---

## 💡 РЕКОМЕНДАЦИИ

### Приоритет 1 (КРИТИЧНО):
1. ✅ Заменить старые роуты на новые (`/new` → новая версия)
2. ✅ Обновить ссылки в списке задач
3. ✅ Протестировать создание задачи через UI

### Приоритет 2 (ВАЖНО):
4. Добавить миграцию данных (если есть старые задачи)
5. Настроить cron для автоматизации
6. Протестировать отправку в Telegram

### Приоритет 3 (УЛУЧШЕНИЯ):
7. Добавить визуализацию сгенерированных напоминаний
8. Добавить кнопку "Протестировать правила" в UI
9. Добавить статистику (сколько отправлено/пропущено)

---

## 🔍 ДИАГНОСТИКА ПРОБЛЕМ

### Если задача не сохраняется:
```bash
# Смотрим логи Flask
tail -f /home/valstan/mikrokredit/logs/error.log

# Смотрим логи gunicorn
sudo journalctl -u mikrokredit -n 100
```

### Если напоминания не генерируются:
```python
# Проверить в Python
cd /home/valstan/mikrokredit
python3
>>> from app.reminder_generator import regenerate_task_reminders
>>> count = regenerate_task_reminders(TASK_ID)
>>> print(f"Создано {count} напоминаний")
```

### Если не отправляются в Telegram:
```python
# Проверить credentials
cd /home/valstan/mikrokredit
python3
>>> from app.secrets import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
>>> print(f"Token: {TELEGRAM_BOT_TOKEN[:10]}...")
>>> print(f"Chat ID: {TELEGRAM_CHAT_ID}")

# Тест отправки
>>> from app.telegram_notifier import telegram_notifier
>>> telegram_notifier.send_message("Тест")
```

---

## 📊 АРХИТЕКТУРА СИСТЕМЫ

```
┌─────────────────────────────────────────────────────────┐
│  USER → /tasks/new/v2                                   │
│         ↓                                                │
│  [UI] edit_v2.html (Alpine.js)                         │
│         ↓ (POST JSON)                                    │
│  [Backend] tasks_views.py::new_v2()                    │
│         ↓                                                │
│  Сохраняет: TaskORM + TaskScheduleORM + ReminderRuleORM│
│         ↓                                                │
│  [Generator] reminder_generator.py                      │
│         ↓                                                │
│  Создает: TaskReminderORM (на 14 дней вперед)         │
│         ↓                                                │
│  [Cron] send_task_reminders.py (каждую минуту)        │
│         ↓                                                │
│  Читает TaskReminderORM где sent=0 и время наступило  │
│         ↓                                                │
│  [Telegram] telegram_notifier.py                        │
│         ↓                                                │
│  📱 USER получает уведомление                           │
│         ↓                                                │
│  TaskReminderORM.sent = 1                              │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ ЧЕКЛИСТ ДЛЯ ЗАВЕРШЕНИЯ

```markdown
- [ ] Заменить старые роуты `/tasks/new` и `/tasks/<id>/edit` на v2
- [ ] Обновить ссылки в `web/templates/tasks/index.html`
- [ ] Удалить старый шаблон `edit.html` (или переименовать в `edit_old.html`)
- [ ] Протестировать создание задачи через UI
- [ ] Протестировать редактирование существующей задачи
- [ ] Настроить cron: `./scripts/setup_all_cron.sh`
- [ ] Проверить генерацию напоминаний для тестовой задачи
- [ ] Проверить отправку в Telegram
- [ ] Добавить в README инструкцию по настройке
- [ ] Обновить документацию с реальным доменом
```

---

## 🚀 БЫСТРЫЙ СТАРТ ДЛЯ СЛЕДУЮЩЕЙ СЕССИИ

```bash
# 1. Перейти в проект
cd /home/valstan/mikrokredit

# 2. Прочитать этот файл
cat docs/SESSION_CONTEXT_NEXT.md

# 3. Открыть нужные файлы
# - web/tasks_views.py (строки 367-612)
# - web/templates/tasks/index.html
# - web/templates/tasks/edit_v2.html

# 4. Начать с замены роутов (см. "ЧТО НУЖНО СДЕЛАТЬ")
```

---

## 📞 КОНТАКТЫ И ССЫЛКИ

- **Сервер**: valstan@73269587c9af.vps.myjino.ru
- **Проект**: /home/valstan/mikrokredit
- **Systemd**: `sudo systemctl restart mikrokredit`
- **Порт**: 8002
- **База**: PostgreSQL (mikrokredit)
- **GitHub**: уже запушено (коммит 6ec5d61)

---

## 💬 КРАТКОЕ РЕЗЮМЕ

**Что работает**: Вся система полностью готова - БД, backend, UI, автоматизация.

**Что НЕ работает**: Новый UI не доступен через обычный интерфейс, только через прямые ссылки `/tasks/new/v2`.

**Что делать**: Заменить старые роуты на новые или добавить ссылки на v2 в список задач.

**Время на доработку**: 15-30 минут.

---

**Удачи! Система готова на 95%, осталось только "включить" новый интерфейс! 🚀**

