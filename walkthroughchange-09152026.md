# Walkthrough: Production Gunicorn + UvicornWorker Deployment Migration

**Date:** September 15, 2026  
**Reference Document:** [changesforgunicorn.md](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/changesforgunicorn.md)  
**Status:** Completed & Validated  

---

## 1. Executive Summary

OrganicBattles has been transitioned from a standalone single-process `uvicorn` development server to an enterprise-ready **Gunicorn master process manager driving `uvicorn.workers.UvicornWorker` ASGI worker processes** ("guvicorn" architecture).

This migration provides:
- **Multi-Core Process Concurrency**: Bypasses Python's Global Interpreter Lock (GIL) by utilizing multiple worker processes scaled according to available CPU cores or explicit `WEB_CONCURRENCY` configuration.
- **Worker Process Supervision & Self-Healing**: Automatically detects crashed or hung workers (via heartbeat ping / timeouts) and transparently spawns healthy replacements without dropping incoming TCP connections.
- **Memory Leak Mitigation**: Employs `max_requests` (1,500) and randomized jitter (+/- 100 requests) to periodically recycle worker processes after handling high-volume workloads, preventing unbounded memory growth.
- **Graceful Zero-Downtime Reloads**: Supports `SIGHUP` rolling reload in production environments, replacing worker processes one by one without connection drops.
- **Multi-Worker Rate Limiting Support**: Pre-configured SlowAPI limiter storage with Redis backend support (`settings.redis_url`) with fallback to local memory.
- **Database Connection Pool Safety**: Database pool calculations in `app/infrastructure/database/engine.py` dynamically scale by `settings.web_concurrency`, ensuring total active connections stay well beneath Supabase limits.

---

## 2. Comprehensive Changes Implemented

### 2.1 Dependency Specifications & Virtual Environment Sync
- **[pyproject.toml](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/pyproject.toml)**: Added `gunicorn>=23.0.0` to the project dependencies.
- **[requirements.txt](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/requirements.txt)**: Added `gunicorn>=23.0.0` to ensure legacy and standard pip builds reflect the dependency.
- **[uv.lock](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/uv.lock)**: Updated lockfile and installed `gunicorn==26.2.0` in `.venv`.

### 2.2 Gunicorn Master Configuration File
Created **[gunicorn.conf.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/gunicorn.conf.py)** at the workspace root with production best practices:
- **Binding**: Dynamically binds to `${HOST:-0.0.0.0}:${PORT:-8000}`, adapting to container orchestration environments (Cloud Run, ECS, Kubernetes, Render).
- **Worker Class**: Configured to use `uvicorn.workers.UvicornWorker` to provide native ASGI execution for FastAPI with `asyncio` loop performance.
- **Worker Count**: Dynamically calculated as:
  ```python
  workers = int(os.getenv("WEB_CONCURRENCY")) if os.getenv("WEB_CONCURRENCY") else min(4, max(2, multiprocessing.cpu_count()))
  ```
- **Lifecycle & Memory Control**:
  - `max_requests = 1500`: Recycles worker after 1,500 requests to reclaim accumulated memory.
  - `max_requests_jitter = 100`: Randomizes recycling threshold to avoid simultaneous restarts across all workers ("thundering herd" restart).
  - `timeout = 60`: Worker timeout threshold in seconds.
  - `graceful_timeout = 30`: Grace period given to active workers to drain existing requests before termination.
  - `keepalive = 5`: Persistent HTTP connection keep-alive timeout.
- **Operational Hooks**:
  - `on_starting(server)`: Logs server initialization and process ID.
  - `when_ready(server)`: Logs operational readiness when all workers are listening.
  - `post_fork(server, worker)`: Logs worker initialization with worker ID and PID.
  - `worker_exit(server, worker)`: Logs worker retirement and exit status.

### 2.3 Container Packaging (Dockerfile)
Updated **[Dockerfile](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/Dockerfile)**:
- Replaced the single-worker development CMD:
  ```dockerfile
  # Previous:
  CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
  ```
  with the production Gunicorn configuration:
  ```dockerfile
  # Updated:
  CMD ["gunicorn", "-c", "gunicorn.conf.py", "-w", "2", "app.main:app"]
  ```

### 2.4 Distributed Rate Limiter
Updated **[app/api/deps.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/api/deps.py)**:
- Updated the SlowAPI `Limiter` instantiation to utilize `storage_uri=settings.redis_url if settings.redis_url else "memory://"`.
- When `REDIS_URL` is set, rate-limit buckets are synchronized across all Gunicorn worker processes.

