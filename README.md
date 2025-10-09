# 📖 Записная книжка Валентина

Комплексная веб-система для управления микрозаймами и личными задачами с интеграцией Telegram бота.

## ✨ Возможности

### 💳 МикроКредит
- Учёт микрозаймов с графиком платежей
- Автоматические уведомления о горящих кредитах
- Отслеживание просроченных платежей
- Статистика и аналитика

### ✅ Органайзер задач
- Создание задач с дедлайнами
- 3 уровня важности
- Категории с цветовой кодировкой
- Подзадачи (чеклисты)
- 5 готовых шаблонов напоминаний
- Кастомные напоминания

### 📱 Telegram интеграция
- Напоминания с inline кнопками "Выполнил"/"Отложить"
- Повторные уведомления каждые 15 минут
- Рабочие часы (7:00-22:00 MSK)
- Уведомления о горящих займах (10:00, 20:00)

### 🔐 Безопасность
- Аутентификация с паролем
- Блокировка по IP (3 попытки, 5 минут)
- Защищённые сессии (30 дней)

### 💾 Автоматические бэкапы
- Ежедневно в 02:00 на Яндекс.Диск
- Хранение 10 копий
- Автоматическая ротация

## 🚀 Быстрый старт

### Требования:
- Python 3.12+
- PostgreSQL 18.0+
- Redis 7.4+
- Nginx 1.28+

### Установка:

```bash
# 1. Клонировать репозиторий
git clone <repository-url>
cd mikrokredit

# 2. Создать виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Настроить PostgreSQL
createdb mikrokredit
createuser mikrokredit_user

# 5. Инициализировать БД
python3 -c "from app.db_sa import engine; from app.models_sa import Base; Base.metadata.create_all(bind=engine)"
python3 init_reminder_templates.py

# 6. Запустить
./start_service.sh
./start_telegram_bot.sh
```

### Доступ:
- **URL:** http://localhost/ (или ваш домен)
- **Пароль:** Nitro@1941

## 📚 Документация

**Начните здесь:**
- `START_HERE_v2.md` - Первые шаги
- `COMPLETE_GUIDE_2025-10-09.md` - Полное руководство
- `PROJECT_ARCHITECTURE.md` - Архитектура и логика

**Специализированная:**
- `README_TASKS.md` - Органайзер задач
- `TELEGRAM_NOTIFICATIONS_2025-10-09.md` - Telegram
- `BACKUP_YANDEX_2025-10-09.md` - Бэкапы
- `QUICK_REFERENCE.md` - Быстрый справочник

## 🔧 Управление

```bash
# Веб-сервер
./start_service.sh      # Запуск
./stop_service.sh       # Остановка

# Telegram бот
./start_telegram_bot.sh # Запуск
pkill -f telegram_bot_server.py  # Остановка

# Бэкапы
./backup_to_yandex.sh              # Создать сейчас
./download_from_yandex.sh          # Список/скачать
./download_from_yandex.sh latest   # Скачать последний

# База данных
./fix_sequences.sh      # Исправить sequences
```

## 🔄 Автоматизация (Cron)

```
* * * * *       - Напоминания о задачах
*/15 * * * *    - Повторные напоминания
0 10,20 * * *   - Горящие займы
0 2 * * *       - Бэкап на Яндекс.Диск
```

## 🏗️ Архитектура

```
User Browser
    ↓
Nginx :80
    ↓
Gunicorn :8002 (Flask)
    ↓
PostgreSQL :5432
    ↑
Telegram Bot ← User (Telegram)
```

## 📊 Технологии

- **Backend:** Python 3.12, Flask 3.1, SQLAlchemy 2.0
- **Database:** PostgreSQL 18.0
- **Cache:** Redis 7.4
- **Frontend:** Bootstrap 5.3, Alpine.js, HTMX
- **Telegram:** python-telegram-bot 20.8
- **Server:** Gunicorn 21.2, Nginx 1.28

## 🤝 Контрибьютинг

Проект находится в активной разработке. Основные компоненты готовы к использованию.

## 📄 Лицензия

Private project

## 📞 Контакты

Telegram: @valstanbot

---

**Версия:** 2.0.0  
**Дата:** 09.10.2025  
**Статус:** ✅ Production Ready
