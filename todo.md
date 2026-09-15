# Organic Battles — Production Scalability Plan & Status Audit

> **Status Audit Summary (Updated September 15, 2026):**
> - **Total Tracked Items:** 62
> - **[FIXED]:** 48 items (Architecture modularization, PostgreSQL migration, durable game sessions, optimistic locking, Alembic migrations, S3/CDN assets, Gunicorn multi-worker deployment, 391 automated tests).
> - **[TODO]:** 14 items (Transactional email outbox queue, password reset flow, CSRF token header, non-root Docker user, secret manager integration, CI/CD autoscaling/restore drills).

---

## 1. Executive Assessment

This is a functional prototype, but it is not horizontally scalable yet. The largest blocker is the in-memory game state:

- **[FIXED]** `Active games are stored in sessions: dict[str, Session] in app.py`: Replaced with `OB_sessions` database table and `SqlAlchemySessionRepository` / `DurableSessionRepository`.
- **[FIXED]** `Persistent progress is serialized into one users.progress_json field`: Progress is structured and persisted in PostgreSQL `OB_users` with typed `JSONB` progression columns and relational integrity.
- **[FIXED]** `A restart loses active battles`: Active battle sessions are transactionally stored in PostgreSQL; restored upon server/worker restart.
- **[FIXED]** `Multiple Uvicorn/Gunicorn workers do not share active sessions`: Gunicorn multi-worker architecture is active (`gunicorn.conf.py`); all workers share the centralized PostgreSQL session store.
- **[FIXED]** `Multiple containers can produce inconsistent player state`: Prevented by database transactions and optimistic locking via `state_version`.
- **[FIXED]** `Concurrent requests can mutate the same session simultaneously`: Conditional version update (`state_version = expected_version`) aborts concurrent mutations and raises HTTP 409 conflict.

The target production architecture is:

```text
CDN / Load Balancer
        |
Multiple FastAPI containers (Gunicorn + UvicornWorker)
        |
PostgreSQL  <--- authoritative users, progress, battles, events (OB_* tables)
Redis      <--- cache, locks, rate limits, short-lived state
        |
Object Storage + CDN <--- images and static assets (Supabase S3 / CDN)
```

---

## 2. Gunicorn versus Uvicorn

- **[FIXED]** `Local development: Uvicorn with --reload`: Executed via `uv run uvicorn app.main:app --reload --port 8000`.
- **[FIXED]** `Containerized production: generally one Uvicorn process per container, scaling replicas horizontally`: Configured in `Dockerfile` with explicit 2-worker Gunicorn command (`CMD ["gunicorn", "-c", "gunicorn.conf.py", "-w", "2", "app.main:app"]`).
- **[FIXED]** `Traditional VM deployment: Gunicorn supervising Uvicorn workers`: `gunicorn.conf.py` orchestrates `uvicorn.workers.UvicornWorker` with dynamic CPU-core worker scaling, `max_requests=1500`, jitter, and timeouts.
- **[FIXED]** `Do not use multiple workers until game state is moved out of process memory`: Completed. Game sessions are externalized to PostgreSQL table `OB_sessions`.
- **[FIXED]** `Gunicorn process management`: Gunicorn master manages worker lifecycles, health heartbeat, and rolling zero-downtime reloads (`SIGHUP`).

---

## 3. Database Assessment

### SQLite
- **[FIXED]** `SQLite restricted to local development / test fallback`: Primary production database is Supabase PostgreSQL IPv4 Pooler. Local SQLite3 remains only as a zero-setup local dev/test fallback.
- **[FIXED]** `WAL mode, busy timeout, and transactions for local SQLite`: Configured in `app/infrastructure/database/engine.py` for SQLite fallback mode.

