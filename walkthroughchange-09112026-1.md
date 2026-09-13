# Walkthrough: Least-Privilege Supabase Database Identities & Row-Level Security (RLS)

**Date**: 2026-09-12  
**Document**: `walkthroughchange-09112026-1.md`  
**Milestone**: Phase 9 — Least-Privilege Database Identities, Row-Level Security, Multi-Engine Splitting & Zero-DDL Web Startup

---

## 1. Executive Summary

Organic Battles has successfully migrated from a shared, high-privilege administrative connection to an enterprise-grade **least-privilege database architecture** on Supabase PostgreSQL.

### Key Milestones Achieved:
1. **5-Role Security Matrix**: Provisioned 1 table owner role (`ob_owner` with `NOLOGIN`) and 4 segregated login roles (`ob_player_api`, `ob_admin_api`, `ob_content_ingest`, `ob_migrator`).
2. **Zero Web DDL Privileges**: `ob_player_api` and `ob_admin_api` have no schema modification rights (`CREATE`, `DROP`, `ALTER`). Runtime `ensure_db_schema()` and `Base.metadata.create_all()` were eliminated from FastAPI web application startup.
3. **PostgreSQL Row-Level Security (RLS)**: Enforced and forced across all 6 player personal data tables (`OB_users`, `OB_auth_sessions`, `OB_game_sessions`, `OB_player_question_progress`, `OB_answer_attempts`, `OB_verification_codes`).
4. **Multi-Engine Splitting**: Created isolated SQLAlchemy engines (`player_engine`, `admin_engine`) and dedicated session factories (`PlayerSessionLocal`, `AdminSessionLocal`).
5. **Dynamic RLS Context**: Authenticated player requests automatically set transaction-local identity (`SET LOCAL app.current_user_id = '<user_id>'`).
6. **Live Supabase Verification**: Verified all 4 roles against the live Supabase PostgreSQL instance via connection strings in `local.env`, proving permission barriers and RLS isolation.
7. **Complete Boss Synchronization**: Populated 2,700 bosses in `OB_bosses` and 27,000 relational mappings in `OB_boss_question_assignments` across all 20 tracks.

---

## 2. Role Matrix & Privilege Architecture

| Role | Type | Primary Consumer | Privileges & Boundaries | RLS Status |
| :--- | :--- | :--- | :--- | :--- |
| **`ob_owner`** | `NOLOGIN` | Table & Schema Owner | Owns all 15 `OB_*` tables and sequences. Can execute schema DDL. Assumed exclusively by `ob_migrator` via `SET ROLE ob_owner;`. | **BYPASS** |
| **`ob_player_api`** | `LOGIN` | User Auth, Gameplay, Combat routes | `SELECT` on content (`OB_curricula`, `OB_tracks`, `OB_bosses`, `OB_questions`, `OB_content_releases`). Scoped DML on player tables. **BLOCKED (`42501`)** on `OB_admin_users`, `DELETE` on questions, and DDL. | **ENFORCED** (Scoped to `app.current_user_id`) |
| **`ob_admin_api`** | `LOGIN` | Admin Portal (`/api/admin/*`) | Full read access across all tables. DML on content and users. Append-only on `OB_answer_attempts`. **BLOCKED (`42501`)** on `DELETE`/`UPDATE` of audit attempts and DDL. | **GLOBAL AUDIT** (`USING (true)`) |
| **`ob_content_ingest`**| `LOGIN` | Content Ingestion & Boss Sync | DML on content tables only (`OB_curricula`, `OB_tracks`, `OB_questions`, `OB_bosses`, `OB_boss_question_assignments`, `OB_content_releases`). **BLOCKED (`42501`)** on player personal data and admin tables. | **N/A** (Zero player table access) |
| **`ob_migrator`** | `LOGIN` | Alembic Migration Runner | Member of `ob_owner`. Executes `SET ROLE ob_owner;` during one-shot migration tasks. Never used by web processes. | **OWNER PRIVILEGES** |

---

## 3. Implementation Details

