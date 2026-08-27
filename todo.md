# Organic Battles — Production Scalability Plan

## Executive assessment

This is a functional prototype, but it is not horizontally scalable yet. The largest blocker is the in-memory game state:

- Active games are stored in `sessions: dict[str, Session]` in `app.py`.
- Persistent progress is serialized into one `users.progress_json` field.
- A restart loses active battles.
- Multiple Uvicorn/Gunicorn workers do not share active sessions.
- Multiple containers can produce inconsistent player state.
- Concurrent requests can mutate the same session simultaneously.

The target production architecture is:

```text
CDN / Load Balancer
        |
Multiple FastAPI containers
        |
PostgreSQL  <--- authoritative users, progress, battles, events
Redis      <--- cache, locks, rate limits, short-lived state
        |
Object Storage + CDN <--- images and static assets
```

## Gunicorn versus Uvicorn

“Unicorn” likely means **Gunicorn**.

- Local development: Uvicorn with `--reload`.
- Containerized production: generally one Uvicorn process per container, scaling replicas horizontally.
- Traditional VM deployment: Gunicorn supervising Uvicorn workers.
- Do not use multiple workers until game state is moved out of process memory.

Gunicorn improves process management and concurrency, but it does not solve the current architecture. Every worker would still have its own independent `sessions` dictionary.

The official Uvicorn deployment guidance recommends Gunicorn for production, while noting that the older `uvicorn.workers` module is being deprecated in favor of the separate `uvicorn-worker` package.

## Database assessment

### SQLite

SQLite is acceptable for local development, automated tests, a single-instance private beta, and very low write traffic.

It is a poor primary database for this paid production application because:

- Battle actions write frequently.
- SQLite has limited concurrent-write capacity.
- Multiple containers cannot safely share a local SQLite file.
- Container filesystems may be ephemeral.
- There is no managed failover or straightforward horizontal scaling.
- `save_game_progress()` rewrites the entire serialized state after many requests.
- There is no visible migration framework or production backup process.

If SQLite must temporarily remain, use WAL mode, a busy timeout, explicit transactions, a persistent volume, scheduled backups, restore testing, indexes, cleanup jobs, and a single application instance. Treat this as an interim stage only.

### PostgreSQL

Move to PostgreSQL before launching broadly. Store normalized data such as:

- `users`
- `auth_sessions`
- `verification_codes`
- `game_sessions`
- `player_progress`
- `battle_turns` or `battle_events`
- `rewards`
- Optional analytics tables

Do not store the entire game as one mutable JSON blob in `users.progress_json`. JSONB can remain useful for flexible fields, but core progression should be queryable and transactionally updated.

Every battle command should load the current state, verify an expected version, apply exactly one transition, increment the version, and persist the result transactionally. Use optimistic locking with a `state_version` column.

## Session-storage recommendation

There are two separate session types.

### Authentication sessions

The current `auth_sessions` table is conceptually appropriate. Keep durable authentication sessions in PostgreSQL and add:

- Indexes on `user_id` and `expires_at`
- Created/revoked timestamps
- Session/device metadata
- Periodic cleanup
- Rotation on login and sensitive actions
- Opaque HttpOnly cookies
- Secure cookies in production
- Explicit cookie path/domain
- CSRF protection for cookie-authenticated state-changing requests

Currently login and verification return the token in JSON as well as setting an HttpOnly cookie. This weakens the benefit of the HttpOnly cookie because JavaScript can access the returned token.

### Active game sessions

Do not use the process-local dictionary in production.

Recommended approach:

- PostgreSQL is the authoritative durable state.
- Redis stores short-lived state/cache and distributed locks.
- Each request reads or reconstructs game state from PostgreSQL.
- Redis reduces repeated reads and serializes commands for one player.
- Persist every meaningful state transition.

Redis alone should not be the only source of truth for paid-user progression unless persistence and recovery are carefully designed.

## Highest-priority application risks

### 1. State consistency

These endpoints mutate the same in-memory object:

- `/api/battle/select-spell`
- `/api/battle/answer`
- `/api/battle/retry`
- `/api/battle/next-turn`

There is no per-session lock or version check. Double-clicks, retries, multiple tabs, or browser races can cause duplicate rewards, incorrect HP, repeated answers, lost progress, invalid cooldowns, and state overwrites.

Add idempotency keys and atomic state transitions.

### 2. Synchronous email delivery

`send_verification_email()` performs SMTP work directly inside signup/resend requests. This can tie up worker capacity, increase latency, fail during provider outages, and create poor retry behavior.

Use a transactional email provider or background job system with an outbox, retry policy, dead-letter handling, delivery status, and rate limits.