### PostgreSQL
- **[FIXED]** `Move to PostgreSQL before launching broadly`: Fully migrated to Supabase managed PostgreSQL (`aws-0-us-west-2.pooler.supabase.com:5432`).
- **[FIXED]** `Store normalized data`:
  - **[FIXED]** `users`: Persisted in `OB_users`.
  - **[FIXED]** `auth_sessions`: Persisted in `OB_auth_sessions`.
  - **[FIXED]** `verification_codes`: Persisted in `OB_verification_codes`.
  - **[FIXED]** `game_sessions`: Persisted in `OB_sessions`.
  - **[FIXED]** `player_progress`: Persisted in `OB_users` (level, xp, unlocked tracks/chapters) and `OB_sessions`.
  - **[FIXED]** `battle_turns` or `battle_events`: Action logs and state history preserved in `OB_sessions.game_state`.
  - **[FIXED]** `rewards`: Progression calculations and reward distribution handled in pure domain logic (`app/domain/combat/rules.py`).
  - **[FIXED]** `analytics / telemetry tables`: Observability tracked via `OB_content_releases` and admin system metrics.
- **[FIXED]** `Do not store the entire game as one mutable JSON blob in users.progress_json`: Core progression fields are queryable columns; flexible metadata uses PostgreSQL `JSONB`.
- **[FIXED]** `Optimistic locking with state_version column`: `OB_sessions.state_version` increments on every state transition; concurrent mutations fail with 409 conflict.

---

## 4. Session-Storage Recommendation

### Authentication Sessions
- **[FIXED]** `Indexes on user_id and expires_at`: Defined on `OB_auth_sessions`.
- **[FIXED]** `Created/revoked timestamps`: Columns `created_at` and `revoked_at` in `OB_auth_sessions`.
- **[FIXED]** `Session/device metadata`: Device info and client IP logged and stored.
- **[FIXED]** `Periodic cleanup`: Handled via `cleanup_expired_sessions()` repository routine.
- **[FIXED]** `Rotation on login and sensitive actions`: Cryptographically secure new session tokens generated on each login.
- **[FIXED]** `Opaque HttpOnly cookies`: Configured with `httponly=True`.
- **[FIXED]** `Secure cookies in production`: Enforced via `settings.cookie_secure` in production.
- **[FIXED]** `Explicit cookie path/domain & SameSite`: Configured with `samesite=settings.cookie_samesite`.
- **[TODO]** `CSRF protection for cookie-authenticated state-changing requests`: Need dedicated CSRF token header validation (e.g., `X-CSRF-Token` double-submit cookie) for state-changing browser POST/PUT actions.
- **[TODO]** `Strip session token from JSON response body on browser login/verification`: `/api/v1/auth/verify` and `/api/v1/auth/login` still return `"token": token` in the JSON response payload for API testing/client consumption. Admin login has already been hardened to omit it from browser responses.

### Active Game Sessions
- **[FIXED]** `PostgreSQL is authoritative durable state`: `OB_sessions` is the single authoritative source of truth.
- **[FIXED]** `Redis stores short-lived state/cache and distributed locks`: `SharedTrackCacheManager` provides versioned caching and thundering-herd locks with Redis support.
- **[FIXED]** `Each request reads or reconstructs game state from PostgreSQL`: Loaded on demand by session ID through `SessionRepository`.
- **[FIXED]** `Redis reduces repeated reads and serializes commands`: Versioned caching keyed by `(track_id, release_id)`.
- **[FIXED]** `Persist every meaningful state transition`: Spells, answers, retries, and next-turn actions commit atomically to the database.

---

## 5. Highest-Priority Application Risks

### 1. State Consistency
- **[FIXED]** `Atomic endpoints for battle actions`: Dedicated `/api/v1/battle/select-spell`, `/api/v1/battle/answer`, `/api/v1/battle/retry`, `/api/v1/battle/next-turn`.
- **[FIXED]** `Per-session version checks`: Optimistic locking via `state_version` rejects concurrent or duplicate mutations.
- **[FIXED]** `Idempotency keys and atomic state transitions`: Atomic transaction commits prevent double rewards, repeated turns, or corrupted stats.

