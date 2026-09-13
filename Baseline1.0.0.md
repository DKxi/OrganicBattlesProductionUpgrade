# Production Baseline v1.0.0 Specification

**Release Version**: `1.0.0`  
**Git Tag**: `v1.0.0`  
**Git Baseline Branch**: `baseline/v1.0.0`  
**Base Commit**: `78eac92` (`chore(release): bump version to 1.0.0 for production security baseline`)  
**CI Workflow Commit**: `c63a4cd` (`ci: add GitHub Actions workflow for automated Ruff linting`)  
**Date**: September 13, 2026  
**Target Runtime**: Python 3.12+ / FastAPI / PostgreSQL 15+ / Redis 7+  

---

## 1. Executive Summary

`v1.0.0` represents the audited, production-hardened baseline for the **Organic Battles** platform. It establishes an immutable reference point following comprehensive modularization, database security overhaul, atomic content releases, pure domain combat rules, observability telemetry, and automated CI quality gating.

All 384 unit, integration, and security regression tests are passing (100% green).

---

## 2. Core Architecture & Components

```
OrganicBattles/
├── .github/workflows/         # CI/CD pipelines (Automated Ruff Linting)
├── app/
│   ├── api/                   # Presentation Layer (FastAPI Routers & Endpoints)
│   │   ├── deps.py            # Dependency Injection & Token Auth
│   │   ├── errors.py          # Standardized RFC 7807 Error Envelopes
│   │   └── v1/                # Versioned Endpoints (auth, battle, admin, analytics)
│   ├── domain/                # Pure Business Logic (No DB / HTTP Dependencies)
│   │   ├── combat/            # Deterministic Combat Engine (rules, spells, entities)
│   │   ├── content/           # Release Resolver, Bundle Loader, Payload Validator
│   │   └── progression/       # Avatars, Ranks, Mastery Scoring
│   ├── infrastructure/        # External Systems & Adapters
│   │   ├── database/          # SQLAlchemy Models, Alembic Migrations, Repositories
│   │   ├── cache/             # SharedTrackCacheManager (Redis + Local Fallback)
│   │   ├── identity/          # PBKDF2 (310k rounds), Timing-Safe Verification
│   │   ├── messaging/         # SMTP Verification & Worker Queues
│   │   └── storage/           # S3 Client Streaming (Supabase Storage)
│   ├── observability/         # RED Metrics, Structured Logging, Connection Telemetry
│   ├── main.py                # FastAPI App, Middleware Stack (CSP, HSTS, CORS)
│   └── settings.py            # Pydantic Settings with Strong Env Parsing
├── migrations/                # Alembic Migrations (Versions 0001–0009)
├── pyproject.toml             # Python 3.12 Dependencies, Ruff Config, Pytest Options
└── tests/                     # 384 Regression & Playwright Browser Tests
```

---

## 3. Production Hardening Milestones in `v1.0.0`

### A. Security & Identity
- **Password Security**: Hardened PBKDF2 hashing using 310,000 SHA-256 iterations (`PBKDF2_ITERATIONS = 310_000`) with cryptographic salt generation.
- **Session Ownership Guardrails**: Timing-safe identity comparisons (`secrets.compare_digest`) prevent player session hijacking and cross-tenant access.
- **Strict Browser Headers**:
  - `Content-Security-Policy`: Restricts scripts, styles, and assets to trusted origins (`self`, Supabase CDN, Google Fonts, cdnjs).
  - `Strict-Transport-Security`: `max-age=63072000; includeSubDomains; preload`.
  - `X-Content-Type-Options`: `nosniff`.
  - `X-Frame-Options`: `DENY`.
- **Cookie Policy**: `HttpOnly`, `SameSite=Lax`, and `Secure=True` enforced across all auth endpoints.
- **Rate Limiting**: Configured Slowapi middleware on auth routes (`/api/auth/login`, `/api/auth/signup`).

