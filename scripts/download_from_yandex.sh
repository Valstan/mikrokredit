#!/bin/bash
# Скачивание бэкапа с Яндекс.Диска
# Публичная папка: https://yadi.sk/d/gVpI3Fst7J5EIw

# Загружаем переменные из .env
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

YANDEX_TOKEN="${YANDEX_DISK_TOKEN}"
YANDEX_FOLDER="/МикроКредит_Backups"

# Если не указан файл - показываем список
if [ -z "$1" ]; then
    echo "=== Список бэкапов на Яндекс.Диске ==="
    curl -s "https://cloud-api.yandex.net/v1/disk/resources?path=${YANDEX_FOLDER}&limit=100&sort=-created" \
        -H "Authorization: OAuth ${YANDEX_TOKEN}" \
        | python3 -c "
import sys, json
data = json.load(sys.stdin)
if '_embedded' in data and 'items' in data['_embedded']:
    for i, item in enumerate(data['_embedded']['items'], 1):
        size_mb = item.get('size', 0) / 1024
        created = item.get('created', '')[:19].replace('T', ' ')
        print(f'{i}. {item[\"name\"]} ({size_mb:.1f} KB) - {created}')
else:
    print('Бэкапы не найдены')
"
    echo ""
    echo "Использование: $0 mikrokredit_YYYYMMDD_HHMMSS.sql.gz"
    echo "Или:           $0 latest  (скачать последний)"
    exit 0
fi

BACKUP_FILE="$1"

# Если запрошен последний бэкап
if [ "$BACKUP_FILE" == "latest" ]; then
    echo "Получение последнего бэкапа..."
    BACKUP_FILE=$(curl -s "https://cloud-api.yandex.net/v1/disk/resources?path=${YANDEX_FOLDER}&limit=1&sort=-created" \
        -H "Authorization: OAuth ${YANDEX_TOKEN}" \
        | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['_embedded']['items'][0]['name'] if '_embedded' in data and 'items' in data['_embedded'] and data['_embedded']['items'] else '')")
    
    if [ -z "$BACKUP_FILE" ]; then
        echo "Ошибка: не найдено ни одного бэкапа"
        exit 1
    fi
    echo "Последний бэкап: $BACKUP_FILE"
fi

# Получаем ссылку для скачивания
echo "Получение ссылки для скачивания..."
DOWNLOAD_URL=$(curl -s "https://cloud-api.yandex.net/v1/disk/resources/download?path=${YANDEX_FOLDER}/${BACKUP_FILE}" \
    -H "Authorization: OAuth ${YANDEX_TOKEN}" \
    | grep -o '"href":"[^"]*"' | cut -d'"' -f4)

if [ -z "$DOWNLOAD_URL" ]; then
    echo "Ошибка: не удалось получить ссылку для скачивания"
    echo "Проверьте имя файла"
    exit 1
fi

# Скачиваем
echo "Скачивание: $BACKUP_FILE"
if curl -# -L "$DOWNLOAD_URL" -o "$BACKUP_FILE"; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✓ Бэкап скачан: $BACKUP_FILE (размер: $SIZE)"
    echo ""
    echo "Для восстановления:"
    echo "  1. gunzip $BACKUP_FILE"
    echo "  2. export PGPASSWORD='YOUR_DB_PASSWORD'  # из .env файла"
    echo "  3. psql -U mikrokredit_user -h localhost -d mikrokredit < ${BACKUP_FILE%.gz}"
else
    echo "✗ Ошибка скачивания"
    exit 1
fi

