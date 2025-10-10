# 📋 Записная книжка Валентина

> Комплексная система управления займами и задачами с Telegram интеграцией

[![Production](https://img.shields.io/badge/status-production-success)]()
[![Version](https://img.shields.io/badge/version-2.0.0-blue)]()
[![Python](https://img.shields.io/badge/python-3.12-blue)]()
[![PostgreSQL](https://img.shields.io/badge/postgresql-18.0-blue)]()

---

## 🚀 Быстрый доступ

**Веб-интерфейс:**
- 🌐 URL: http://73269587c9af.vps.myjino.ru/
- 🔐 Пароль: `[см. .env - AUTH_PASSWORD]`

**Telegram:**
- 🤖 Бот: [@valstanbot](https://t.me/valstanbot)
- 📱 Уведомления 24/7

---

## 💡 Основные возможности

### 💳 Модуль МикроКредит
Полный учёт займов с умной аналитикой:
- 📊 График платежей с автоматическим отслеживанием
- 🔥 Уведомления о горящих кредитах (< 5 дней)
- 💰 Автоматический расчёт долга
- 📈 Статистика и аналитика

### ✅ Органайзер задач
Гибкая система управления делами:
- 🎯 3 уровня важности (Важная/Нужная/Хотелось бы)
- 📂 Категории с цветовой кодировкой
- ✔️ Подзадачи (чеклисты)
- ⏰ Шаблоны и кастомные напоминания
- 📱 **Telegram интеграция с интерактивными кнопками**

### 📱 Умные уведомления
Никогда не забывайте важное:
- 🔔 Автоматические напоминания о задачах
- 🔄 Повторы каждые 15 мин при игнорировании
- ⏰ Рабочие часы: 7:00-22:00 MSK
- 🔥 Уведомления о горящих займах (10:00, 20:00)
- 🎯 Кнопки "Выполнил" / "Отложить"

---

## 📖 Полная документация

### Главный документ:
📘 **[DOCUMENTATION.md](DOCUMENTATION.md)** - содержит ВСЮ информацию:
- Быстрый старт и примеры использования
- Полное описание всех модулей
- Инструкции по управлению системой
- Troubleshooting и решение проблем
- API и конфигурация

### Архивные документы:
Техническая документация по разработке находится в `docs/archive/`

---

## 🏗️ Технологии

| Компонент | Технология |
|-----------|------------|
| Backend | Python 3.12, Flask 3.1, SQLAlchemy 2.0 |
| Database | PostgreSQL 18.0 (9 таблиц) |
| Frontend | Bootstrap 5.3, Alpine.js |
| Server | Gunicorn (4 workers), Nginx |
| Cache | Redis 7.4 |
| Notifications | python-telegram-bot 20.8 |
| Cloud | Yandex.Disk (бэкапы) |

---

## 🚀 Управление системой

### Запуск сервисов:
```bash
cd /home/valstan/mikrokredit

# Веб-сервер
scripts/start_service.sh

# Telegram бот
scripts/start_telegram_bot.sh
```

### Остановка:
```bash
scripts/stop_service.sh           # Веб
pkill -f telegram_bot_server.py   # Telegram бот
```

### Проверка статуса:
```bash
# Health check
curl http://localhost/healthz

# Процессы
ps aux | grep -E "(gunicorn|telegram)" | grep -v grep

# Логи
tail -f logs/error.log
tail -f logs/telegram_tasks.log
```

### Утилиты:
```bash
scripts/backup_to_yandex.sh       # Бэкап БД
scripts/download_from_yandex.sh   # Скачать бэкап
scripts/fix_sequences.sh          # Исправить sequences
```

---

## 🔐 Безопасность

- 🔑 Аутентификация по паролю
- 🛡️ Блокировка IP при брутфорсе (3 попытки → 5 минут)
- 🍪 Безопасные сессии (30 дней)
- 🔒 HTTPS-ready конфигурация

---

## 💾 Автоматические бэкапы

- ⏰ Ежедневно в 02:00 MSK
- ☁️ Яндекс.Диск (10 копий)
- 🔗 [Папка с бэкапами](https://yadi.sk/d/gVpI3Fst7J5EIw)
- 📦 SQL dump + gzip (~8 KB)

---

## 📊 Статистика проекта

```
Файлы:              ~50 Python/HTML/Shell
Строк кода:         ~5,000
Таблиц БД:          9
Telegram ботов:     4 скрипта
Cron задач:         4
Скриптов:           10+
```

---

## 🎯 Основные маршруты

| URL | Описание |
|-----|----------|
| `/` | Dashboard (общая статистика) |
| `/loans` | Список займов |
| `/tasks` | Органайзер задач |
| `/tasks/categories` | Управление категориями |
| `/auth/login` | Вход в систему |
| `/healthz` | Health check для мониторинга |

---

## 🔧 Конфигурация

### База данных:
```
Host:     localhost:5432
Database: mikrokredit
User:     mikrokredit_user
Password: [см. .env - DB_PASSWORD]
```

### Telegram:
```
Bot:      @valstanbot
Token:    [см. .env - TELEGRAM_BOT_TOKEN]
Chat ID:  352096813
```

---

## 🐛 Troubleshooting

**Проблемы с запуском?**
```bash
# Проверьте логи
tail -50 logs/error.log

# Исправьте sequences
scripts/fix_sequences.sh

# Перезапустите
scripts/stop_service.sh
scripts/start_service.sh
```

**Не работают кнопки в Telegram?**
```bash
# Перезапустите бота
pkill -f telegram_bot_server.py
scripts/start_telegram_bot.sh

# Создайте новую задачу для свежих кнопок
```

**Полное руководство по решению проблем → [DOCUMENTATION.md](DOCUMENTATION.md#troubleshooting)**

---

## 📞 Ссылки

- 📘 **[Полная документация](DOCUMENTATION.md)** - читайте ЭТО для всех вопросов
- 🌐 [Веб-интерфейс](http://73269587c9af.vps.myjino.ru/)
- 🤖 [Telegram бот](https://t.me/valstanbot)
- ☁️ [Яндекс.Диск бэкапы](https://yadi.sk/d/gVpI3Fst7J5EIw)
- 📦 GitHub: `github.com/Valstan/mikrokredit`

---

**Версия:** 2.0.0  
**Дата:** 09.10.2025  
**Статус:** ✅ Production Ready

---

<div align="center">

**Создано с ❤️ для автоматизации личных финансов и задач**

</div>
