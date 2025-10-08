#!/bin/bash

# MikroKredit Backup Script
# Creates backup of SQLite database and exports data to JSON

set -e

# Configuration
APP_DIR="/home/valstan/development/mikrokredit"
BACKUP_DIR="$APP_DIR/backups"
DB_FILE="$APP_DIR/mikrokredit.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Check if database exists
if [ ! -f "$DB_FILE" ]; then
    log_error "Database file not found: $DB_FILE"
    exit 1
fi

log_info "Starting backup process..."

# 1. Create SQLite database backup
log_info "Creating SQLite database backup..."
DB_BACKUP="$BACKUP_DIR/mikrokredit_db_$TIMESTAMP.db"
cp "$DB_FILE" "$DB_BACKUP"
log_info "Database backup created: $DB_BACKUP"

# 2. Export data to JSON
log_info "Exporting data to JSON..."
JSON_BACKUP="$BACKUP_DIR/mikrokredit_export_$TIMESTAMP.json"

# Start the application temporarily for export
cd "$APP_DIR"
source .venv/bin/activate

# Start app in background
python -c "
from web import create_app
app = create_app()
with app.test_client() as client:
    response = client.get('/export/json')
    with open('$JSON_BACKUP', 'wb') as f:
        f.write(response.data)
print('JSON export completed')
" &

# Wait for export to complete
sleep 3

# Stop any running processes
pkill -f "python -c" || true

log_info "JSON export created: $JSON_BACKUP"

# 3. Create compressed archive
log_info "Creating compressed archive..."
ARCHIVE="$BACKUP_DIR/mikrokredit_backup_$TIMESTAMP.tar.gz"
tar -czf "$ARCHIVE" -C "$BACKUP_DIR" "mikrokredit_db_$TIMESTAMP.db" "mikrokredit_export_$TIMESTAMP.json"
log_info "Archive created: $ARCHIVE"

# 4. Clean up old backups (keep last 10)
log_info "Cleaning up old backups..."
cd "$BACKUP_DIR"
ls -t mikrokredit_backup_*.tar.gz | tail -n +11 | xargs -r rm -f
ls -t mikrokredit_db_*.db | tail -n +11 | xargs -r rm -f
ls -t mikrokredit_export_*.json | tail -n +11 | xargs -r rm -f

# 5. Show backup summary
log_info "Backup completed successfully!"
log_info "Files created:"
log_info "  - Database: $DB_BACKUP"
log_info "  - JSON: $JSON_BACKUP"
log_info "  - Archive: $ARCHIVE"

# Show backup directory contents
log_info "Current backups:"
ls -la "$BACKUP_DIR" | grep mikrokredit
