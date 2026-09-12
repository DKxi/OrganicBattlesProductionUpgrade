# Supabase Least-Privilege Database Roles & Connection Strings Guide

This guide provides step-by-step instructions to create, secure, and configure the least-privilege PostgreSQL roles in Supabase for **Organic Battles**, construct role-specific connection strings, and update application environment files.

---

## Architecture Overview

Organic Battles separates database access into **4 application login roles** and **1 schema owner role**, retiring the superuser `postgres` role from web application runtime:

| Database Role | Role Type | Used By | Intended Access | Connection Limit |
| :--- | :--- | :--- | :--- | :--- |
| **`ob_owner`** | `NOLOGIN` | Schema / Table Owner | Owns all `OB_*` tables, views, and sequences. Never used by runtime web processes. Assumed only by `ob_migrator` via `SET ROLE ob_owner;`. | N/A |
| **`ob_player_api`** | `LOGIN` | Player Auth, Game, Battle routes | `SELECT` on published catalogs; `SELECT`/`INSERT`/`UPDATE` on player accounts, sessions, and progress. Enforced by PostgreSQL Row-Level Security (RLS). Zero access to admin tables. | 30 |
| **`ob_admin_api`** | `LOGIN` | Admin portal & management routes | `SELECT`, `INSERT`, `UPDATE`, `DELETE` across application, admin, and content tables. Zero DDL or schema alteration rights. | 8 |
| **`ob_content_ingest`** | `LOGIN` | Question import & release scripts | DML on content catalogs and release tables (`OB_curricula`, `OB_tracks`, `OB_questions`, `OB_bosses`, `OB_content_releases`). Zero access to player credentials or admin tables. | 2 |
| **`ob_migrator`** | `LOGIN` | Alembic / deployment jobs | Member of `ob_owner`. Runs database migrations in standalone CI/deployment pipelines. Zero web routes use this role. | 2 |

---

## Step 1: Run the Provisioning Script in Supabase SQL Editor