### 3. Authentication abuse controls

Add login, signup, and verification-code rate limits; verification attempt limits; resend cooldowns; IP/device throttling; generic account-existence responses; password reset; and multi-device session revocation.

Associate verification codes explicitly with the intended user/email and bound their attempts.

### 4. Database migrations

The current startup migration uses an ad hoc `ALTER TABLE` with a broad exception. Use Alembic or another real migration system. Migrations should run as a deployment step, not implicitly in every worker startup.

### 5. Docker security and image size

The Dockerfile uses `COPY . .`, which can copy `.env`, `secrets.toml`, SQLite files, ZIP archives, test caches, and development artifacts into the image.

Create a strict `.dockerignore`, keep secrets out of the build context, use a non-root user, and move large images to object storage plus CDN.

Static assets are approximately 233 MB, with additional large ZIP archives in the repository. This will slow builds and increase image size.

### 6. Runtime/version inconsistency

The Docker image uses Python 3.12 while `pyproject.toml` declares Python `>=3.14`. Dependency definitions are also split between `requirements.txt` and `pyproject.toml`.

Choose one supported Python version and one locked dependency strategy.

### 7. Tests are not currently a production gate

The test run produced 4 passed and 8 failed. The failures occur because the tests call `/api/game/new` without authentication while the endpoint now requires authentication, returning HTTP 401.

Add integration tests for signup/verification, login/logout, session expiry, restart recovery, multi-worker behavior, duplicate battle commands, concurrent actions, database rollback, Redis outage, email failure, authorization ownership, and rate limits.

### 8. Startup/content handling

The app loads content and validates assets during module import. With multiple workers, this repeats per worker. Local startup also emits many missing-image warnings and appears to contain encoding problems in some chemistry names.

Validate content in CI or at build time instead of discovering missing assets during production startup.

## Recommended rollout sequence

### Phase 1: Establish production requirements

Define daily active users, peak concurrent players, requests per second, latency targets, recovery point objective, recovery time objective, uptime target, and expected asset bandwidth.

### Phase 2: Stabilize the application boundary

- Split `app.py` into routes, services, models, persistence, and game rules.
- Remove startup side effects where possible.
- Add structured logging and request IDs.
- Add health and readiness endpoints.
- Add centralized error handling.
- Add API versioning.
- Add automated migrations.
- Add authenticated integration tests.

### Phase 3: Make game transitions durable

- Replace the in-memory `Session` model as the authority.
- Implement durable `game_sessions`.
- Add versioned state.
- Make battle commands transactional.
- Add idempotency keys.
- Define one active game per user, or explicitly support multiple games.
- Support exact recovery after process restart.
- Handle multiple-tab conflicts.

This is the most important engineering phase.

### Phase 4: Move to PostgreSQL

Migrate users, authentication sessions, verification codes, avatars, progression, rewards, and active battle state. Add indexes, connection pooling, migrations, backups, point-in-time recovery, and restore drills.

### Phase 5: Add Redis selectively

Use Redis for distributed per-player locks, rate limiting, short-lived caches, email queues, state cache, and idempotency-key storage. Do not move permanent progression exclusively into Redis.

### Phase 6: Separate email and asset delivery

Use a transactional email provider with an outbox and worker. Store images in object storage, serve them through a CDN, use immutable versioned filenames, compress/resize images, and remove ZIP archives and duplicate assets from production images.

### Phase 7: Production deployment

- One Uvicorn process per container.
- Scale containers through the orchestration platform.
- Use managed PostgreSQL and Redis.
- Put the service behind a load balancer/CDN.
- Configure graceful shutdown.
- Configure readiness/liveness checks.
- Run migrations as a controlled release step.
- Use rolling or blue-green deployments.

For a single VM initially, Gunicorn with Uvicorn workers is reasonable, but only after state is externalized. Do not deploy multiple workers while active state remains in `sessions`.

### Phase 8: Security and observability

Add HTTPS-only cookies, CSRF protection, security headers, trusted-host validation, explicit CORS policy if needed, secret-manager integration, dependency/container scanning, database encryption and backups, centralized logs, metrics, and alerting.

## Practical recommendation

1. Keep SQLite only for local development and tests.
2. Before paid beta, adopt PostgreSQL and durable game-session persistence.
3. At moderate traffic, add Redis for locking, caching, rate limits, and jobs.
4. At public scale, use stateless containers, managed database services, CDN/object storage, background workers, and observability.
5. Use Gunicorn as a process manager where appropriate; it is not a substitute for externalizing state.

The first architectural milestone should be: **a player can issue a battle command, the process can restart immediately afterward, and the player can continue from the exact correct state.**
