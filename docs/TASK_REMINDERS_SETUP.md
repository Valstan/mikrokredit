# 🔔 Настройка системы напоминаний для задач

## 📖 Обзор

Система автоматических напоминаний для задач с гибким расписанием и правилами.

### Компоненты:

1. **ReminderGenerator** - генерирует конкретные напоминания из правил
2. **TelegramNotifier** - отправляет уведомления в Telegram
3. **Cron задачи** - автоматизация

---

## 🚀 Быстрый старт

### 1. Создайте задачу с расписанием

```
http://ваш-домен/tasks/new
```

Выберите:
- **Тип**: Регулярное событие
- **Расписание**: Понедельник, Среда, Пятница с 20:00 до 21:00
- **Правила**:
  - Периодически до начала: каждые 30 мин с 16:00 до 30 мин до начала
  - За 20 минут до конца

### 2. Настройте cron задачи

```bash
cd /home/valstan/mikrokredit
./scripts/setup_all_cron.sh
```

Это установит:
- ✅ Отправка напоминаний: **каждую минуту**
- ✅ Регенерация: **каждый день в 00:00**

### 3. Проверьте что всё работает

```bash
# Тест отправки напоминаний
python3 scripts/send_task_reminders.py

# Тест регенерации
python3 scripts/regenerate_reminders.py
```

---

## 📊 Как это работает

### Шаг 1: Создание задачи
Пользователь создает задачу через UI `/tasks/new`:
- Указывает расписание (дни недели, время)
- Настраивает правила напоминаний

### Шаг 2: Генерация напоминаний
При сохранении задачи:
```python
regenerate_task_reminders(task_id)
```
- Читает правила из `reminder_rules`
- Читает расписание из `task_schedules`
- Создает записи в `task_reminders` на 14 дней вперед

### Шаг 3: Отправка
Каждую минуту cron запускает `send_task_reminders.py`:
- Проверяет `task_reminders` где `sent=0` и время наступило
- Отправляет в Telegram через `telegram_notifier`
- Помечает как отправленное (`sent=1`)

### Шаг 4: Регенерация
Каждый день в 00:00 cron запускает `regenerate_reminders.py`:
- Обновляет напоминания для всех активных задач
- Удаляет старые неотправленные
- Генерирует новые на следующие 14 дней

---

## 🎯 Примеры правил

### 1. Простая задача с дедлайном

```json
{
  "task_type": "simple",
  "due_date": "2025-10-15 18:00",
  "reminder_rules": [
    {"rule_type": "before_start", "offset_minutes": 1440},  // За 1 день
    {"rule_type": "before_start", "offset_minutes": 60}     // За 1 час
  ]
}
```

**Результат**: 2 напоминания
- 14.10.2025 в 18:00
- 15.10.2025 в 17:00

---

### 2. Футбол (из ТЗ)

```json
{
  "task_type": "recurring_event",
  "schedules": [
    {"day_of_week": 1, "start_time": "20:00", "end_time": "21:00"},
    {"day_of_week": 3, "start_time": "20:00", "end_time": "21:00"},
    {"day_of_week": 5, "start_time": "21:00", "end_time": "22:00"}
  ],
  "reminder_rules": [
    {
      "rule_type": "periodic_before",
      "interval_minutes": 30,
      "start_from": "16:00",
      "stop_at": "30"
    },
    {
      "rule_type": "before_end",
      "offset_minutes": 20
    }
  ]
}
```

**Результат для понедельника**:
- 16:00, 16:30, 17:00, 17:30, 18:00, 18:30, 19:00, 19:30 (каждые 30 мин)
- 20:40 (за 20 мин до конца)

**Результат для пятницы**:
- 16:00, 16:30, 17:00, 17:30, 18:00, 18:30, 19:00, 19:30, 20:00, 20:30
- 21:40 (за 20 мин до конца)

---

### 3. Ежедневная проверка почты

```json
{
  "task_type": "recurring_event",
  "schedules": [
    {"day_of_week": 1, "start_time": "09:00"},
    {"day_of_week": 2, "start_time": "09:00"},
    {"day_of_week": 3, "start_time": "09:00"},
    {"day_of_week": 4, "start_time": "09:00"},
    {"day_of_week": 5, "start_time": "09:00"}
  ],
  "reminder_rules": [
    {"rule_type": "before_start", "offset_minutes": 0}  // В момент начала
  ]
}
```

**Результат**: Напоминание каждый будний день в 09:00

---

## 🛠️ API

### Python API

```python
from app.reminder_generator import regenerate_task_reminders

# После создания/редактирования задачи
count = regenerate_task_reminders(task_id)
print(f"Создано {count} напоминаний")
```

### Telegram API

```python
from app.telegram_notifier import send_task_reminder_notification

success = send_task_reminder_notification(
    task_title="Футбол - сын",
    task_id=123,
    reminder_type="before_start"
)
```

---

## 📝 Логи

```bash
# Логи отправки (каждую минуту)
tail -f logs/reminders_send.log

# Логи регенерации (раз в день)
tail -f logs/reminders_regenerate.log

# Логи приложения
tail -f logs/error.log
```

---

## 🔧 Настройка

### Переменные окружения

В `.env`:
```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Изменение расписания cron

Отредактируйте `scripts/setup_all_cron.sh` и запустите снова.

Примеры:
```bash
# Каждые 5 минут
*/5 * * * * ...

# Каждый час
0 * * * * ...

# Каждый день в 9:00
0 9 * * * ...
```

---

## ❓ FAQ

**Q: Как приостановить задачу на время?**  
A: В UI поставьте галочку "Приостановить до даты" и выберите дату.

**Q: Напоминания не приходят?**  
A: Проверьте:
1. `crontab -l` - есть ли задачи
2. `logs/reminders_send.log` - логи отправки
3. Telegram credentials в `.env`

**Q: Как удалить все старые напоминания?**  
A: 
```sql
DELETE FROM task_reminders WHERE sent = 0 AND reminder_time < datetime('now');
```

**Q: Как изменить период генерации (14 дней)?**  
A: В `regenerate_reminders.py` измените параметр `days_ahead`.

---

## 🎓 Архитектура

```
User creates task → ReminderGenerator
                    ↓
                task_reminders (14 days ahead)
                    ↓
         Cron (every minute) → send_task_reminders.py
                    ↓
              TelegramNotifier → User's phone 📱
                    ↓
           task_reminders.sent = 1
```

---

## 📅 Планы на будущее

- [ ] Web интерфейс для просмотра очереди напоминаний
- [ ] Статистика отправленных/пропущенных
- [ ] Push уведомления в веб-приложении
- [ ] Email уведомления
- [ ] Кастомные шаблоны сообщений

---

**Дата создания**: 10 октября 2025  
**Автор**: AI Assistant  
**Версия**: 1.0

