# 🔧 Инструкция по настройке Nginx для проекта на VPS

> **Для AI-разработчика на другом сервере**  
> Эта инструкция описывает как настроен Nginx в проекте "Записная книжка Валентина" (MikroKredit Manager) для публикации Flask приложения в интернет.

---

## 📋 Контекст

**Сервер:** Ubuntu 24.04.3 LTS  
**Nginx версия:** 1.28.0  
**Приложение:** Flask + Gunicorn  
**URL:** http://73269587c9af.vps.myjino.ru/

---

## 🎯 Архитектура

```
Internet (port 80)
    ↓
Nginx (слушает 0.0.0.0:80)
    ↓
Reverse Proxy → Gunicorn (слушает 127.0.0.1:8002)
    ↓
Flask Application
    ↓
PostgreSQL / Redis
```

**Ключевой момент:** Nginx слушает публичный порт 80 и проксирует запросы на локальный Gunicorn (127.0.0.1:8002).

---

## 📁 Структура конфигурации Nginx

### 1. Главный конфиг

**Файл:** `/etc/nginx/nginx.conf`

**Важная строка:**
```nginx
include /etc/nginx/conf.d/*.conf;
```

Это означает, что Nginx автоматически загружает **ВСЕ** файлы с расширением `.conf` из директории `/etc/nginx/conf.d/`.

### 2. Конфиг нашего приложения

**Файл:** `/etc/nginx/conf.d/mikrokredit.conf`

**Расположение:** Именно в `conf.d/`, НЕ в `sites-enabled/` или `sites-available/` (их на этом сервере нет).

---

## 🔧 Полная конфигурация Nginx

Вот **ТОЧНЫЙ** конфиг, который работает у нас:

```nginx
server {
    # Слушаем порт 80 как default_server
    # Это означает что Nginx будет обрабатывать ВСЕ запросы на порт 80
    listen 80 default_server;
    
    # Server name "_" означает "любой хост"
    # Nginx ответит на любой домен/IP который указан на этот сервер
    server_name _;

    # === SECURITY HEADERS ===
    # Важны для безопасности, но не критичны для работы
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # === LOGGING ===
    access_log /var/log/nginx/mikrokredit_access.log;
    error_log /var/log/nginx/mikrokredit_error.log;

    # === STATIC FILES (опционально) ===
    # Если у вас есть статические файлы (CSS, JS, изображения)
    location /static {
        alias /home/valstan/mikrokredit/web/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # === MAIN APPLICATION ===
    # САМАЯ ВАЖНАЯ ЧАСТЬ!
    location / {
        # Проксируем на Gunicorn
        proxy_pass http://127.0.0.1:8002;
        
        # Передаём заголовки
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Таймауты (по умолчанию 30 секунд достаточно)
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        
        # Буферизация (можно оставить как есть)
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # === HEALTH CHECK (опционально) ===
    # Эндпоинт для проверки работы приложения
    location /healthz {
        proxy_pass http://127.0.0.1:8002/healthz;
        access_log off;  # Не логируем health checks
    }
}
```

---

## 🚀 Пошаговая инструкция для настройки

### Шаг 1: Проверьте структуру Nginx

```bash
# Проверьте главный конфиг
cat /etc/nginx/nginx.conf | grep include

# Должна быть строка:
# include /etc/nginx/conf.d/*.conf;
```

**Если используется `sites-enabled/`:**
```bash
# Альтернативный вариант (Debian/Ubuntu стиль)
# include /etc/nginx/sites-enabled/*;
```

### Шаг 2: Убедитесь что Gunicorn работает

```bash
# Проверьте процесс Gunicorn
ps aux | grep gunicorn

# Должно быть что-то вроде:
# gunicorn --bind 127.0.0.1:8000 app:app
```

**Важно:** Запомните на каком порту работает Gunicorn (у нас `8002`, у вас может быть `8000` или другой).

### Шаг 3: Создайте конфиг для вашего приложения

```bash
# Создайте файл (замените PROJECT на название вашего проекта)
sudo nano /etc/nginx/conf.d/PROJECT.conf
```

