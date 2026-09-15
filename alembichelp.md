# Alembic Migrations & Supabase Database Architecture Guide

**Date:** September 15, 2026  
**Topic:** Alembic Schema Migrations, Application Usage, and Safe Operations on Network-Separated Supabase Databases  

---

## 1. What is an Alembic Migration?

**Alembic** is the official database schema migration tool for Python applications built on SQLAlchemy.

Think of Alembic as **"Git for database structure"**:
- **Code vs Schema Tracking**: Just as Git tracks file line changes across commits, Alembic tracks relational schema changes (tables, columns, indexes, foreign keys, and constraints) across versioned migration scripts.
- **Revision History**: Each migration script in `migrations/versions/` has a unique revision ID (e.g. `0001_initial_schema`, `0002_jsonb_conversion`, `0009_query_performance_indexes`).
- **State Tracking Table**: Alembic tracks which migrations have already been applied to a database by checking a single 1-row table named `alembic_version` inside the database.
- **Strictly Additive and Non-Destructive**: Alembic migrations in Organic Battles are additive (e.g. `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`). They **never** drop tables, truncate rows, or wipe existing business data.

---

## 2. Where is this Application Using Alembic?

Alembic is organized across four key areas in the repository:

### 2.1 Configuration & Migration Scripts
- **[alembic.ini](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/alembic.ini)**: Root configuration file defining the migration directory path and logging behavior.
- **[migrations/env.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/migrations/env.py)**: The migration execution environment that inspects SQLAlchemy models from [app/infrastructure/database/models.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/infrastructure/database/models.py) and applies connection settings dynamically.
- **[migrations/versions/](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/migrations/versions/)**: Contains all 9 versioned schema migrations:
  1. `0001_initial_schema.py`: Baseline tables (`OB_users`, `OB_auth_sessions`, `OB_sessions`, `OB_questions`, `OB_tracks`, `OB_curricula`).
  2. `0002_jsonb_conversion.py`: PostgreSQL native `JSONB` conversion for options and spell definitions.
  3. `0003_content_releases.py`: Atomic content releases table (`OB_content_releases`).
  4. `0004_stable_question_identity_constraints.py`: Unique composite index on `(track_id, release_id, chapter, order_index)`.
  5. `0005_game_session_active_question_identity.py`: Question identity binding in active game sessions.
  6. `0006_optimistic_locking.py`: `state_version` column on `OB_sessions` to prevent combat race conditions.
  7. `0007_search_indexes.py`: PostgreSQL `pg_trgm` trigram indexes for question search.
  8. `0008_least_privilege_roles_and_rls.py`: Database role permissions and security grants.
  9. `0009_query_performance_indexes.py`: Composite query performance indexes.

### 2.2 Programmatic Migration Runner
- **[app/infrastructure/database/alembic_runner.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/infrastructure/database/alembic_runner.py)**:
  - Exposes `run_alembic_migrations(target_engine)` to run pending migrations programmatically via Python.
  - Exposes `get_current_migration_revision()` to inspect the current revision without modifying the database.
  - Used for deployment pipelines and automated testing.

### 2.3 Administrative Sync Endpoint (On-Demand Only)
- **[app/api/v1/admin.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/api/v1/admin.py#L744)**:
  - Provides a protected endpoint (`POST /api/v1/admin/system/schema/sync`) allowing authenticated administrators to trigger a schema sync on demand. It is never triggered automatically by regular user traffic.

### 2.4 Automated Test Suite
- **[tests/test_alembic_migrations.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/tests/test_alembic_migrations.py)**:
  - Runs in CI/CD against ephemeral test databases to verify that schema migrations execute from revision 0 to head cleanly.

---

## 3. Working with Existing Supabase Data on a Separate Network Host

### 3.1 Your Data on Supabase is 100% Safe
If you already have populated tables on a remote Supabase host, the application will **not** alter, wipe, or drop your data:

1. **Zero DDL on Server Startup**:
   - The FastAPI factory `create_app()` in [app/main.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/main.py) **does NOT execute migrations or DDL statements on startup**.
   - Verified by test `tests/test_least_privilege_database_roles.py::test_create_app_does_not_invoke_ensure_db_schema`.
   - When Gunicorn / Uvicorn starts up, it connects to Supabase in **least-privilege runtime mode**, executing only application queries (`SELECT`, `INSERT`, `UPDATE`).
2. **State-Aware Revision Checking**:
   - Even if `alembic upgrade head` is executed manually, Alembic first reads `alembic_version`. If the target revision has already been applied, it immediately exits without executing any SQL.
3. **No Destructive Operations**:
   - None of the migration scripts contain `DROP TABLE`, `TRUNCATE`, or destructive data commands.

### 3.2 Connecting to Your Remote Supabase Database
Because your Supabase database lives on a physically separate network, the application connects over secure TLS/SSL via the Supabase connection pooler.

Configure your connection string in your environment (e.g. `prod.env` or Docker environment):
```bash
# Supabase Transaction Pooler (port 5432 or 6543)
DATABASE_URL=postgresql://postgres.YOUR_PROJECT_REF:YOUR_PASSWORD@aws-0-us-west-2.pooler.supabase.com:5432/postgres?sslmode=require
```

### 3.3 How the Application Reads Your Existing Supabase Tables
Once connected, the application immediately reads and serves your existing data:
- **Questions & Curricula**: Queries `OB_content_releases`, `OB_questions`, and `OB_tracks`. If questions are already ingested into published releases, players receive them immediately.
- **Player Accounts & Progression**: User records and saved levels in `OB_users` are preserved and loaded directly.
- **Active Combat Sessions**: Loaded on demand from `OB_sessions`.
- **Authentication**: Validated against `OB_auth_sessions`.

---

## 4. Helpful Alembic Commands (CLI Reference)

All commands should be run using `uv run` from the project root:

| Command | Description | Modifies Data? |
|---|---|:---:|
| `uv run alembic current` | Displays the current migration revision hash applied to the database. | **No** (Read-Only) |
| `uv run alembic heads` | Shows the latest available migration revision in the code repository. | **No** (Read-Only) |
| `uv run alembic history` | Displays the full linear chronological list of all migrations. | **No** (Read-Only) |
| `uv run alembic check` | Compares the database schema against SQLAlchemy models to detect drift. | **No** (Read-Only) |
| `uv run alembic upgrade head` | Applies any *new* pending migrations up to the latest revision. | Structural Only (Additive) |

---

## 5. Summary Checklist

- [x] **Alembic is a version-control tool for database schemas**, not an automatic data-wiping script.
- [x] **The application does not run Alembic migrations on startup**; Gunicorn runs in pure application query mode.
- [x] **Existing data in Supabase is completely preserved**; connecting to your remote host only performs reads and standard gameplay writes.
- [x] **Connection over the network** is handled cleanly via standard PostgreSQL SSL connection strings (`DATABASE_URL`).
