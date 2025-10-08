#!/bin/bash

# MikroKredit Project Management Script
# Integrates with valstan_network and shared infrastructure

set -e

# Configuration
PROJECT_NAME="mikrokredit"
COMPOSE_FILE="docker-compose.yml"
NETWORK_NAME="valstan_network"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        return 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        return 1
    fi
    
    # Check if valstan_network exists
    if ! docker network ls | grep -q "$NETWORK_NAME"; then
        log_warn "Creating valstan_network..."
        docker network create "$NETWORK_NAME" || log_error "Failed to create network"
    fi
    
    log_info "Prerequisites check completed"
}

# Function to start the project
start_project() {
    log_info "Starting MikroKredit project..."
    
    check_prerequisites
    
    # Start services
    docker-compose -f "$COMPOSE_FILE" up -d
    
    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 10
    
    # Check service status
    if docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        log_info "Project started successfully!"
        log_info "Web application: http://localhost:8002"
        log_info "PostgreSQL: localhost:5434"
        log_info "API Gateway integration: Enabled"
    else
        log_error "Failed to start project"
        return 1
    fi
}

# Function to stop the project
stop_project() {
    log_info "Stopping MikroKredit project..."
    docker-compose -f "$COMPOSE_FILE" down
    log_info "Project stopped"
}

# Function to restart the project
restart_project() {
    log_info "Restarting MikroKredit project..."
    stop_project
    sleep 2
    start_project
}

# Function to show status
show_status() {
    log_info "MikroKredit Project Status:"
    echo ""
    docker-compose -f "$COMPOSE_FILE" ps
    echo ""
    
    # Show network information
    log_info "Network Information:"
    docker network inspect "$NETWORK_NAME" --format '{{range .Containers}}{{.Name}}: {{.IPv4Address}}{{"\n"}}{{end}}' | grep "$PROJECT_NAME" || log_warn "No containers found in network"
}

# Function to show logs
show_logs() {
    local service="${1:-mikrokredit-web}"
    log_info "Showing logs for $service..."
    docker-compose -f "$COMPOSE_FILE" logs -f "$service"
}

# Function to backup database
backup_database() {
    log_info "Creating database backup..."
    
    BACKUP_FILE="mikrokredit_backup_$(date +%Y%m%d_%H%M%S).sql"
    
    docker-compose -f "$COMPOSE_FILE" exec mikrokredit-postgres pg_dump -U mikrokredit_user -d mikrokredit_db > "$BACKUP_FILE"
    
    if [ -f "$BACKUP_FILE" ]; then
        log_info "Backup created: $BACKUP_FILE"
    else
        log_error "Failed to create backup"
        return 1
    fi
}

# Function to restore database
restore_database() {
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
        docker-compose -f "$COMPOSE_FILE" exec -T mikrokredit-postgres psql -U mikrokredit_user -d mikrokredit_db < "$BACKUP_FILE"
        log_info "Database restored successfully"
    else
        log_info "Restore cancelled"
    fi
}

# Function to migrate from Render
migrate_from_render() {
    log_info "Migrating data from Render PostgreSQL..."
    
    # Check if project is running
    if ! docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        log_error "Project is not running. Please start it first with: $0 start"
        return 1
    fi
    
    # Run migration script
    docker-compose -f "$COMPOSE_FILE" exec mikrokredit-web python scripts/migrate_to_local_postgres.py
    
    log_info "Migration completed"
}

# Function to connect to database
connect_database() {
    log_info "Connecting to database..."
    docker-compose -f "$COMPOSE_FILE" exec mikrokredit-postgres psql -U mikrokredit_user -d mikrokredit_db
}

# Function to show project info
show_info() {
    log_info "MikroKredit Project Information:"
    echo ""
    echo "Project Name: $PROJECT_NAME"
    echo "Network: $NETWORK_NAME"
    echo "Web Application: http://localhost:8002"
    echo "PostgreSQL: localhost:5434"
    echo "Database: mikrokredit_db"
    echo "User: mikrokredit_user"
    echo "Password: mikrokredit_pass_2024"
    echo ""
    echo "API Gateway Integration:"
    echo "- Gateway URL: http://api-gateway:8000"
    echo "- Redis Cache: redis://:Nitro@1941@redis_cache:6379"
    echo "- Shared Network: valstan_network"
    echo ""
    echo "Available Commands:"
    echo "  start     - Start the project"
    echo "  stop      - Stop the project"
    echo "  restart   - Restart the project"
    echo "  status    - Show project status"
    echo "  logs      - Show service logs"
    echo "  backup    - Create database backup"
    echo "  restore   - Restore database from backup"
    echo "  migrate   - Migrate data from Render"
    echo "  connect   - Connect to database"
    echo "  info      - Show project information"
}

# Main script logic
case "${1:-info}" in
    start)
        start_project
        ;;
    stop)
        stop_project
        ;;
    restart)
        restart_project
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$2"
        ;;
    backup)
        backup_database
        ;;
    restore)
        restore_database "$2"
        ;;
    migrate)
        migrate_from_render
        ;;
    connect)
        connect_database
        ;;
    info)
        show_info
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs [service]|backup|restore <file>|migrate|connect|info}"
        echo ""
        echo "MikroKredit Project Management Script"
        echo "Integrates with valstan_network and shared infrastructure"
        exit 1
        ;;
esac
