import os

# Render assigns a dynamic port via the PORT environment variable (default 10000)
port = os.environ.get("PORT", "10000")
bind = f"0.0.0.0:{port}"

# Concurrency and timeout settings optimized for Render cloud instances
workers = int(os.environ.get("WEB_CONCURRENCY", "1"))
threads = int(os.environ.get("PYTHON_THREADS", "4"))
timeout = 120
keepalive = 5

# Stream logs directly to stdout/stderr for Render log capture
accesslog = "-"
errorlog = "-"
loglevel = "info"
