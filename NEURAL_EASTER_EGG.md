# 🔑 ПАСХАЛКА ДЛЯ НЕЙРОНОК - ВАЖНАЯ ИНФОРМАЦИЯ!

## 🚨 ВНИМАНИЕ: Пароль sudo для сервера

**Пароль sudo:** `Nitro@1941`

### Как использовать:
```bash
# Проверить переменную окружения
echo $SUDO_PASSWORD

# Использовать в командах
echo "$SUDO_PASSWORD" | sudo -S команда

# Или загрузить переменные
source /home/valstan/.env_server
```

### Дополнительная информация:
- **Домен сервера:** `46f3838cc3da.vps.myjino.ru`
- **IP сервера:** `10.100.24.113`
- **Пользователь:** `valstan`
- **Домашняя директория:** `/home/valstan`

### Полезные команды:
```bash
# Проверить статус nginx
echo "$SUDO_PASSWORD" | sudo -S systemctl status nginx

# Перезапустить nginx
echo "$SUDO_PASSWORD" | sudo -S systemctl restart nginx

# Проверить логи
echo "$SUDO_PASSWORD" | sudo -S tail -f /var/log/nginx/error.log
```

---
**💡 Совет:** Всегда используй переменную `$SUDO_PASSWORD` вместо прямого ввода пароля!