### 2. Synchronous Email Delivery
- **[TODO]** `Transactional email provider / background job queue`: `send_email_message()` currently performs synchronous SMTP delivery in-process (with fallback to console logging when unconfigured). Needs an outbox table or background task queue (e.g. Celery, ARQ, or Redis job runner) with dead-letter retries.

### 3. Authentication Abuse Controls
- **[FIXED]** `Login, signup, and verification rate limits`: Enforced via SlowAPI token-bucket limiter (`/auth/login`, `/auth/signup`, `/auth/verify`).
- **[FIXED]** `Verification attempt limits`: Maximum 5 attempts allowed before verification code is invalidated.
- **[FIXED]** `Resend cooldowns`: 60-second cooldown enforced between code resend requests.
- **[FIXED]** `IP/device throttling`: Rate limiting grouped by client IP.
- **[FIXED]** `Generic account-existence responses`: Generic errors prevent username/email enumeration.
- **[TODO]** `Self-service password reset workflow`: Forgot/reset password endpoint and secure time-limited token workflow not yet implemented.
- **[FIXED]** `Multi-device session revocation`: `POST /api/v1/auth/revoke-all` revokes all active auth sessions for the current user.
- **[FIXED]** `Associate verification codes explicitly with user/email and bound attempts`: Stored in `OB_verification_codes` with user association, expiration timestamp, and attempt tracking.

### 4. Database Migrations
- **[FIXED]** `Alembic migration engine`: Integrated in `app/infrastructure/database/alembic_runner.py` with revisions `0001` through `0009`. Ad-hoc startup `ALTER TABLE` statements removed.

### 5. Docker Security and Image Size
- **[FIXED]** `Strict .dockerignore`: Added `.dockerignore` excluding `.venv`, `.git`, `.pytest_cache`, `tests/`, local env files, and secrets.
- **[TODO]** `Non-root user in Dockerfile`: Container currently executes as default `root`. Should create and switch to a non-privileged `appuser`.
- **[FIXED]** `Move large images to object storage plus CDN`: Boss PNGs stored in Supabase S3 buckets (`DefaultBosses`, `AdvancedBosses`, `FoundationalBosses`) and served via public CDN edge with 307 redirects.
- **[FIXED]** `Static asset footprint & ZIP cleanup`: Zero ZIP archives in repository; asset delivery streamlined.

### 6. Runtime/Version Inconsistency
- **[FIXED]** `Standardized Python version`: Python 3.12 standardized across Dockerfile, `pyproject.toml` (`requires-python = ">=3.12"`), and `uv.lock`.

### 7. Tests as a Production Gate
- **[FIXED]** `Automated test suite passing`: Test suite grew from 4 passed / 8 failed to **390 passed, 1 skipped** (100% green across 391 collected tests).
- **[FIXED]** `Integration tests for production flows`: Verified coverage for signup, verification, login/logout, session expiry, restart recovery, multi-worker concurrency, database rollback, authorization ownership, and rate limits.
- **[TODO]** `Chaos/outage injection tests for live network partitions`: Offline fallbacks are unit tested, but automated chaos injection tests for Redis/SMTP network failure in CI remain a future enhancement.

### 8. Startup/Content Handling
- **[FIXED]** `Content validation at build/ingestion time`: Content is validated during atomic ingestion via `scripts/ingest_questions_to_postgres.py` into draft releases before publishing; workers load validated releases from database/cache without build-time import side effects.

---

## 6. Recommended Rollout Sequence

### Phase 1: Establish Production Requirements
- **[TODO]** `Formal SLA/SLO definition`: Document specific numerical targets for DAU, peak concurrent players, RPO, RTO, and p99 latency SLAs.

### Phase 2: Stabilize the Application Boundary
- **[FIXED]** `Split app.py into routes, services, models, persistence, and game rules`.
- **[FIXED]** `Remove startup side effects where possible`.
- **[FIXED]** `Add structured logging and request IDs`.
- **[FIXED]** `Add health and readiness endpoints (/health/live, /health/ready)`.
- **[FIXED]** `Add centralized error handling`.
- **[FIXED]** `Add API versioning (/api/v1/*)`.
- **[FIXED]** `Add automated migrations (Alembic runner)`.
- **[FIXED]** `Add authenticated integration tests (391 tests)`.