### 2.5 Documentation Artifacts & References
- Created **[changesforgunicorn.md](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/changesforgunicorn.md)**: Detailed migration roadmap, architectural analysis, operational guidelines, and verification blueprint.
- Created **[walkthroughchange-09152026.md](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/walkthroughchange-09152026.md)**: This document.
- Updated **[README.md](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/README.md)**: Added Gunicorn + UvicornWorker to Technology Stack Matrix, added production server launch instructions, Docker execution commands, and updated automated test suite totals to 391.
- Updated **[cookbook.md](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/cookbook.md)**: Added Production Web Server layer to Technology Stack Matrix with multi-worker details and test count updates.
- Updated **[startupsteps.txt](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/startupsteps.txt)**: Added production multi-worker execution command alongside local development reload commands.
- Updated **[todo.md](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/todo.md)**: Marked Gunicorn supervision active with database session persistence.

---

## 3. New Automated Tests Added

Created **[tests/test_gunicorn_config.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/tests/test_gunicorn_config.py)** with comprehensive validation:

1. **`test_gunicorn_conf_defaults`**:
   - Validates that `gunicorn.conf.py` executes successfully.
   - Checks worker class is `uvicorn.workers.UvicornWorker`.
   - Checks `max_requests`, `max_requests_jitter`, `timeout`, `graceful_timeout`, and default worker calculation.
2. **`test_gunicorn_conf_environment_overrides`**:
   - Validates environment variable overrides for `WEB_CONCURRENCY`, `PORT`, `HOST`, and `TIMEOUT`.
   - Confirms that container environments with custom configs properly override defaults.
3. **`test_asgi_app_target_compatibility`**:
   - Loads the ASGI target `app.main:app`.
   - Confirms that the loaded object is callable and conforms to the ASGI specification signature (`scope`, `receive`, `send`).
4. **`test_live_multi_worker_gunicorn_probe`**:
   - Finds an open ephemeral port using `socket.bind(("127.0.0.1", 0))`.
   - Spawns a real background Gunicorn master process with 2 `uvicorn.workers.UvicornWorker` processes (`--workers 2`).
   - Polls `/health/live` to verify master and worker bootstrap.
   - Sends concurrent requests to `/health/live` and `/` root endpoint to verify worker request routing.
   - Issues `SIGTERM` to the master process and verifies clean worker termination without hanging processes.

---

## 4. Test Verification Results

### 4.1 Gunicorn Config & Probe Tests
```bash
$ uv run pytest tests/test_gunicorn_config.py -v
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-8.3.4, pluggy-1.6.0
rootdir: /Users/nkoneru/Downloads/AIApps/OrganicBattles
configfile: pyproject.toml
plugins: playwright-0.9.0, anyio-4.14.2, base-url-2.1.0
collected 4 items

tests/test_gunicorn_config.py::test_gunicorn_conf_defaults PASSED        [ 25%]
tests/test_gunicorn_config.py::test_gunicorn_conf_environment_overrides PASSED [ 50%]
tests/test_gunicorn_config.py::test_asgi_app_target_compatibility PASSED [ 75%]
tests/test_gunicorn_config.py::test_live_multi_worker_gunicorn_probe PASSED [100%]

============================== 4 passed in 1.37s ===============================
```

### 4.2 Code Quality & Static Analysis
```bash
$ uvx ruff check .
All checks passed!
```

### 4.3 Full Test Suite Execution
All unit, integration, concurrency, and release tests passed with zero regressions:
```bash
$ uv run pytest -q
390 passed, 1 skipped in 104.77s
```

---

## 5. How to Run and Operate

### Local Development / Quick Start
To launch the multi-worker server locally:
```bash
# Uses gunicorn.conf.py defaults (binds to 0.0.0.0:8000)
uv run gunicorn -c gunicorn.conf.py app.main:app
```

### Custom Worker & Port Configuration
```bash
# Run with 4 workers on port 8080 with 30s timeout
WEB_CONCURRENCY=4 PORT=8080 TIMEOUT=30 uv run gunicorn -c gunicorn.conf.py app.main:app
```

### Docker Container Build & Run
```bash
# Build production image
docker build -t organicbattles:latest .

# Run container with 4 workers on port 8000
docker run -p 8000:8000 -e WEB_CONCURRENCY=4 organicbattles:latest
```

### Rolling Reload Without Dropping Traffic
To reload code or config in a live production environment without dropping active client connections:
```bash
# Send SIGHUP to the Gunicorn master PID
kill -HUP <gunicorn_master_pid>
```
Gunicorn will start new workers with the updated configuration/code and gracefully terminate old workers once they finish inflight requests.