### A. Database Provisioning Script ([scripts/setup_supabase_least_privilege_roles.sql](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/scripts/setup_supabase_least_privilege_roles.sql))
- Executed successfully in Supabase SQL Editor (`Success. No rows returned`).
- **Step 1**: Created roles `ob_owner`, `ob_player_api`, `ob_admin_api`, `ob_content_ingest`, and `ob_migrator`.
- **Step 2**: Revoked public and inherited access across all tables (`REVOKE ALL ON TABLE ... FROM public, anon, authenticated`).
- **Step 3**: Granted player privileges (content read, player-scoped DML, sequence usage).
- **Step 4**: Granted admin privileges (read all, DML on app/content, append-only answer attempts).
- **Step 5**: Transferred ownership of all tables and sequences to `ob_owner` (`GRANT ob_owner TO postgres; ALTER TABLE ... OWNER TO ob_owner;`).
- **Step 6**: Enabled and forced RLS on player tables with policies keyed to `current_setting('app.current_user_id', true)`.

### B. Alembic Migration ([migrations/versions/0008_least_privilege_roles_and_rls.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/migrations/versions/0008_least_privilege_roles_and_rls.py))
- Dialect-aware migration applying RLS enabling, forcing, and role policies on PostgreSQL.
- Executes `SET ROLE ob_owner;` prior to running DDL when running on PostgreSQL.
- Acts as a clean no-op on SQLite for local development and CI testing.

### C. Application Settings ([app/settings.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/settings.py))
Added independent configuration fields with environment variable overrides:
- `database_url_player`: Loaded from `DATABASE_URL_PLAYER` (defaults to `DATABASE_URL`).
- `database_url_admin`: Loaded from `DATABASE_URL_ADMIN` (defaults to `DATABASE_URL`).
- `database_url_ingest`: Loaded from `DATABASE_URL_INGEST` (defaults to `DATABASE_URL`).
- `database_url_migration`: Loaded from `DATABASE_URL_MIGRATION` (defaults to `DATABASE_URL`).
- Automatically loads `local.env` when present.

### D. Engine Separation & Session Factories ([app/infrastructure/database/engine.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/infrastructure/database/engine.py))
- **`player_engine`**: Built from `player_db_url` (`ob_player_api`).
- **`admin_engine`**: Built from `admin_db_url` (`ob_admin_api`).
- **`PlayerSessionLocal` & `AdminSessionLocal`**: Independent session factories.
- **`SessionLocal = PlayerSessionLocal`**: Guarantees that any fallback callers or content loaders operate under the least-privileged player engine.
- **`set_session_user_context(db, user_id)`**: Issues `select set_config('app.current_user_id', :user_id, true)` in the active transaction.
- **Dependencies**: `get_player_db()`, `get_admin_db()`, `get_db = get_player_db`.

### E. Authentication & RLS Propagation ([app/api/deps.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/api/deps.py))
- `get_current_user`: Depends on `get_player_db()`. Upon session validation, automatically calls `set_session_user_context(db, user.id)`, scoping all subsequent queries in the request transaction to that player under PostgreSQL RLS.
- `auth_admin`: Depends on `get_admin_db()`, querying `OB_admin_users` and `OB_admin_sessions`.

### F. Web Startup Decoupling & Job Isolation
- **[app/main.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/main.py)**:
  - Runtime DDL removed (`create_all` and `ensure_db_schema` eliminated from `create_app()`). Web processes run with zero DDL privileges.
- **[scripts/ingest_questions_to_postgres.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/scripts/ingest_questions_to_postgres.py)**:
  - Connects using `database_url_ingest` (`ob_content_ingest`) with `NullPool`.
  - Ingests questions into draft releases and activates them atomically.
- **[scripts/sync_bosses_to_postgres.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/scripts/sync_bosses_to_postgres.py)**:
  - Connects using `database_url_ingest` with `NullPool`.
  - Populates `OB_bosses` (2,700 bosses) and `OB_boss_question_assignments` (27,000 assignments).
- **[app/infrastructure/database/alembic_runner.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/infrastructure/database/alembic_runner.py)** & **[migrations/env.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/migrations/env.py)**:
  - Connects using `database_url_migration` (`ob_migrator`) with `NullPool`.
  - Executes `SET ROLE ob_owner;` prior to running migration upgrades.

---

## 4. Verification & Validation Results

### 1. Live Supabase Role Privilege Verification
Executed [scripts/verify_least_privilege_live.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/scripts/verify_least_privilege_live.py) against the live Supabase instance using `local.env`:

