# Удаление Docker из проекта - 09.10.2025

## Причина

Docker не использовался в проекте MikroKredit. Всё работает локально:
- PostgreSQL установлен системно
- Nginx установлен системно
- Redis установлен системно
- Python работает через virtualenv
- Gunicorn запускается напрямую

Для одной системы с одним проектом изолированные контейнеры избыточны.

## Что было удалено

### Системные пакеты:
```
docker-ce                    (5:28.5.1)
docker-ce-cli               (5:28.5.1)
docker-ce-rootless-extras   (5:28.5.1)
docker-buildx-plugin        (0.29.1)
docker-compose-plugin       (2.40.0)
containerd.io               (1.7.28)
libslirp0                   (зависимость)
pigz                        (зависимость)
slirp4netns                 (зависимость)
```

### Директории и конфигурация:
```
/var/lib/docker/            (Docker данные)
/etc/docker/                (конфигурация)
~/.docker/                  (пользовательская конфигурация)
/etc/apt/sources.list.d/docker.list  (репозиторий)
```

### Файлы проекта:
```
Dockerfile                  (конфигурация образа)
docker-compose.yml          (оркестрация)
docker/Dockerfile.web       (web образ)
postgres.sh                 (скрипт для Docker PostgreSQL)
```

## Освобождено места

**Всего:** ~437 MB
- Пакеты Docker: 436 MB
- Зависимости: 409 KB
- Файлы проекта: ~2 KB

**Было:** 6.4G свободно  
**Стало:** 6.8G свободно (+400MB)

## Что осталось работать

✅ **PostgreSQL 18.0** - системный сервис
```bash
systemctl status postgresql
psql -U mikrokredit_user -d mikrokredit -h localhost
```

✅ **Nginx 1.28.0** - системный сервис
```bash
systemctl status nginx
```

✅ **Redis 7.4.1** - системный сервис
```bash
systemctl status redis-server
```

✅ **MikroKredit** - Python virtualenv + Gunicorn
```bash
./start_service.sh
./stop_service.sh
```

## Преимущества удаления

1. **Производительность**
   - Нет overhead контейнеризации
   - Прямой доступ к системным ресурсам
   - Быстрее запуск и работа

2. **Простота**
   - Меньше слоёв абстракции
   - Проще отладка
   - Понятнее архитектура

3. **Ресурсы**
   - Освобождено 437 MB диска
   - Меньше потребление RAM
   - Нет фоновых процессов Docker

4. **Обслуживание**
   - Меньше компонентов для обновления
   - Проще резервное копирование
   - Системные инструменты работают напрямую

## Когда Docker нужен

Docker полезен когда:
- Несколько проектов с разными версиями зависимостей
- Нужна воспроизводимая среда для команды
- Микросервисная архитектура
- Deployment в облако (Kubernetes, etc)
- CI/CD пайплайны

## Наш случай

У нас:
- ✅ Одна система
- ✅ Один проект
- ✅ Стабильная среда
- ✅ Всё работает локально

**Вывод:** Docker избыточен! ✨

## Альтернативы (если понадобится изоляция)

### Python virtualenv (уже используется)
```bash
python -m venv .venv
source .venv/bin/activate
```
Изолирует Python зависимости - достаточно для большинства случаев.

### systemd-nspawn
Если нужна изоляция без Docker - легковесные контейнеры от systemd.

### Виртуальная машина
Для полной изоляции - но это overkill для нашего случая.

## Проверка после удаления

✅ MikroKredit запущен и работает
```bash
curl http://localhost/healthz
# {"status":"ok"}
```

✅ База данных доступна
```bash
psql -U mikrokredit_user -d mikrokredit -h localhost -c "SELECT COUNT(*) FROM loans;"
# 26 записей
```

✅ Веб-интерфейс работает
```bash
curl -I http://localhost/
# HTTP/1.1 200 OK
```

✅ Все сервисы активны
```bash
systemctl status postgresql nginx redis-server
# All: active (running)
```

## Обновлённая архитектура

```
┌─────────────────────────────────────────┐
│         Ubuntu 24.04 LTS                │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  Системные сервисы                │ │
│  │  ├─ PostgreSQL 18.0   (port 5432) │ │
│  │  ├─ Nginx 1.28.0      (port 80)   │ │
│  │  └─ Redis 7.4.1       (port 6379) │ │
│  └───────────────────────────────────┘ │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  MikroKredit                      │ │
│  │  ├─ Python 3.12 (virtualenv)     │ │
│  │  ├─ Gunicorn (port 8002)         │ │
│  │  └─ Flask приложение              │ │
│  └───────────────────────────────────┘ │
│                                         │
│  Nginx ──proxy──> Gunicorn ──> PostgreSQL
│                                         │
└─────────────────────────────────────────┘
```

Всё просто, понятно и эффективно! 🎯

## Управление сервисами

### PostgreSQL
```bash
# Статус
systemctl status postgresql

# Перезапуск (если нужно)
sudo systemctl restart postgresql

# Бэкап
pg_dump -U mikrokredit_user -h localhost mikrokredit > backup.sql

# Восстановление
psql -U mikrokredit_user -h localhost mikrokredit < backup.sql
```

### MikroKredit
```bash
# Запуск
./start_service.sh

# Остановка
./stop_service.sh

# Логи
tail -f logs/error.log
tail -f logs/access.log
```

### Nginx
```bash
# Статус
systemctl status nginx

# Проверка конфигурации
sudo nginx -t

# Перезагрузка конфигурации
sudo systemctl reload nginx
```

---
**Дата:** 09.10.2025 09:00 MSK  
**Освобождено:** 437 MB  
**Статус:** ✅ Всё работает без Docker

