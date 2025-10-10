#!/bin/bash
# Скрипт для синхронизации sequences с данными в таблицах

set -e

# Загружаем переменные из .env
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

echo "🔧 Синхронизация PostgreSQL sequences..."

export PGPASSWORD="${DB_PASSWORD}"
PGUSER="${DB_USER:-mikrokredit_user}"
PGHOST="localhost"
PGDB="mikrokredit"

# Функция для синхронизации sequence
sync_sequence() {
    local table=$1
    local seq=$2
    
    echo -n "  Проверка $table... "
    
    # Получаем текущие значения
    result=$(psql -U $PGUSER -h $PGHOST -d $PGDB -t -c "
        SELECT 
            COALESCE(MAX(id), 0) as max_id,
            (SELECT last_value FROM $seq) as seq_value
        FROM $table;
    ")
    
    max_id=$(echo $result | awk '{print $1}')
    seq_value=$(echo $result | awk '{print $3}')
    
    if [ "$max_id" -gt "$seq_value" ]; then
        echo "❌ Рассинхронизация! (max_id=$max_id, seq=$seq_value)"
        echo -n "     Исправление... "
        psql -U $PGUSER -h $PGHOST -d $PGDB -c "SELECT setval('$seq', $max_id, true);" > /dev/null
        echo "✅ Исправлено"
    elif [ "$max_id" -eq "$seq_value" ]; then
        echo "✅ OK (значение: $max_id)"
    else
        echo "⚠️  Sequence опережает ($max_id < $seq_value) - норма для пустой таблицы"
    fi
}

# Синхронизируем все sequences
sync_sequence "loans" "loans_id_seq"
sync_sequence "installments" "installments_id_seq"

echo ""
echo "✅ Синхронизация завершена!"
echo ""
echo "Текущее состояние:"
psql -U $PGUSER -h $PGHOST -d $PGDB -c "
SELECT 
    'loans' as table_name,
    COALESCE(MAX(id), 0) as max_id,
    (SELECT last_value FROM loans_id_seq) as sequence_value
FROM loans
UNION ALL
SELECT 
    'installments' as table_name,
    COALESCE(MAX(id), 0) as max_id,
    (SELECT last_value FROM installments_id_seq) as sequence_value
FROM installments;
"

unset PGPASSWORD

