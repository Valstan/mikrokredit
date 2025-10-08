#!/bin/bash

# MikroKredit PostgreSQL Management Script

set -e

# Configuration
CONTAINER_NAME="mikrokredit-postgres"
POSTGRES_DB="mikrokredit"
POSTGRES_USER="mikrokredit_user"
POSTGRES_PASSWORD="mikrokredit_pass"
POSTGRES_PORT="5433"

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

# Function to start PostgreSQL
start_postgres() {
    log_info "Starting PostgreSQL container..."
    
    # Check if container already exists
    if docker ps -a --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        if docker ps --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
            log_warn "PostgreSQL container is already running"
            return 0
        else
            log_info "Starting existing PostgreSQL container..."
            docker start "$CONTAINER_NAME"
        fi
    else
        log_info "Creating new PostgreSQL container..."
        docker run --name "$CONTAINER_NAME" \
            -e POSTGRES_DB="$POSTGRES_DB" \
            -e POSTGRES_USER="$POSTGRES_USER" \
            -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
            -p "$POSTGRES_PORT:5432" \
            -d postgres:15
    fi
    
    # Wait for PostgreSQL to be ready
    log_info "Waiting for PostgreSQL to be ready..."
    sleep 5
    
    # Test connection
    if docker exec "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1;" > /dev/null 2>&1; then
        log_info "PostgreSQL is ready!"
        log_info "Connection string: postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@localhost:$POSTGRES_PORT/$POSTGRES_DB"
    else
        log_error "PostgreSQL failed to start properly"
        return 1
    fi
}

# Function to stop PostgreSQL
stop_postgres() {
    log_info "Stopping PostgreSQL container..."
    docker stop "$CONTAINER_NAME" 2>/dev/null || log_warn "Container was not running"
}

# Function to restart PostgreSQL
restart_postgres() {
    log_info "Restarting PostgreSQL container..."
    stop_postgres
    sleep 2
    start_postgres
}

# Function to show status
show_status() {
    if docker ps --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        log_info "PostgreSQL container is running"
        log_info "Connection string: postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@localhost:$POSTGRES_PORT/$POSTGRES_DB"
        
        # Show database info
        log_info "Database information:"
        docker exec "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
            SELECT 
                'Loans: ' || COUNT(*) as loans_count
            FROM loans
            UNION ALL
            SELECT 
                'Installments: ' || COUNT(*) as installments_count
            FROM installments;
        " 2>/dev/null || log_warn "Could not query database"
    else
        log_warn "PostgreSQL container is not running"
    fi
}

# Function to backup database
backup_postgres() {
    log_info "Creating PostgreSQL backup..."
    
    BACKUP_FILE="mikrokredit_postgres_backup_$(date +%Y%m%d_%H%M%S).sql"
    
    if docker exec "$CONTAINER_NAME" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" > "$BACKUP_FILE"; then
        log_info "Backup created: $BACKUP_FILE"
    else
        log_error "Failed to create backup"
        return 1
    fi
}

# Function to restore database
restore_postgres() {
    if [ -z "$1" ]; then
        log_error "Please provide backup file path"
        return 1
    fi
    
    BACKUP_FILE="$1"
    
    if [ ! -f "$BACKUP_FILE" ]; then
        log_error "Backup file not found: $BACKUP_FILE"
        return 1
    fi
    
    log_warn "This will replace all data in the database!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Restoring database from: $BACKUP_FILE"
        docker exec -i "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$BACKUP_FILE"
        log_info "Database restored successfully"
    else
        log_info "Restore cancelled"
    fi
}

# Function to connect to database
connect_postgres() {
    log_info "Connecting to PostgreSQL database..."
    docker exec -it "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
}

# Main script logic
case "${1:-status}" in
    start)
        start_postgres
        ;;
    stop)
        stop_postgres
        ;;
    restart)
        restart_postgres
        ;;
    status)
        show_status
        ;;
    backup)
        backup_postgres
        ;;
    restore)
        restore_postgres "$2"
        ;;
    connect)
        connect_postgres
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|backup|restore <file>|connect}"
        echo ""
        echo "Commands:"
        echo "  start    - Start PostgreSQL container"
        echo "  stop     - Stop PostgreSQL container"
        echo "  restart  - Restart PostgreSQL container"
        echo "  status   - Show container and database status"
        echo "  backup   - Create database backup"
        echo "  restore  - Restore database from backup file"
        echo "  connect  - Connect to database with psql"
        exit 1
        ;;
esac
