#!/bin/bash

# MikroKredit Web Application Startup Script

set -e

# Configuration
APP_DIR="/home/valstan/development/mikrokredit"
VENV_DIR="$APP_DIR/.venv"
GUNICORN_CONFIG="$APP_DIR/gunicorn.conf.py"
PID_FILE="$APP_DIR/mikrokredit.pid"
LOG_DIR="$APP_DIR/logs"

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

# Check if running as correct user
if [ "$USER" != "valstan" ]; then
    log_error "This script must be run as user 'valstan'"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    log_error "Virtual environment not found at $VENV_DIR"
    exit 1
fi

# Check if gunicorn config exists
if [ ! -f "$GUNICORN_CONFIG" ]; then
    log_error "Gunicorn config not found at $GUNICORN_CONFIG"
    exit 1
fi

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to start the application
start_app() {
    log_info "Starting MikroKredit Web Application..."
    
    # Check if already running
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        log_warn "Application is already running (PID: $(cat $PID_FILE))"
        return 0
    fi
    
    # Activate virtual environment and start gunicorn
    cd "$APP_DIR"
    source "$VENV_DIR/bin/activate"
    
    # Start gunicorn in background
    gunicorn --config "$GUNICORN_CONFIG" "web:create_app()" &
    echo $! > "$PID_FILE"
    
    # Wait a moment and check if it started successfully
    sleep 2
    if kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        log_info "Application started successfully (PID: $(cat $PID_FILE))"
        log_info "Application is available at: http://localhost:8002"
        log_info "Health check: http://localhost:8002/healthz"
    else
        log_error "Failed to start application"
        rm -f "$PID_FILE"
        exit 1
    fi
}

# Function to stop the application
stop_app() {
    log_info "Stopping MikroKredit Web Application..."
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            sleep 2
            if kill -0 "$PID" 2>/dev/null; then
                log_warn "Process didn't stop gracefully, forcing..."
                kill -9 "$PID"
            fi
            log_info "Application stopped"
        else
            log_warn "Process not running"
        fi
        rm -f "$PID_FILE"
    else
        log_warn "PID file not found, application may not be running"
    fi
}

# Function to restart the application
restart_app() {
    log_info "Restarting MikroKredit Web Application..."
    stop_app
    sleep 1
    start_app
}

# Function to show status
show_status() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        log_info "Application is running (PID: $(cat $PID_FILE))"
        log_info "Application is available at: http://localhost:8002"
    else
        log_warn "Application is not running"
    fi
}

# Main script logic
case "${1:-start}" in
    start)
        start_app
        ;;
    stop)
        stop_app
        ;;
    restart)
        restart_app
        ;;
    status)
        show_status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
