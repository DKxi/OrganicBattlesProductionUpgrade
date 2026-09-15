# Production Upgrade: Gunicorn + Uvicorn Worker ("GUvicorn") Integration Plan

**Document**: `changesforgunicorn.md`  
**Date**: September 15, 2026  
**Target Component**: Application Server & Deployment Layer  
**Objective**: Transition Organic Battles from single-process Uvicorn to high-throughput multi-worker Gunicorn using Uvicorn's ASGI worker engine (`uvicorn.workers.UvicornWorker`).

---

## 1. Architectural Motivation & Benefits

Running FastAPI directly via `uvicorn app:app` runs in a single process on a single CPU core. In production, multi-process management is required to:
1. **Utilize Multi-Core Hardware**: Scale throughput linearly across available vCPUs.
2. **Process Crash Resilience & Auto-Healing**: If a worker process encounters an unhandled fatal crash or OOM, the Gunicorn master process immediately spawns a fresh worker without dropping traffic.
3. **Graceful Zero-Downtime Reloads**: Seamlessly reload code and configuration (`kill -HUP <master_pid>`) without dropping active player connections.
4. **Memory Leak Mitigation**: Automatically recycle worker processes after serving $N$ requests (`max_requests` and `max_requests_jitter`).

---

## 2. Identified Application Readiness

Organic Battles is architecturally well-suited for multi-worker execution:
- **Stateless Application Layer**: Auth sessions (`OB_auth_sessions`) and active game states (`OB_game_sessions` with optimistic concurrency versioning) are stored in PostgreSQL/SQLite.
- **No DDL Startup Race Conditions**: `create_app()` does not execute Alembic migrations on startup; migrations are run decoupled via Alembic.
- **Connection Pool Awareness**: [`app/settings.py`](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/settings.py) and [`app/infrastructure/database/engine.py`](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/infrastructure/database/engine.py) already track `WEB_CONCURRENCY` to validate cluster-wide connection limits against Supabase poolers.

---

## 3. Required Changes Specification

### A. Dependencies Update
Add `gunicorn>=23.0.0` to project manifests:
- [`pyproject.toml`](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/pyproject.toml)
- [`requirements.txt`](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/requirements.txt)

### B. Production Gunicorn Configuration File (`gunicorn.conf.py`)
Create a standardized configuration file in the project root:
- **`worker_class`**: `"uvicorn.workers.UvicornWorker"`
- **`workers`**: Evaluates `WEB_CONCURRENCY` env var, defaulting to `(2 * CPU_COUNT) + 1` (capped for containerized environments).
- **`bind`**: Binds to `0.0.0.0:${PORT:-8000}`.
- **`timeout`**: Set to 120s to accommodate complex chemistry trials and cold database queries.
- **`graceful_timeout`**: 30s.
- **`max_requests` & `max_requests_jitter`**: 1500 requests with $\pm 100$ jitter to prevent thundering-herd worker recycling.
- **`accesslog` & `errorlog`**: Direct to stdout/stderr (`"-"`) for standard container log collectors.

### C. Dockerfile Modernization
Update [`Dockerfile`](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/Dockerfile) from:
```dockerfile
CMD ["sh","-c","uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
```
To:
```dockerfile
CMD ["sh", "-c", "gunicorn -c gunicorn.conf.py app.main:app"]
```

### D. Multi-Worker Rate Limiting (SlowAPI with Redis)
Update [`app/api/deps.py`](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/api/deps.py) to configure SlowAPI with `storage_uri=settings.redis_url` when `REDIS_URL` is defined, falling back to `"memory://"` for local offline development.

### E. Database Connection Pool Sizing per Worker
Ensure connection limits are calculated properly per worker:
$$\text{Total Connections} = \text{Workers} \times (\text{DB\_POOL\_SIZE} + \text{DB\_MAX\_OVERFLOW})$$
With Supabase default poolers:
- Default `pool_size = 3`
- Default `max_overflow = 2`
- Peak connections per worker = $5$. With 4 workers, total = $20$ connections (safely under the 60 limit).

---

## 4. Automated Verification Plan

1. **Unit & Configuration Tests** ([`tests/test_gunicorn_config.py`](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/tests/test_gunicorn_config.py)):
   - Validate `gunicorn.conf.py` syntax, attributes, and default values.
   - Verify `WEB_CONCURRENCY` override mechanism.
   - Verify `uvicorn.workers.UvicornWorker` class loading.
   - Verify `app.main:app` entrypoint compatibility with Gunicorn WSGI/ASGI spec.
   - Functional test: Start a local 2-worker Gunicorn server probe, verify `/` and `/health/live` respond with HTTP 200, then cleanly terminate.
2. **Full Regression Test Suite**:
   - Run `uv run pytest` (all 387+ tests).
   - Run `uvx ruff check .` for static analysis.
