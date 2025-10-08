# Gunicorn configuration file
import multiprocessing

# Server socket
bind = "127.0.0.1:8002"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "/home/valstan/development/mikrokredit/logs/access.log"
errorlog = "/home/valstan/development/mikrokredit/logs/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "mikrokredit"

# Server mechanics
daemon = False
pidfile = "/home/valstan/development/mikrokredit/mikrokredit.pid"
tmp_upload_dir = None

# SSL (if needed)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"

# Environment variables
raw_env = [
    'MIKROKREDIT_USE_SQLITE=1',
]

# Preload app
preload_app = True