**Минимальная рабочая конфигурация:**

```nginx
server {
    listen 80 default_server;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;  # ЗАМЕНИТЕ на ваш порт!
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**ВАЖНО:** Замените `8000` на порт вашего Gunicorn!

### Шаг 4: Удалите дефолтный конфиг (если есть)

```bash
# Проверьте есть ли default.conf
ls -la /etc/nginx/conf.d/

# Если есть default.conf, переименуйте его
sudo mv /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf.bak
```

**Почему?** Если есть несколько конфигов с `listen 80 default_server`, Nginx не запустится.

### Шаг 5: Проверьте синтаксис конфига

```bash
# Проверка конфигурации
sudo nginx -t

# Должно быть:
# nginx: configuration file /etc/nginx/nginx.conf test is successful
```

**Если ошибка:** Читайте сообщение внимательно, там указана строка и причина.

### Шаг 6: Перезапустите Nginx

```bash
# Перезагрузка конфигурации (мягкий способ)
sudo nginx -s reload

# ИЛИ полный перезапуск (если reload не помог)
sudo systemctl restart nginx

# Проверьте статус
sudo systemctl status nginx
```

### Шаг 7: Проверьте что порты слушаются

```bash
# Проверьте что Nginx слушает порт 80
sudo ss -tulpn | grep :80

# Должно быть:
# tcp   LISTEN  0.0.0.0:80    nginx

# Проверьте что Gunicorn слушает свой порт
sudo ss -tulpn | grep :8000  # Замените на ваш порт

# Должно быть:
# tcp   LISTEN  127.0.0.1:8000    python3
```

### Шаг 8: Тестирование

```bash
# Локальная проверка
curl http://localhost

# Должен вернуться HTML вашего приложения

# Проверка извне (с другого компьютера или через браузер)
# http://YOUR_SERVER_IP/
```

---

## 🐛 Troubleshooting: Почему не работает?

### Проблема 1: "502 Bad Gateway"

**Причина:** Nginx не может подключиться к Gunicorn.

**Решение:**
```bash
# 1. Убедитесь что Gunicorn работает
ps aux | grep gunicorn

# 2. Проверьте на каком порту
sudo ss -tulpn | grep python