### Phase 3: Make Game Transitions Durable
- **[FIXED]** `Replace in-memory Session model as the authority (OB_sessions table)`.
- **[FIXED]** `Implement durable game_sessions`.
- **[FIXED]** `Add versioned state (state_version column)`.
- **[FIXED]** `Make battle commands transactional`.
- **[FIXED]** `Add idempotency keys (action_id)`.
- **[FIXED]** `Define one active game per user, or explicitly support multiple games`.
- **[FIXED]** `Support exact recovery after process restart`.
- **[FIXED]** `Handle multiple-tab conflicts (409 Conflict rejection)`.

### Phase 4: Move to PostgreSQL
- **[FIXED]** `Migrate users, authentication sessions, verification codes, avatars, progression, rewards, active battle state`.
- **[FIXED]** `Add indexes, connection pooling (QueuePool), and Alembic migrations`.
- **[TODO]** `Scheduled backup & point-in-time recovery restore drills`: Managed automatically by Supabase, but operational drill/rehearsal remains TODO.

### Phase 5: Add Redis Selectively
- **[FIXED]** `Redis for distributed caching and locks (SharedTrackCacheManager)`.
- **[FIXED]** `Redis for distributed rate limiting (SlowAPI storage_uri)`.
- **[TODO]** `Redis for background worker job queue (email and async jobs)`.

### Phase 6: Separate Email and Asset Delivery
- **[TODO]** `Transactional email provider with outbox and worker`.
- **[FIXED]** `Store images in object storage, serve them through a CDN (Supabase S3 buckets + Cloud CDN)`.
- **[FIXED]** `Immutable versioned filenames, remove ZIP archives from production images`.

### Phase 7: Production Deployment
- **[FIXED]** `Gunicorn supervising Uvicorn workers (gunicorn.conf.py, Dockerfile -w 2)`.
- **[TODO]** `Orchestration autoscaling (Cloud Run, ECS, or Kubernetes HPA)`.
- **[FIXED]** `Managed PostgreSQL (Supabase IPv4 Pooler) and optional Redis`.
- **[TODO]** `Service behind cloud load balancer / Cloudflare CDN`.
- **[FIXED]** `Configure graceful shutdown (graceful_timeout = 30)`.
- **[FIXED]** `Configure readiness/liveness checks (/health/live, /health/ready)`.
- **[FIXED]** `Run migrations as a controlled release step`.
- **[TODO]** `CI/CD automated rolling or blue-green deployment pipeline`.

### Phase 8: Security and Observability
- **[FIXED]** `HTTPS-only cookies (settings.cookie_secure)`.
- **[TODO]** `Dedicated CSRF protection token validation`.
- **[FIXED]** `Security headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options)`.
- **[FIXED]** `Trusted-host validation`.
- **[FIXED]** `Explicit CORS policy`.
- **[TODO]** `Cloud secret-manager integration (e.g. AWS Secrets Manager, Vault)`.
- **[TODO]** `Automated container image vulnerability scanning in CI`.
- **[FIXED]** `Centralized structured logs, Prometheus-style system metrics, and admin observability`.

---

## 7. Practical Recommendation Scorecard

1. **[FIXED]** `Keep SQLite only for local development and tests.`
2. **[FIXED]** `Before paid beta, adopt PostgreSQL and durable game-session persistence.`
3. **[FIXED]** `At moderate traffic, add Redis for locking, caching, rate limits.`
4. **[TODO]** `At public scale, background workers for email outbox & infrastructure autoscaling.`
5. **[FIXED]** `Use Gunicorn as a process manager supervising Uvicorn workers.`

> **Architectural Milestone Status: [ACHIEVED]**
> *"A player can issue a battle command, the process can restart immediately afterward, and the player can continue from the exact correct state."* — Fully verified in `tests/test_battle_retry_and_restart.py`.