1. Log in to your **Supabase Dashboard**: [https://supabase.com/dashboard](https://supabase.com/dashboard).
2. Select your project (e.g., `OrganicBattles`).
3. In the left navigation sidebar, click **SQL Editor** (the `>_` terminal icon).
4. Click **New query**.
5. Copy and paste the entire contents of [`scripts/setup_supabase_least_privilege_roles.sql`](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/scripts/setup_supabase_least_privilege_roles.sql).
6. Click **Run** (or press `Cmd + Enter` / `Ctrl + Enter`).

> [!NOTE]
> The script executes as the `postgres` superuser. It creates the roles, transfers table ownership to `ob_owner`, applies explicit table grants/revokes, and establishes Row-Level Security (RLS) policies.

---

## Step 2: Set Strong Passwords for the Login Roles

In the same Supabase **SQL Editor**, generate and set unique, strong passwords for each of the 4 login roles.

Replace `<STRONG_PASSWORD_...>` below with random 24+ character passwords (avoid characters like `@`, `:`, `/`, `?`, `#` to prevent URL-encoding issues in connection strings, or use standard alphanumeric strings `A-Z`, `a-z`, `0-9`):

```sql
-- Set passwords for each login role:
ALTER ROLE ob_player_api WITH PASSWORD 'PlayerSecret_ChangeMe123_abc!';
ALTER ROLE ob_admin_api WITH PASSWORD 'AdminSecret_ChangeMe123_abc!';
ALTER ROLE ob_content_ingest WITH PASSWORD 'IngestSecret_ChangeMe123_abc!';
ALTER ROLE ob_migrator WITH PASSWORD 'MigratorSecret_ChangeMe123_abc!';
```

Click **Run** to execute.

---

## Step 3: Find Your Supabase Project Reference & Host

In your Supabase Dashboard:
1. Click the **Project Settings** (gear icon) in the bottom-left sidebar.
2. Under **Configuration**, click **Database**.
3. Scroll to the **Connection parameters** / **Connection string** section.

Note the two key values:
- **Project Reference ID**: (e.g., `aamwrwbsrmorllisdffc`)
- **Host / Pooler Host**:
  - **Connection Pooler (Recommended)**: `aws-0-us-west-2.pooler.supabase.com` (or your project's region)
  - **Direct Connection**: `db.<project_ref>.supabase.co`

---

## Step 4: Construct Role Connection Strings

Supabase supports two connection modes. Construct your connection strings using the format corresponding to your setup:

### Format A: Supabase Connection Pooler (Recommended for Web Processes)

When connecting via the Supabase pooler (`aws-0-...pooler.supabase.com`), the PostgreSQL username format is:
`[role_name].[project_ref]`

```bash
# 1. Player Web Process (Port 5432 - Session Mode)
DATABASE_URL_PLAYER="postgresql+psycopg2://ob_player_api.<PROJECT_REF>:<PLAYER_PASSWORD>@<POOLER_HOST>:5432/postgres?sslmode=require"

# 2. Admin Web Process (Port 5432 - Session Mode)
DATABASE_URL_ADMIN="postgresql+psycopg2://ob_admin_api.<PROJECT_REF>:<ADMIN_PASSWORD>@<POOLER_HOST>:5432/postgres?sslmode=require"

# 3. Question Ingestion Job (Port 5432 - Session Mode)
DATABASE_URL_INGEST="postgresql+psycopg2://ob_content_ingest.<PROJECT_REF>:<INGEST_PASSWORD>@<POOLER_HOST>:5432/postgres?sslmode=require"

# 4. Alembic Migration Job (Port 5432 - Direct or Session Mode)
DATABASE_URL_MIGRATION="postgresql+psycopg2://ob_migrator.<PROJECT_REF>:<MIGRATOR_PASSWORD>@<POOLER_HOST>:5432/postgres?sslmode=require"
```

### Format B: Direct Database Host (No Pooler)

When connecting directly to `db.<PROJECT_REF>.supabase.co:5432`, the username is simply the role name:

```bash
# 1. Player Web Process
DATABASE_URL_PLAYER="postgresql+psycopg2://ob_player_api:<PLAYER_PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres?sslmode=require"

# 2. Admin Web Process
DATABASE_URL_ADMIN="postgresql+psycopg2://ob_admin_api:<ADMIN_PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres?sslmode=require"

# 3. Question Ingestion Job
DATABASE_URL_INGEST="postgresql+psycopg2://ob_content_ingest:<INGEST_PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres?sslmode=require"

# 4. Alembic Migration Job
DATABASE_URL_MIGRATION="postgresql+psycopg2://ob_migrator:<MIGRATOR_PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres?sslmode=require"
```

> [!TIP]
> Always include `?sslmode=require` at the end of Supabase PostgreSQL connection strings.
> Always use `postgresql+psycopg2://` for SQLAlchemy in Python.

---

## Step 5: Configure Application Environment Files

Update your local or production environment files. 

### In `local.env` or `prod.env`:

```env
# ==============================================================================
# Least-Privilege Supabase Database Configuration
# ==============================================================================

# Default fallback (Player API role)
DATABASE_URL="postgresql+psycopg2://ob_player_api.aamwrwbsrmorllisdffc:YourPlayerPass@aws-0-us-west-2.pooler.supabase.com:5432/postgres?sslmode=require"

# Player routes (auth, game, combat)
DATABASE_URL_PLAYER="postgresql+psycopg2://ob_player_api.aamwrwbsrmorllisdffc:YourPlayerPass@aws-0-us-west-2.pooler.supabase.com:5432/postgres?sslmode=require"

# Admin routes (/api/admin/*)
DATABASE_URL_ADMIN="postgresql+psycopg2://ob_admin_api.aamwrwbsrmorllisdffc:YourAdminPass@aws-0-us-west-2.pooler.supabase.com:5432/postgres?sslmode=require"

# Standalone question ingestion script
DATABASE_URL_INGEST="postgresql+psycopg2://ob_content_ingest.aamwrwbsrmorllisdffc:YourIngestPass@aws-0-us-west-2.pooler.supabase.com:5432/postgres?sslmode=require"

# Standalone Alembic migrations runner
DATABASE_URL_MIGRATION="postgresql+psycopg2://ob_migrator.aamwrwbsrmorllisdffc:YourMigratorPass@aws-0-us-west-2.pooler.supabase.com:5432/postgres?sslmode=require"
```

> [!IMPORTANT]
> Never commit `local.env`, `prod.env`, `env`, or `.env` files to git. They are already listed in `.gitignore`.

---

## Step 6: Step-by-Step Verification & Testing

Verify that all permissions and security barriers are functioning as intended:

### 1. Run Alembic Migrations as `ob_migrator`
Execute migrations using the migration role:
```bash
uv run python -m app.infrastructure.database.alembic_runner
```
*Expected Result*: Connects via `DATABASE_URL_MIGRATION`, executes `SET ROLE ob_owner;`, and verifies the current revision matches `0008_least_privilege_roles_and_rls`.

### 2. Run Question Ingestion as `ob_content_ingest`
Ingest question content using the ingestion role:
```bash
uv run python scripts/ingest_questions_to_postgres.py --track default
```
*Expected Result*: Connects via `DATABASE_URL_INGEST`, populates questions and release records, and completes without attempting any DDL.

### 3. Verify Player Route Privilege Boundaries (Interactive SQL check)
In the Supabase SQL Editor, test the isolation barriers:

```sql
-- Test 1: ob_player_api CAN read published tracks
SET ROLE ob_player_api;
SELECT count(*) FROM public."OB_tracks";  -- Succeeds!

-- Test 2: ob_player_api CANNOT read admin users or credentials
SELECT count(*) FROM public."OB_admin_users";  -- ERROR: permission denied for table OB_admin_users

-- Test 3: ob_player_api CANNOT alter tables or create schema
DROP TABLE public."OB_users";  -- ERROR: permission denied for table OB_users

RESET ROLE;
```

### 4. Verify Admin Route Boundaries
```sql
-- Test: ob_admin_api CAN read admin tables, but CANNOT alter schema
SET ROLE ob_admin_api;
SELECT count(*) FROM public."OB_admin_users";  -- Succeeds!
ALTER TABLE public."OB_users" ADD COLUMN hacked text;  -- ERROR: must be owner of table OB_users

RESET ROLE;
```

### 5. Run Local Test Suite
Run the automated test suite to ensure all 365 regression tests pass:
```bash
uv run pytest tests/test_least_privilege_database_roles.py
uv run pytest
```

---

## Troubleshooting & FAQ

### Issue: `FATAL: Tenant or user not found`
- **Cause**: When using the Supabase pooler, omitting `.<project_ref>` from the username causes Supavisor to fail routing the connection.
- **Fix**: Ensure your username is `ob_player_api.<project_ref>` (e.g. `ob_player_api.aamwrwbsrmorllisdffc`), not just `ob_player_api`.

### Issue: `password authentication failed for user "ob_player_api"`
- **Cause**: Special characters in the password (such as `@`, `/`, or `:`) break URL parsing.
- **Fix**: Either URL-encode the special characters using Python (`urllib.parse.quote_plus("your_pass")`) or re-set the role password using alphanumeric characters only.

### Issue: `permission denied for schema public`
- **Cause**: Step 2 of `setup_supabase_least_privilege_roles.sql` was not run or revoked usage.
- **Fix**: Re-run `GRANT USAGE ON SCHEMA public TO ob_player_api, ob_admin_api, ob_content_ingest, ob_migrator;`.

### Issue: `permission denied for table alembic_version`
- **Cause**: Table ownership or grants for `alembic_version` need `ob_owner` assignment.
- **Fix**: Ensure `ALTER TABLE alembic_version OWNER TO ob_owner;` has been executed in the Supabase SQL Editor.
