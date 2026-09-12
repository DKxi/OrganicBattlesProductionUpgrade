# Supabase Connection Pooling & Connection Strings Guide

This reference document explains how to set up the correct connection strings for **Supabase Connection Pooling** with SQLAlchemy in Organic Battles.

---

## 1. Choosing the Right Pooling Mode

Supabase provides two pooling modes via Supavisor. For **Organic Battles (FastAPI + SQLAlchemy)**, always use **Session Mode (Port 5432)**:

| Feature | **Session Mode (Port 5432)** ✅ *(Recommended)* | Transaction Mode (Port 6543) |
| :--- | :--- | :--- |
| **Why use it** | Supports **SQLAlchemy connection pools**, **Row-Level Security (`set_config`)**, transaction locks, and **role switching (`SET ROLE`)**. | Best for stateless serverless functions (e.g., AWS Lambda, Cloudflare Workers). |
| **Prepared statements** | Supported | Disallowed |
| **Port** | **`5432`** | `6543` |

---

## 2. Connection String Anatomy

When connecting via the Supabase Pooler (`pooler.supabase.com`), the username **must** include the project reference ID (`.<project_ref>`):

```text
postgresql+psycopg2://[username].[project_ref]:[password]@[pooler_host]:5432/postgres?sslmode=require
```

### Your Project Parameters:
- **Project Reference**: `aamwrwbsrmorllisdffc`
- **Pooler Host**: `aws-0-us-west-2.pooler.supabase.com`
- **Port**: `5432` (Session Mode)
- **Database**: `postgres`
- **SSL Mode**: `require`

---

## 3. Ready-to-Use Connection Strings

Add these connection strings to your [`local.env`](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/local.env) or [`prod.env`](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/prod.env) file:

### Option A: Standard Superuser Configuration (Single Role)
```bash
# Default / Superuser database connection
DATABASE_URL="postgresql+psycopg2://postgres.aamwrwbsrmorllisdffc:YOUR_PASSWORD@aws-0-us-west-2.pooler.supabase.com:5432/postgres?sslmode=require"
```

### Option B: Least-Privilege Role Configuration (Production Recommended)
```bash
# 1. Player Routes (Authentication, Game State, Combat Battles)
DATABASE_URL_PLAYER="postgresql+psycopg2://ob_player_api.aamwrwbsrmorllisdffc:YOUR_PLAYER_PASS@aws-0-us-west-2.pooler.supabase.com:5432/postgres?sslmode=require"

# 2. Admin Portal Routes (/api/admin/*)
DATABASE_URL_ADMIN="postgresql+psycopg2://ob_admin_api.aamwrwbsrmorllisdffc:YOUR_ADMIN_PASS@aws-0-us-west-2.pooler.supabase.com:5432/postgres?sslmode=require"

# 3. Question Ingestion Job (Standalone script)
DATABASE_URL_INGEST="postgresql+psycopg2://ob_content_ingest.aamwrwbsrmorllisdffc:YOUR_INGEST_PASS@aws-0-us-west-2.pooler.supabase.com:5432/postgres?sslmode=require"

# 4. Alembic Migration Runner (Assumes ob_owner)
DATABASE_URL_MIGRATION="postgresql+psycopg2://ob_migrator.aamwrwbsrmorllisdffc:YOUR_MIGRATOR_PASS@aws-0-us-west-2.pooler.supabase.com:5432/postgres?sslmode=require"
```

---

## 4. How to Inspect in Supabase Dashboard

1. Navigate to your project dashboard: [https://supabase.com/dashboard](https://supabase.com/dashboard).
2. Click the green **`Connect`** button in the top navigation bar.
3. Select **ORM** $\rightarrow$ choose **SQLAlchemy**.
4. Set **Mode** to **Session** (Port `5432`).
5. Verify the hostname and project reference match `aws-0-us-west-2.pooler.supabase.com` and `aamwrwbsrmorllisdffc`.

---

## 5. Important Rules

1. **SQLAlchemy Prefix**: Always use `postgresql+psycopg2://` instead of `postgresql://` so Python uses the psycopg2 driver.
2. **Username Suffix**: Always append `.<project_ref>` to the username when using the pooler (`aws-0-...pooler.supabase.com`). If omitted, Supavisor cannot identify your project tenant and rejects the connection with `FATAL: Tenant or user not found`.
3. **SSL Mode**: Always include `?sslmode=require` at the end of the connection string.
4. **Password Characters**: If your database password contains characters like `@`, `:`, `/`, or `#`, URL-encode them or use an alphanumeric password to avoid connection string parsing errors.