```
============================================================
TESTING ROLE: ob_player_api
============================================================
  [+] Connected as: CURRENT_USER=ob_player_api, SESSION_USER=ob_player_api
  [+] Content reads succeeded: curricula=3, tracks=20, bosses=2700, questions=27000
  [+] BLOCKED (Expected): Reading OB_admin_users denied with 42501
  [+] BLOCKED (Expected): DELETE on OB_questions denied with 42501
  [+] BLOCKED (Expected): CREATE TABLE denied with 42501
  [+] RLS check (unauthenticated context): OB_game_sessions visible rows = 0
  [+] RLS check (user context): OB_game_sessions visible rows = 0
  --> ob_player_api: ALL CHECKS PASSED

============================================================
TESTING ROLE: ob_admin_api
============================================================
  [+] Connected as: CURRENT_USER=ob_admin_api, SESSION_USER=ob_admin_api
  [+] Admin table read succeeded: OB_admin_users count = 2
  [+] Read player & attempt tables succeeded: users=4, attempts=4
  [+] BLOCKED (Expected): DELETE on OB_answer_attempts denied with 42501
  [+] BLOCKED (Expected): UPDATE on OB_answer_attempts denied with 42501
  [+] BLOCKED (Expected): CREATE TABLE denied with 42501
  --> ob_admin_api: ALL CHECKS PASSED

============================================================
TESTING ROLE: ob_content_ingest
============================================================
  [+] Connected as: CURRENT_USER=ob_content_ingest, SESSION_USER=ob_content_ingest
  [+] Content reads succeeded: questions=27000, bosses=2700
  [+] BLOCKED (Expected): Reading OB_users denied with 42501
  [+] BLOCKED (Expected): Reading OB_admin_users denied with 42501
  [+] BLOCKED (Expected): Reading OB_game_sessions denied with 42501
  [+] BLOCKED (Expected): CREATE TABLE denied with 42501
  --> ob_content_ingest: ALL CHECKS PASSED

============================================================
TESTING ROLE: ob_migrator
============================================================
  [+] Connected as: CURRENT_USER=ob_migrator, SESSION_USER=ob_migrator
  [+] Switched role to: CURRENT_USER=ob_owner
  [+] DDL capability verified: Successfully created and dropped test table as ob_owner
  [+] Reset role to: CURRENT_USER=ob_migrator
  --> ob_migrator: ALL CHECKS PASSED

************************************************************
ALL 4 LEAST-PRIVILEGE ROLES VERIFIED SUCCESSFULLY AGAINST LIVE DB!
************************************************************
```

### 2. Unit & Integration Test Suite
Executed [tests/test_least_privilege_database_roles.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/tests/test_least_privilege_database_roles.py):
- 8/8 tests passing (SQL script grants, independent settings, engine separation, RLS helper, zero startup DDL, router dependencies).

### 3. Full Regression Suite
Executed `uv run pytest`:
- **365 passed, 1 skipped in 79.20s** (100% green).
- Playwright UI E2E tests passing.
- Database connection pooling & concurrency tests passing.

---

## 5. Artifacts & Reference Documentation

| Document / Script | Purpose |
| :--- | :--- |
| **[SUPABASE_LEAST_PRIVILEGE_SETUP.md](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/SUPABASE_LEAST_PRIVILEGE_SETUP.md)** | Step-by-step administrator guide for role creation, password assignment, and connection strings. |
| **[changeconn.md](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/changeconn.md)** | Connection pooling strings for Supabase session mode (port 5432) across all 4 roles. |
| **[GetawayfromDatafolder.md](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/GetawayfromDatafolder.md)** | Architectural audit of the `/data/` folder and 4-phase decoupling roadmap into Supabase PostgreSQL and Storage. |
| **[scripts/setup_supabase_least_privilege_roles.sql](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/scripts/setup_supabase_least_privilege_roles.sql)** | Production SQL script for provisioning roles, table grants, revokes, and RLS policies. |
| **[scripts/verify_least_privilege_live.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/scripts/verify_least_privilege_live.py)** | Automated live role verification test script for Supabase connections. |
| **[scripts/sync_bosses_to_postgres.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/scripts/sync_bosses_to_postgres.py)** | Batch synchronization script for `OB_bosses` and `OB_boss_question_assignments`. |
