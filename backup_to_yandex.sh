#!/bin/bash
# Автоматический бэкап PostgreSQL на Яндекс.Диск
# Запускается через cron ежедневно в 2:00 MSK
# Публичная папка: https://yadi.sk/d/gVpI3Fst7J5EIw

set -e

# Конфигурация
BACKUP_DIR="/home/valstan/mikrokredit/backups"
DB_NAME="mikrokredit"
DB_USER="mikrokredit_user"
DB_HOST="localhost"
export PGPASSWORD="mikrokredit_pass_2024"

# Яндекс.Диск настройки
YANDEX_TOKEN="y0__xDR8Z0KGNuWAyCFzMykFJz31O8WoqV9ONfVuMNLNIyjYsZK"
YANDEX_FOLDER="/МикроКредит_Backups"  # Папка на Яндекс.Диске
MAX_BACKUPS=10  # Максимальное количество бэкапов

# Логирование
LOG_FILE="/home/valstan/mikrokredit/logs/backup.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== Начало создания бэкапа ==="

# Создание директории для бэкапов
mkdir -p "$BACKUP_DIR"

# Генерация имени файла с датой и временем
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/mikrokredit_${TIMESTAMP}.sql"
BACKUP_FILENAME="mikrokredit_${TIMESTAMP}.sql"

log "Создание дампа базы данных: $BACKUP_FILENAME"

# Создание дампа PostgreSQL
if pg_dump -U "$DB_USER" -h "$DB_HOST" "$DB_NAME" > "$BACKUP_FILE" 2>> "$LOG_FILE"; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "✓ Дамп создан успешно (размер: $BACKUP_SIZE)"
else
    log "✗ Ошибка создания дампа!"
    exit 1
fi

# Сжатие бэкапа
log "Сжатие бэкапа..."
gzip -f "$BACKUP_FILE"
BACKUP_FILE="${BACKUP_FILE}.gz"
BACKUP_FILENAME="${BACKUP_FILENAME}.gz"
COMPRESSED_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
log "✓ Бэкап сжат (размер: $COMPRESSED_SIZE)"

# Загрузка на Яндекс.Диск
log "Загрузка на Яндекс.Диск..."

# 1. Получаем URL для загрузки
UPLOAD_URL=$(curl -s -X GET \
    "https://cloud-api.yandex.net/v1/disk/resources/upload?path=${YANDEX_FOLDER}/${BACKUP_FILENAME}&overwrite=false" \
    -H "Authorization: OAuth ${YANDEX_TOKEN}" \
    | grep -o '"href":"[^"]*"' | cut -d'"' -f4)

if [ -z "$UPLOAD_URL" ]; then
    log "✗ Не удалось получить URL для загрузки. Проверьте токен и папку."
    exit 1
fi

# 2. Загружаем файл
if curl -s -X PUT "$UPLOAD_URL" \
    --data-binary "@${BACKUP_FILE}" \
    -H "Content-Type: application/x-gzip" \
    -o /dev/null; then
    log "✓ Бэкап загружен на Яндекс.Диск: ${YANDEX_FOLDER}/${BACKUP_FILENAME}"
else
    log "✗ Ошибка загрузки на Яндекс.Диск"
    exit 1
fi

# Удаление старых бэкапов на Яндекс.Диске (оставляем только MAX_BACKUPS)
log "Проверка количества бэкапов на Яндекс.Диске..."

# Получаем список файлов в папке
BACKUPS_LIST=$(curl -s -X GET \
    "https://cloud-api.yandex.net/v1/disk/resources?path=${YANDEX_FOLDER}&limit=100&sort=created" \
    -H "Authorization: OAuth ${YANDEX_TOKEN}")

# Подсчитываем количество файлов
BACKUPS_COUNT=$(echo "$BACKUPS_LIST" | grep -o '"type":"file"' | wc -l)
log "Всего бэкапов на Яндекс.Диске: $BACKUPS_COUNT"

if [ "$BACKUPS_COUNT" -gt "$MAX_BACKUPS" ]; then
    log "Удаление старых бэкапов (оставляем последние $MAX_BACKUPS)..."
    
    # Получаем список файлов для удаления (самые старые)
    FILES_TO_DELETE=$((BACKUPS_COUNT - MAX_BACKUPS))
    log "Нужно удалить $FILES_TO_DELETE старых бэкапов"
    
    # Получаем имена файлов для удаления
    OLD_FILES=$(echo "$BACKUPS_LIST" | grep -o '"name":"mikrokredit_[^"]*"' | cut -d'"' -f4 | head -n "$FILES_TO_DELETE")
    
    for OLD_FILE in $OLD_FILES; do
        log "Удаление: $OLD_FILE"
        curl -s -X DELETE \
            "https://cloud-api.yandex.net/v1/disk/resources?path=${YANDEX_FOLDER}/${OLD_FILE}&permanently=true" \
            -H "Authorization: OAuth ${YANDEX_TOKEN}" \
            -o /dev/null
        log "✓ Удалён: $OLD_FILE"
    done
fi

# Удаление локального бэкапа (оставляем только последние 3 локально)
log "Очистка локальных бэкапов..."
LOCAL_BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/mikrokredit_*.sql.gz 2>/dev/null | wc -l)
if [ "$LOCAL_BACKUP_COUNT" -gt 3 ]; then
    log "Удаление старых локальных бэкапов (оставляем последние 3)"
    ls -1t "$BACKUP_DIR"/mikrokredit_*.sql.gz | tail -n +4 | xargs rm -f
    log "✓ Старые локальные бэкапы удалены"
fi

# Статистика
log "=== Бэкап завершён ==="
log "Файл: $BACKUP_FILENAME"
log "Размер: $COMPRESSED_SIZE"
log "Локальная копия: $BACKUP_FILE"
log "Яндекс.Диск: ${YANDEX_FOLDER}/${BACKUP_FILENAME}"

# Очистка переменной с паролем
unset PGPASSWORD

exit 0