### B. Database & Connection Management
- **Table Namespacing**: All models standardized under unified `OB_` table prefixing (`OB_users`, `OB_game_sessions`, `OB_questions`, `OB_tracks`, `OB_content_releases`, etc.).
- **Least-Privilege Roles**: Defined 5 operational database roles:
  1. `ob_player`: DML on gameplay sessions and player progress.
  2. `ob_admin`: DML on administrative models and audit logs.
  3. `ob_content_ingest`: Targeted write access to questions, releases, and curriculum tables.
  4. `ob_migrator`: DDL execution rights for Alembic migrations.
  5. `ob_owner`: Full database management.
- **Dual Connection Pools**:
  - `SessionLocal`: Scaled connection pool for standard gameplay traffic with connection recycling and timeout guards.
  - `AdminSessionLocal`: Isolated pool with separate capacity for admin queries, metrics, and migration tasks.
- **Alembic Baseline**: Migrations 0001 through 0009 tracked and verified in PostgreSQL.

### C. Content Pipeline & Zero-Drift Shared Cache
- **Atomic Release Lifecycle**:
  - `OB_content_releases` manages draft, published, and archived versions.
  - Questions are ingested into draft releases first; live players are never exposed to partial imports.
  - Instant cluster-wide rollbacks supported via `POST /api/v1/admin/tracks/{track_id}/releases/{version}/rollback`.
- **Shared Track Cache (`SharedTrackCacheManager`)**:
  - Cache keys versioned by `(track_id, release_id)` eliminating invalidation drift.
  - Per-track threading lock prevents thundering herd on cache misses.
  - Redis backing with automatic, seamless fallback to bounded in-memory LRU tier.
  - S3 streaming reader pulls question bundles and assets directly from cloud buckets.

### D. Pure Domain Combat Engine
- **Deterministic Combat**: Domain combat rules (`evaluate_combat_turn`, `apply_spell_cooldown`, `decrement_cooldowns`) are completely isolated from HTTP requests and database sessions.
- **Mathematical Balance**:
  - Player starting health: 150 HP.
  - Offensive spell catalog: `Fire Spark` (20 DMG), `Resonance Burst` (30 DMG), `Mechanism Storm` (45 DMG).
  - Spell backfiring: Incorrect answers fizzle the cast and apply full spell base power as recoil damage directly to the player.
  - Cooldown tracking: Pure time-based cooldown validation prevents turn skipping and replay exploitation.

### E. Observability & Telemetry
- **Metrics Registry (`app/observability/metrics.py`)**:
  - Continuous measurement of 9 production dimensions: RED metrics (Rate, Errors, Duration), Cache Hit Ratio, Database Connection Pool Saturation, and Bundle Memory Footprints.
- **Health Probes**:
  - `/health/live`: Liveness check for orchestrators (Kubernetes / ECS).
  - `/health/ready`: Deep readiness probe checking database and cache connectivity.

### F. CI/CD & Automated Code Quality
- **GitHub Actions Pipeline (`.github/workflows/lint.yml`)**:
  - Triggers on `push` and `pull_request` to `main`, plus manual `workflow_dispatch`.
  - Automated concurrency cancellation (`cancel-in-progress: true`).
  - Runs Astral `ruff` on native Python 3.12 with GitHub workflow annotations.
- **Ruff Configuration (`pyproject.toml`)**:
  - Standard rules: `E`, `F`, `W`.
  - Protected per-file ignores for framework re-exports (`app/api/deps.py`, `app.py`).

---

## 4. Verification & Test Suite Results

| Test Category | Command | Result | Duration |
|:---|:---|:---:|:---:|
| **Full Regression Suite** | `uv run pytest -q` | **383 passed, 1 skipped** (100% green) | 94.90s |
| **Static Analysis / Lint** | `uvx ruff check .` | **0 errors** (All checks passed) | 0.82s |
| **Playwright WebKit / Safari** | `python tests/ui_test_suite.py` | **100% passed** (All UI flows green) | 28.40s |

---

## 5. Git Baseline References

- **Tag**: `v1.0.0`
- **Branch**: `baseline/v1.0.0`
- **Remote URL**: `https://github.com/DKxi/OrganicBattlesProductionUpgrade.git`
- **Checkout Command**:
  ```bash
  git checkout tags/v1.0.0
  # or
  git checkout baseline/v1.0.0
  ```
