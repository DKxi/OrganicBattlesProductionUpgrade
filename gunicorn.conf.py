"""
Organic Battles - Production Gunicorn Configuration File.
Orchestrates multi-worker FastAPI execution via Uvicorn's ASGI worker engine.
"""

import os
import multiprocessing

# 1. Server Socket Binding
host = os.getenv("HOST", "0.0.0.0")
port = os.getenv("PORT", "8000")
bind = f"{host}:{port}"

# 2. Worker Processes & Concurrency
# Uvicorn's high-performance uvloop ASGI worker class
worker_class = "uvicorn.workers.UvicornWorker"

# Automatic worker scaling: (2 x cores) + 1, capped to 8 by default in containerized environments
cpu_cores = multiprocessing.cpu_count()
calculated_workers = min(8, max(2, (cpu_cores * 2) + 1))
workers = int(os.getenv("WEB_CONCURRENCY", os.getenv("WORKERS", str(calculated_workers))))

# 3. Connection & Timeout Policies
# Generous timeout for complex chemistry trial queries, asset loading, and cold-start queries
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))

# 4. Memory Leak Prevention & Process Recycling
# Automatically recycle worker after handling N requests (with randomized jitter to prevent thundering herd)
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "1500"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "100"))

# 5. Logging Configuration
accesslog = os.getenv("GUNICORN_ACCESSLOG", "-")
errorlog = os.getenv("GUNICORN_ERRORLOG", "-")
loglevel = os.getenv("LOG_LEVEL", "info").lower()


def post_fork(server, worker):
    """Callback invoked immediately after a worker has been forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)


def worker_exit(server, worker):
    """Callback invoked when a worker exits."""
    server.log.info("Worker exited cleanly (pid: %s)", worker.pid)