# 3. Проверьте что порт в nginx.conf правильный
grep proxy_pass /etc/nginx/conf.d/*.conf

# 4. Проверьте логи Nginx
sudo tail -f /var/log/nginx/error.log
```

### Проблема 2: "Connection refused"

**Причина:** Gunicorn слушает неправильный интерфейс.

**Решение:**
```bash
# Gunicorn ДОЛЖЕН слушать 127.0.0.1 (localhost)
# В вашем скрипте запуска должно быть:
gunicorn --bind 127.0.0.1:8000 app:app

# НЕ 0.0.0.0:8000 (хотя тоже работает, но менее безопасно)
```

### Проблема 3: "Сайт не открывается из интернета"

**Возможные причины:**

1. **Firewall блокирует порт 80**
   ```bash
   # Проверьте firewall
   sudo ufw status
   
   # Если активен, откройте порт 80
   sudo ufw allow 80/tcp
   sudo ufw reload
   ```

2. **Nginx не слушает 0.0.0.0:80**
   ```bash
   # Проверьте что Nginx слушает ВСЕ интерфейсы
   sudo ss -tulpn | grep :80
   
   # Должно быть:
   # 0.0.0.0:80  (а не 127.0.0.1:80)
   ```

3. **Провайдер VPS блокирует порт**
   ```bash
   # Уточните у хостинг-провайдера
   # Некоторые VPS требуют открыть порты через панель управления
   ```

### Проблема 4: "nginx: [emerg] bind() to 0.0.0.0:80 failed"

**Причина:** Порт 80 уже занят.

**Решение:**
```bash
# Найдите что занимает порт
sudo lsof -i :80

# Если это Apache или другой веб-сервер
sudo systemctl stop apache2
sudo systemctl disable apache2

# Потом запустите Nginx
sudo systemctl start nginx
```

### Проблема 5: Nginx запустился, но показывает дефолтную страницу

**Причина:** Неправильный приоритет конфигов.

**Решение:**
```bash
# Убедитесь что ваш конфиг имеет default_server
grep "default_server" /etc/nginx/conf.d/*.conf

# Должна быть только ОДНА строка с default_server

# Проверьте порядок загрузки конфигов
sudo nginx -T | grep "server_name"
```

---

## ✅ Контрольный чек-лист

Перед тем как писать "не работает", проверьте:

- [ ] Gunicorn запущен и работает (`ps aux | grep gunicorn`)
- [ ] Gunicorn слушает 127.0.0.1:ПОРТ (`ss -tulpn | grep ПОРТ`)
- [ ] Nginx запущен (`systemctl status nginx`)
- [ ] Nginx слушает 0.0.0.0:80 (`ss -tulpn | grep :80`)
- [ ] Конфиг Nginx валидный (`nginx -t`)
- [ ] Порт 80 открыт в firewall (`ufw status`)
- [ ] proxy_pass указывает на правильный порт Gunicorn
- [ ] В логах нет ошибок (`tail -f /var/log/nginx/error.log`)
- [ ] Локально работает (`curl http://localhost`)

---

## 📝 Пример рабочей конфигурации для FastAPI/Flask

### Для FastAPI (как у проекта SETKA)

```nginx
server {
    listen 80 default_server;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Для WebSocket (если используется)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Запуск FastAPI через Uvicorn

```bash
# В фоне
nohup uvicorn main:app --host 127.0.0.1 --port 8000 > /dev/null 2>&1 &

# Или через systemd (рекомендуется)
# Создайте /etc/systemd/system/fastapi.service
```

---

## 🔒 Бонус: SSL/HTTPS (если нужно)

Если хотите HTTPS:

```bash
# Установите Certbot
sudo apt install certbot python3-certbot-nginx

# Получите сертификат (замените на ваш домен)
sudo certbot --nginx -d yourdomain.com

# Certbot автоматически обновит конфиг Nginx!
```

---

## 📞 Команды для диагностики

```bash
# Проверка конфигурации
sudo nginx -t

# Перезагрузка
sudo nginx -s reload

# Полная конфигурация (что реально загружено)
sudo nginx -T

# Логи в реальном времени
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# Проверка портов
sudo ss -tulpn | grep -E "(80|8000|8002)"

# Проверка процессов
ps aux | grep -E "(nginx|gunicorn|uvicorn)"

# Тест с локалхоста
curl -v http://localhost

# Проверка извне (с другого компьютера)
curl -v http://YOUR_SERVER_IP
```

---

## 🎯 Главные моменты для успеха

1. **Gunicorn слушает `127.0.0.1:ПОРТ`** (НЕ 0.0.0.0)
2. **Nginx слушает `0.0.0.0:80`** (публичный интерфейс)
3. **Конфиг в `/etc/nginx/conf.d/`** с расширением `.conf`
4. **`proxy_pass http://127.0.0.1:ПОРТ`** должен совпадать с портом Gunicorn
5. **Только один `default_server`** в конфигах
6. **После изменений:** `nginx -t` → `nginx -s reload`
7. **Порт 80 открыт** в firewall и у VPS провайдера

---

## 💡 Если всё ещё не работает

Пришлите мне:

1. Вывод команды: `sudo nginx -T | head -100`
2. Вывод команды: `ps aux | grep -E "(gunicorn|uvicorn|python)"`
3. Вывод команды: `sudo ss -tulpn | grep -E "(80|8000)"`
4. Последние 50 строк логов: `sudo tail -50 /var/log/nginx/error.log`
5. Вывод: `curl -v http://localhost`

Удачи! 🚀

---

**Автор:** AI Assistant для проекта "Записная книжка Валентина"  
**Дата:** 10.10.2025  
**Версия:** 1.0  
**Проверено на:** Ubuntu 24.04.3 LTS, Nginx 1.28.0

