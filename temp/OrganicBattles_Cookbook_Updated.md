# Organic Battles V3 — Engineering Cookbook

Verified against repository commit `f821848d37bfc597a732928358ad2dbe9ba19d23` (September 11, 2026).

This is an operator and contributor guide for the code that exists today. It separates current behavior from recommended production behavior so that known weaknesses do not accidentally become deployment instructions.

## 1. What is in the repository

Organic Battles is a FastAPI learning game for organic chemistry. A player selects a curriculum track, chooses a spell, answers a question, and applies damage based on the result. PostgreSQL stores users, sessions, game state, releases, questions, assignments, attempts, and mastery. Source JSON files remain the authoring/import format and can be an explicitly enabled fallback.

Current inventory:

| Item | Verified value |
|---|---:|
| Python target | 3.12+ |
| Application version | 3.0.0 |
| Question tracks | 20 |
| Real curricula | 2 (`advanced`, `foundational`) |
| Chapter JSON files | 568 |
| Source questions | 28,400 |
| Database tables | 15, all prefixed `OB_` |
| Test files | 34 |
| Front end | Vanilla JavaScript, CSS, Phaser 3.80.1 |

`all` in `data/tracks_config.json` is a UI filter, not a third curriculum.

```mermaid
flowchart TD
    B["Browser UI"] --> API["FastAPI /api/v1 and /api"]
    API --> AUTH["Auth and game services (ob_player / ob_admin_api)"]
    API --> CONTENT["Content loader"]
    AUTH --> DB["PostgreSQL with RLS & Roles, or SQLite"]
    CONTENT --> DB
    CONTENT --> CACHE["Bounded LRU cache; optional Redis (ob: prefix, JSON schema)"]
    CONTENT -->|"explicit fallback only"| JSON["Validated source JSON"]
```

Both `/api/v1` and `/api` expose the same routers. The second prefix exists for the current front end and backward compatibility; new clients should use `/api/v1`.

## 2. Repository map

| Path | Purpose | Guidance |
|---|---|---|
| `app/main.py` | FastAPI application factory and route registration | Canonical application entry point |
| `app/api/v1/` | Auth, game, battle, admin, question, and analytics routes | Add API behavior here |
| `app/domain/` | Combat, content loading, validation, and cache logic | Keep framework-independent rules here |
| `app/infrastructure/database/` | Canonical engine, schema, models, and repositories | Use this database layer for new work |
| `app/infrastructure/cache/` | Local and Redis content caches | Redis serialization needs hardening before production |
| `data/` | Track catalog, question JSON, images, audio, and bosses | Source content and fallback data |
| `scripts/` | Import, cache warming, and content utilities | Review destructive behavior before use |
| `static/`, `templates/` | Browser application | Served directly by FastAPI |
| `tests/` | Unit, integration, security, and optional UI tests | Live-database tests are not cleanly marked |
| `app.py` | Compatibility export for `app:app` | Used by the Docker command |
| `models.py` | Compatibility adapter | Prefer canonical models |
| `database.py` | Older, separate engine implementation | Do not use for new code |
| `session_repository.py` | Older repository implementation | Do not use; canonical repository enforces ownership |
| `main.py` | Hello-world scaffold | Not the game server |

The repository includes Alembic as a dependency but has no Alembic migration environment. Schema creation and legacy adjustments currently happen in application code.

## 3. Safe local start

### Prerequisites

- Python 3.12+
- PostgreSQL for production-like work, or SQLite for isolated development
- Redis only if shared caching is intentionally enabled

The safest first run uses SQLite and an explicit process environment. This avoids touching the database URL currently committed in the repository.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

export DATABASE_URL='sqlite:///./organic_battles.sqlite3'
export ALLOW_JSON_FALLBACK='true'
export COOKIE_SECURE='0'

uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

With `uv` installed, `uv sync --locked` is the reproducible alternative because `uv.lock` is committed.

Useful URLs:

- Game: `http://127.0.0.1:8000/`
- OpenAPI: `http://127.0.0.1:8000/docs`
- Liveness: `http://127.0.0.1:8000/healthz`
- Readiness: `http://127.0.0.1:8000/readyz`

Startup creates or updates the schema, seeds track metadata and bosses, and currently seeds administrator accounts. Do not expose a fresh instance publicly until the production blockers in section 12 are resolved.

## 4. Configuration

Configuration resolution is currently:

1. Process environment
2. Values in `secrets.toml` for selected settings
3. Built-in default

At import time, the first existing dotenv file is loaded in this order: explicit `ENV_FILE`, `local.env`, `env`, `.env`, then `prod.env`. Because `local.env` precedes `prod.env`, merely setting `ENVIRONMENT=production` does not select `prod.env`.

Recommended production practice: inject environment variables through the deployment platform. If a file is unavoidable, remove secrets from Git, set `ENV_FILE` explicitly, restrict its permissions, and mount it outside the image.

| Variable | Purpose | Current default/behavior |
|---|---|---|
| `ENV_FILE` | Explicit dotenv filename | Otherwise uses first file in the order above |
| `ENVIRONMENT` | Environment label | `development` |
| `DATABASE_URL` | SQLAlchemy connection URL | Must be supplied securely |
| `DATABASE_URL_PLAYER` | Player/auth/game API database identity | Recommended replacement for player routes |
| `DATABASE_URL_ADMIN` | Admin API database identity | Recommended replacement for admin routes |
| `DATABASE_URL_INGEST` | Content import/release identity | Recommended for controlled import jobs only |
| `DATABASE_URL_MIGRATION` | Schema-owner migration identity | Recommended for deployment jobs only |
| `DATABASE_PATH` | SQLite path fallback | `organic_battles.sqlite3` |
| `DB_POOL_SIZE` | Connections retained per process | Supabase 3; other PostgreSQL 5; SQLite 5 |
| `DB_MAX_OVERFLOW` | Burst connections per process | Supabase 2; other PostgreSQL 10; SQLite 0 |
| `DB_POOL_TIMEOUT` | Pool wait, seconds | 30 |
| `DB_POOL_RECYCLE` | Connection recycle, seconds | 1,800 |
| `WEB_CONCURRENCY` | Web processes per replica | 1 |
| `APP_REPLICAS` | Replica count used in pool estimate | 1 |
| `DB_MAX_CONNECTIONS_LIMIT` | Warning threshold | 60 |
| `MAX_CACHED_TRACKS` | In-process cache bound | 4 |
| `TRACK_CACHE_TTL_SECONDS` | Local cache TTL | 3,600 |
| `REDIS_URL` | Shared cache connection | Disabled when unset |
| `ALLOW_JSON_FALLBACK` | Permit source JSON if DB/cache fails | False |
| `POPULAR_TRACKS` | Track list for warming script | Three named tracks |
| `WARM_TRACKS_ON_STARTUP` | Intended startup warming flag | Defined but not wired into startup |
| `VERIFICATION_CODE_TTL_SECONDS` | Email-code lifetime | 900 |
| `AUTH_SESSION_TTL_DAYS` | Player session lifetime | 30 |
| `ADMIN_SESSION_TTL_HOURS` | Admin session lifetime | 24 |
| `COOKIE_SECURE` | Secure player cookie | False |
| `COOKIE_SAMESITE` | Player cookie SameSite | `lax` |
| `SMTP_*` | Verification email transport | No working mail without configuration |

Connection capacity is approximately:

```text
(DB_POOL_SIZE + DB_MAX_OVERFLOW) × WEB_CONCURRENCY × APP_REPLICAS
```

Leave room for migrations, administrative tools, background jobs, and provider-reserved connections.

### Supabase password and environment-file remediation

The Supabase password found in the reviewed repository must be treated as compromised. Removing it from the current branch does not invalidate it and does not remove it from Git history. The safe order is:

1. Configure the existing connection string as a secret in the FastAPI hosting platform so the application no longer depends on a tracked file.
2. Remove every hardcoded URL and password from application code and tracked environment files.
3. Deploy that code and confirm it reads the runtime secret successfully.
4. Reset the database password in Supabase.
5. Replace the deployed secret immediately and restart every FastAPI worker and replica.
6. Verify the new password works and the old password fails.
7. Decide whether repository history must be rewritten after the credential has been revoked.

Supabase recommends creating a separate database user for every external service instead of sharing the powerful `postgres` account. It also notes that external applications must be updated manually after the project password changes. See [Supabase Postgres roles](https://supabase.com/docs/guides/database/postgres/roles).

#### Remove the hardcoded connection strings

At the reviewed revision, the credential appeared in:

- `local.env`
- `prod.env`
- `app/settings.py` as `DEFAULT_POSTGRES_URL`
- `app/api/v1/admin.py` as a PostgreSQL fallback

Delete both code fallbacks. Production should fail during startup if its database secret is absent:

```python
def resolve_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    if os.getenv("ENVIRONMENT", "development") == "production":
        raise RuntimeError("DATABASE_URL must be configured in production")

    return f"sqlite:///{ROOT_DIR / 'organic_battles.sqlite3'}"
```

Do not expose the resolved URL through an API response, admin configuration page, exception message, metric, or log. The production runtime database-switching endpoint should be removed; at minimum, it must never accept or return raw credentials.

#### Protect environment files

Add these rules to `.gitignore`:

```gitignore
.env
.env.*
local.env
prod.env
env
secrets.toml

# The placeholder template is safe to commit.
!.env.example
```

Stop tracking files that are already committed:

```bash
git rm --cached local.env prod.env env
git add .gitignore
git commit -m "Remove database credentials from tracked environment files"
```

Name only files that actually exist. Commit a placeholder-only `.env.example`:

```dotenv
ENVIRONMENT=development
DATABASE_URL_PLAYER=postgresql+psycopg2://PLAYER_ROLE:PASSWORD@HOST:5432/postgres
DATABASE_URL_ADMIN=postgresql+psycopg2://ADMIN_ROLE:PASSWORD@HOST:5432/postgres
DATABASE_URL_INGEST=postgresql+psycopg2://INGEST_ROLE:PASSWORD@HOST:5432/postgres
DATABASE_URL_MIGRATION=postgresql+psycopg2://MIGRATION_ROLE:PASSWORD@HOST:5432/postgres
ALLOW_JSON_FALLBACK=true
COOKIE_SECURE=0
```

Real local values may be stored in an ignored `.env`; production values belong in the hosting platform's secret store. Never bake them into the Docker image. Generate every password independently with a password manager.

#### Rotate the Supabase project password

1. Open the Organic Battles project in Supabase.
2. Open **Project Settings → Database**.
3. Reset the database password.
4. Store the new password in a password manager.
5. Open **Connect** and copy the correct direct or pooler host information.
6. Update the hosting secret and restart all application processes.
7. Test readiness, login, question loading, answer submission, and an authorized admin update.

Reserved password characters must be percent-encoded when placed inside a connection URL. A safer code pattern is to store components separately and construct the URL with SQLAlchemy:

```dotenv
PLAYER_DB_HOST=HOST_FROM_SUPABASE_CONNECT
PLAYER_DB_PORT=5432
PLAYER_DB_NAME=postgres
PLAYER_DB_USER=ob_player_api.PROJECT_REF
PLAYER_DB_PASSWORD=GENERATED_SECRET
```

```python
from sqlalchemy import URL

player_url = URL.create(
    drivername="postgresql+psycopg2",
    username=os.environ["PLAYER_DB_USER"],
    password=os.environ["PLAYER_DB_PASSWORD"],
    host=os.environ["PLAYER_DB_HOST"],
    port=int(os.getenv("PLAYER_DB_PORT", "5432")),
    database=os.getenv("PLAYER_DB_NAME", "postgres"),
    query={"sslmode": "require"},
)
```

For a shared Supabase pooler, a custom database role uses the username `[ROLE].[PROJECT-REF]`. Persistent VMs and long-running containers can use the direct connection when IPv6 is available; the session pooler on port 5432 is the normal IPv4 alternative. Copy the host rather than constructing it. See [Supabase database connections](https://supabase.com/docs/guides/database/connecting-to-postgres).

#### Remove the old secret from Git history

Rotate first. GitHub explains that history rewriting changes commit hashes, affects pull requests and collaborators, and can be re-contaminated by an old clone. See [GitHub's sensitive-data removal guide](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).

For a coordinated cleanup from a fresh mirror clone, remove the tracked secret files with `git-filter-repo`:

```bash
git filter-repo --sensitive-data-removal \
  --invert-paths \
  --path local.env \
  --path prod.env
```

Because the URL also appeared in Python source, use `git filter-repo --replace-text` with a protected local replacement file containing the old credential. Do not delete `app/settings.py` or `app/api/v1/admin.py` from history. Coordinate the force-push, close or merge open pull requests first, and require collaborators to re-clone. Enable GitHub secret scanning, push protection, and Gitleaks afterward.

### Least-privilege Supabase database identities

Organic Battles should not run its web application as Supabase's `postgres` role. Use four separate login roles:

| Database role | Used by | Intended access |
|---|---|---|
| `ob_player_api` | Player auth, game, and battle routes | Read published content; write player account/session/progress rows only |
| `ob_admin_api` | Authenticated admin routes | Read and update application/admin/content records; no schema ownership or DDL |
| `ob_content_ingest` | Question import and release job | Content catalog and release DML only; no player credentials or admin accounts |
| `ob_migrator` | Alembic/deployment job | Schema changes; never loaded by the web process |

Use an additional `ob_owner` role with `NOLOGIN` as the owner of Organic Battles tables. Only `ob_migrator` may temporarily assume it during a controlled migration. This prevents a stolen web password from altering table definitions even if a grant is accidentally widened.

The existing Supabase roles `anon`, `authenticated`, `authenticator`, and `service_role` belong to Supabase's Data API/Auth model. Do not repurpose them as SQLAlchemy login accounts. Create custom roles for the FastAPI server. Supabase distinguishes grants, which decide which operations a role may attempt, from RLS policies, which decide which rows the operation may affect. Both are required for strong isolation. See [Supabase RLS guidance](https://supabase.com/docs/guides/database/postgres/row-level-security).

#### Step 1: Create the login roles

Run the role creation through a controlled migration or the Supabase SQL Editor while connected as `postgres`. Create the roles without passwords first:

```sql
create role ob_owner
  nologin nosuperuser nocreatedb nocreaterole noinherit noreplication;

create role ob_player_api
  login nosuperuser nocreatedb nocreaterole noinherit noreplication
  connection limit 30;

create role ob_admin_api
  login nosuperuser nocreatedb nocreaterole noinherit noreplication
  connection limit 8;

create role ob_content_ingest
  login nosuperuser nocreatedb nocreaterole noinherit noreplication
  connection limit 2;

create role ob_migrator
  login nosuperuser nocreatedb nocreaterole noinherit noreplication
  connection limit 2;

grant ob_owner to ob_migrator;
grant create on schema public to ob_owner;
```

Set independent passwords without placing them in committed SQL. From an interactive `psql` session, `\password ob_player_api` prompts without echoing the password; repeat for the other roles. Store the resulting connection strings as four separate deployment secrets.

#### Step 2: Remove inherited/default access

Test this first on staging. These statements concern only Organic Battles tables and do not alter Supabase-managed schemas:

```sql
revoke all on table
  public."OB_users",
  public."OB_verification_codes",
  public."OB_auth_sessions",
  public."OB_game_sessions",
  public."OB_curricula",
  public."OB_tracks",
  public."OB_content_releases",
  public."OB_questions",
  public."OB_bosses",
  public."OB_boss_question_assignments",
  public."OB_player_question_progress",
  public."OB_answer_attempts",
  public."OB_admin_users",
  public."OB_admin_sessions",
  public."OB_admin_audit_logs"
from public, anon, authenticated,
     ob_player_api, ob_admin_api, ob_content_ingest;

grant connect on database postgres
  to ob_player_api, ob_admin_api, ob_content_ingest, ob_migrator;

grant usage on schema public
  to ob_player_api, ob_admin_api, ob_content_ingest, ob_migrator;
```

Do not grant `CREATE` on `public` to any web role. Do not grant `SUPERUSER`, `CREATEDB`, `CREATEROLE`, `REPLICATION`, or `BYPASSRLS` to player or admin identities.

#### Step 3: Grant player-route privileges

Player routes need read-only access to published learning content:

```sql
grant select on table
  public."OB_curricula",
  public."OB_tracks",
  public."OB_content_releases",
  public."OB_questions",
  public."OB_bosses",
  public."OB_boss_question_assignments"
to ob_player_api;
```

Grant only the operations used by signup, login, verification, gameplay, and learning records:

```sql
grant select, insert, update on table public."OB_users"
  to ob_player_api;

grant select, insert, update, delete on table
  public."OB_verification_codes",
  public."OB_auth_sessions"
to ob_player_api;

grant select, insert, update on table
  public."OB_game_sessions",
  public."OB_player_question_progress"
to ob_player_api;

grant select, insert on table public."OB_answer_attempts"
  to ob_player_api;
```

Do not grant player routes any privilege on `OB_admin_users`, `OB_admin_sessions`, or `OB_admin_audit_logs`. Do not grant content `INSERT`, `UPDATE`, or `DELETE`.

If an existing code path actually requires another operation, do not add a blanket grant. Identify the exact query, decide whether the operation belongs in that route, and add one narrowly tested privilege.

#### Step 4: Grant admin-route privileges

The admin web identity may inspect all application records but still must not own tables or execute DDL:

```sql
grant select on table
  public."OB_users",
  public."OB_verification_codes",
  public."OB_auth_sessions",
  public."OB_game_sessions",
  public."OB_curricula",
  public."OB_tracks",
  public."OB_content_releases",
  public."OB_questions",
  public."OB_bosses",
  public."OB_boss_question_assignments",
  public."OB_player_question_progress",
  public."OB_answer_attempts",
  public."OB_admin_users",
  public."OB_admin_sessions",
  public."OB_admin_audit_logs"
to ob_admin_api;

grant insert, update, delete on table
  public."OB_users",
  public."OB_verification_codes",
  public."OB_auth_sessions",
  public."OB_game_sessions",
  public."OB_tracks",
  public."OB_content_releases",
  public."OB_questions",
  public."OB_bosses",
  public."OB_boss_question_assignments",
  public."OB_player_question_progress",
  public."OB_admin_users",
  public."OB_admin_sessions",
  public."OB_admin_audit_logs"
to ob_admin_api;
```

Keep `OB_answer_attempts` append-only for ordinary application behavior. If administrators must correct attempts, implement an audited, narrowly scoped stored procedure instead of granting general update/delete.

#### Step 5: Grant ingestion privileges

Do not run `scripts/ingest_questions_to_postgres.py` with the web-admin password:

```sql
grant select on table
  public."OB_curricula",
  public."OB_tracks",
  public."OB_content_releases",
  public."OB_questions",
  public."OB_bosses",
  public."OB_boss_question_assignments"
to ob_content_ingest;

grant insert, update, delete on table
  public."OB_curricula",
  public."OB_tracks",
  public."OB_content_releases",
  public."OB_questions",
  public."OB_bosses",
  public."OB_boss_question_assignments"
to ob_content_ingest;
```

Transfer each Organic Battles table and its associated sequences to `ob_owner` in a reviewed migration, then have the migration connection execute `SET ROLE ob_owner` while Alembic runs. Do not use `REASSIGN OWNED BY postgres`, because the Supabase `postgres` role owns objects outside this application. The migration identity must be used by a one-shot deployment job, not by Uvicorn and not by the admin portal.

For identity/serial columns, inspect the sequences used by the tables above and grant `USAGE, SELECT` only to roles that insert into the corresponding table. Do not grant access to every sequence blindly.

#### Step 6: Add row-level protection for player data

Table grants prevent a player route from editing questions or admin accounts, but every player request still uses the same `ob_player_api` database login. Without RLS, a missing `WHERE user_id = ...` condition could touch another player's row.

Enable RLS on player-owned tables:

- `OB_users`
- `OB_auth_sessions`
- `OB_game_sessions`
- `OB_player_question_progress`
- `OB_answer_attempts`
- `OB_verification_codes` when it can be tied safely to a user or signup identity

Example for game sessions:

```sql
alter table public."OB_game_sessions" enable row level security;
alter table public."OB_game_sessions" force row level security;

create policy player_select_own_game_session
on public."OB_game_sessions"
for select to ob_player_api
using (
  user_id::text = current_setting('app.current_user_id', true)
);

create policy player_insert_own_game_session
on public."OB_game_sessions"
for insert to ob_player_api
with check (
  user_id::text = current_setting('app.current_user_id', true)
);

create policy player_update_own_game_session
on public."OB_game_sessions"
for update to ob_player_api
using (
  user_id::text = current_setting('app.current_user_id', true)
)
with check (
  user_id::text = current_setting('app.current_user_id', true)
);

create policy admin_manage_game_sessions
on public."OB_game_sessions"
for all to ob_admin_api
using (true)
with check (true);
```

Create separate policies for `SELECT`, `INSERT`, `UPDATE`, and `DELETE` on each protected table. Add indexes whose leading column is `user_id`; otherwise RLS filtering can cause expensive scans.

Organic Battles uses its own authentication rather than a Supabase JWT. After authenticating the request, set the user identity transaction-locally before player-data queries:

```python
from sqlalchemy import text

db.execute(
    text("select set_config('app.current_user_id', :user_id, true)"),
    {"user_id": str(current_user.id)},
)
```

The final `true` makes the value transaction-local, which is essential with pooled connections. Use one database transaction per request. A commit ends the setting; if a route commits and continues querying, begin a new transaction and set the identity again. Never use a persistent session setting on a pooled connection.

Authentication lookup occurs before `current_user` is known. Handle this with one of these designs:

1. Preferred: a narrowly scoped `ob_auth_api` role or `SECURITY DEFINER` function that resolves a hashed session token and returns only the user ID needed to establish the player transaction.
2. Transitional: allow `ob_player_api` only the exact token-hash lookup required by the authentication repository, then set the RLS context immediately. Keep the database credential server-only.

RLS protects against application query mistakes. It does not make a shared server credential safe to expose: anyone holding `ob_player_api` credentials may be able to manipulate custom settings. Never send these connection strings to the browser.

#### Step 7: Split SQLAlchemy engines and dependencies

Create separate engines and session factories:

```python
player_engine = create_engine(settings.database_url_player, pool_pre_ping=True)
admin_engine = create_engine(settings.database_url_admin, pool_pre_ping=True)

PlayerSessionLocal = sessionmaker(bind=player_engine, autoflush=False)
AdminSessionLocal = sessionmaker(bind=admin_engine, autoflush=False)
```

Then enforce dependency boundaries:

- Auth, user, game, and battle routers use `get_player_db`.
- Admin, questions-admin, and analytics-admin routers use `get_admin_db`.
- The ingest script reads only `DATABASE_URL_INGEST`.
- Alembic/deployment schema jobs read only `DATABASE_URL_MIGRATION`.
- Repositories receive a session explicitly; they must not import a global `SessionLocal`.
- Remove runtime schema creation and database migration from FastAPI startup.

The total database connection ceiling is now the sum of every role's application pools across all processes and replicas. Keep admin pools small and use `NullPool` for one-shot ingest/migration jobs when appropriate.

#### Step 8: Test allow and deny behavior

Run privilege tests as every role. Required assertions include:

| Test | Expected result |
|---|---|
| Player selects a published question | Allowed |
| Player updates a question or content release | Denied with `42501` |
| Player reads `OB_admin_users` | Denied with `42501` |
| Player updates own game session after setting identity | Allowed |
| Player selects or updates another user's game session | No rows or denied |
| Player deletes an answer attempt | Denied |
| Admin updates a user or question | Allowed and audited |
| Admin creates/drops a table | Denied |
| Ingest role reads player password/session data | Denied |
| Migration role is used by a web request | Test/configuration failure |

Inspect the resulting grants:

```sql
select grantee, table_name, privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and table_name like 'OB\_%' escape '\'
order by grantee, table_name, privilege_type;
```

Add automated negative tests before switching production traffic. A least-privilege rollout is successful only when permitted operations pass and prohibited operations fail.

## 5. Database model

The canonical SQLAlchemy models use these tables:

| Area | Tables |
|---|---|
| Accounts | `OB_users`, `OB_verification_codes`, `OB_auth_sessions` |
| Game state | `OB_game_sessions` |
| Catalog | `OB_curricula`, `OB_tracks`, `OB_bosses` |
| Versioned content | `OB_content_releases`, `OB_questions`, `OB_boss_question_assignments` |
| Learning records | `OB_player_question_progress`, `OB_answer_attempts` |
| Administration | `OB_admin_users`, `OB_admin_sessions`, `OB_admin_audit_logs` |

```mermaid
erDiagram
    OB_users ||--o| OB_game_sessions : owns
    OB_users ||--o{ OB_answer_attempts : submits
    OB_curricula ||--o{ OB_tracks : contains
    OB_tracks ||--o{ OB_content_releases : publishes
    OB_content_releases ||--o{ OB_questions : contains
    OB_bosses ||--o{ OB_boss_question_assignments : receives
    OB_questions ||--o{ OB_boss_question_assignments : assigned
    OB_users ||--o{ OB_player_question_progress : masters
    OB_admin_users ||--o{ OB_admin_sessions : authenticates
    OB_admin_users ||--o{ OB_admin_audit_logs : generates
```

Question options, spells, health, and images use JSON on SQLite and JSONB on PostgreSQL. PostgreSQL setup also attempts to create search/index extensions and question indexes. `OB_game_sessions.user_id` is unique, so each player has one current session; progress for other tracks is archived in user JSON during track switches.

## 6. How questions are loaded

Normal game content is database-first:

```mermaid
flowchart TD
    R["Track requested"] --> M{"In local/shared cache? ({track}:{source_id}:{rel})"}
    M -->|Yes| C["Return validated bundle"]
    M -->|No| D{"Published DB rows available? (ob_player)"}
    D -->|Yes| F["Build, validate, and cache bundle"]
    D -->|No| V{"Validated DB cache exists? (source_identity='db')"}
    V -->|Yes| C
    V -->|No| J{"ALLOW_JSON_FALLBACK?"}
    J -->|Yes| S["Load and validate source JSON"]
    J -->|No| E["Return 503"]
```

A custom data folder bypasses the database and reads JSON directly. That feature should be limited to trusted development workflows; the current user-facing track-switch endpoint accepts custom paths and can place the resulting bundle in a global cache entry.

The loader orders database questions by chapter and `order_index`. It selects the latest published release when that release contains rows. If the selected release has no rows, the current query drops the release filter and can return rows from other releases. Fix this before relying on release isolation.

### Source question shape

```json
{
  "id": "track-specific-stable-id",
  "chapter": 1,
  "chapter_title": "Bonding and Structure",
  "boss": 1,
  "topic": "resonance",
  "difficulty": "medium",
  "question_type": "multiple_choice",
  "question": "Which contributor is most important?",
  "options": [
    {"label": "A", "text": "First answer"},
    {"label": "B", "text": "Second answer"}
  ],
  "correct_option": "B",
  "correct_answer": "Second answer",
  "explanation": "Reasoning shown after the attempt.",
  "spells": ["fire-spark"],
  "health": 100,
  "images": []
}
```

All 20 tracks contain repeated question prompt text. Across the corpus, duplicate prompt occurrences are substantial. Do not use prompt text as identity. The answer-attempt path currently looks up a database question using prompt text and `.first()`, so analytics can associate an attempt with the wrong row. Carry a stable `question_id` and `release_id` through the client turn and submission instead.

### Content totals

| Curriculum | Tracks | Questions per track | Total |
|---|---:|---:|---:|
| Advanced | 12 | 1,350 | 16,200 |
| Foundational default | 1 | 1,350 | 1,350 |
| Other foundational | 7 | 1,550 | 10,850 |
| Repository total | 20 | — | 28,400 |

Track IDs are `default`; `adv-vocab`, `adv-outcomes`, `adv-arrows`, `adv-stereo`, `adv-rankings`, `adv-spectra`, `adv-retro`, `adv-mo`, `adv-thermo`, `adv-medicinal`, `adv-lab`, `adv-trees`; and `found-nomenclature`, `found-outcomes`, `found-mechanisms`, `found-stereo`, `found-property`, `found-spectra`, `found-synthesis`.

## 7. Content recipes

### Validate before import

Run the content-focused tests before changing the database:

```bash
pytest -q \
  tests/test_question_validation_and_jsonb.py \
  tests/test_question_parity.py \
  tests/test_tracks_config.py \
  tests/test_track_content_loading.py
```

### Import one track

The current importer deletes existing questions for the track and commits before the replacement is fully inserted and published. Treat it as destructive and non-atomic.

1. Back up the database.
2. Stop writes or enter a maintenance window.
3. Validate all source files.
4. Use an explicit database URL.
5. Import and then verify counts, release status, and sample gameplay.

```bash
export DATABASE_URL='postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME'
python scripts/ingest_questions_to_postgres.py \
  --track adv-vocab \
  --batch-size 1000
```

Run without `--track` only after testing against a disposable database; it processes the full catalog.

### Warm selected content

```bash
python scripts/warm_cache.py \
  --tracks default,adv-vocab,found-nomenclature
```

The startup-warming configuration flag is not currently consumed. Use the script as a post-deploy step until startup/lifecycle wiring is added.

### Add a track

1. Create a data folder and chapter files following the existing schema.
2. Add boss assets or point to a trusted existing boss folder.
3. Add one entry to `data/tracks_config.json` with a unique ID, curriculum, folders, chapter count, and question count.
4. Validate every option label, correct option, boss number, health value, image path, and question ID.
5. Start against a disposable SQLite database and confirm the track catalog.
6. Back up and import into PostgreSQL.
7. Warm the cache and smoke-test a complete battle.

## 8. Gameplay and API behavior

```mermaid
sequenceDiagram
    participant P as Player
    participant A as API
    participant D as Database
    P->>A: Select spell
    A->>D: Check owner, state, cooldown, version
    A-->>P: Shuffled choices + turn_id + expiry
    P->>A: Answer + turn_id + optional version
    A->>D: Consume turn and update atomically
    A-->>P: Result, damage, explanation, new version
```

The server creates a short-lived, single-use turn ID and supports optimistic version checks. Choices are shuffled, while question progression is sequential within the bundle.

| Spell tier | Spell IDs | Damage | Cooldown |
|---|---|---:|---:|
| Basic | `fire-spark`, `acid-shot`, `carbon-punch` | 20 | 1.5 s |
| Medium | `resonance-burst`, `nucleophile-strike`, `chiral-slash` | 30 | 5 s |
| Strong | `mechanism-storm`, `stereochemical-rift`, `spectral-obliteration` | 45 | 10 s |

On a correct answer, the boss takes spell damage. If still alive, it has a 45% chance to counter for a random 10–25 damage. On an incorrect answer, the player takes the spell's damage value.

Main endpoint groups under `/api/v1`:

| Group | Endpoints |
|---|---|
| Player auth | `/auth/signup`, `/auth/verify`, `/auth/login`, `/auth/me`, `/auth/resend`, `/auth/logout` |
| Game | `/game/new`, `/game/state`, `/progression`, `/avatar/finalize`, `/game/tracks`, `/game/track` |
| Battle | `/battle/select-spell`, `/battle/answer`, `/battle/next-turn`, `/battle/retry`, `/battle/restart` |
| Preferences | `/user/mode`, `/user/content-source` |
| Admin | Login/status; users; sessions; system; tracks/curricula; logging; cache; releases; admin accounts |
| Questions | List, read, edit, reorder, and ingest admin routes |
| Analytics | Overview, question analytics, and user mastery |
| Health | `/healthz`, `/readyz`, `/health/live`, `/health/ready` |

The standardized error body is:

```json
{
  "error": {
    "code": "CONFLICT",
    "message": "Human-readable message",
    "status_code": 409,
    "details": null
  },
  "detail": "Human-readable message"
}
```

The duplicate `detail` field preserves compatibility with older clients.

## 9. Authentication and administration

Player usernames are restricted to 3–24 letters, numbers, underscores, dots, or hyphens. Passwords require at least eight characters. Email verification codes are six digits, SHA-256 hashed, single-use, and expire after 15 minutes by default.

Player authentication supports a bearer token or an HttpOnly cookie. Browser admin login now uses an HttpOnly cookie and no longer returns or stores the admin token in browser `localStorage`. Non-browser clients can still receive a bearer token based on request/client hints.

Admin access is authentication-only today; role values exist, but route-level role-based authorization is not enforced. Newly created admin passwords require only five characters, which is weaker than player policy. The admin cookie is also created with `secure=False` in the current route even when production player cookies are secure.

Rate limits are keyed by remote IP and maintained in process memory. They cover signup, verification, login, resend, and admin login. In a multi-worker deployment, limits are not global and proxy address handling must be configured carefully.

## 10. Cache behavior

The in-process cache is bounded and expires entries. Redis, when configured, provides shared, versioned content entries. If the database is unavailable, a previously validated cache may be served before JSON fallback is considered.

Current Redis entries are compressed Python pickle objects. `pickle.loads` can execute attacker-controlled code. Do not enable the shared Redis cache in a production threat model where another principal can write cache keys. Replace pickle with a schema-validated JSON or MessagePack representation, then authenticate Redis, require TLS, isolate the network, and apply key prefixes/ACLs.

Cache invalidation occurs after imports and release changes, but custom-folder bundles share keys with normal track bundles. Include source identity and release ID in every cache key.

## 11. Testing and verification

Standard local run:

```bash
TESTING=1 pytest -q -m 'not e2e'
```

At the verified commit, this produced:

```text
333 passed, 3 skipped, 8 failed, 1 deselected
```

All eight failures attempted live Supabase/PostgreSQL connections and failed because that external host was unavailable in the scan environment. The result does not establish that those eight behaviors pass against a reachable database. The suite mixes live integration checks with the ordinary test command; add `unit`, `integration`, `live_db`, and `e2e` markers so CI can report each class honestly.

Before release, run at least:

1. Fast unit/content/security tests with SQLite.
2. PostgreSQL integration tests against an ephemeral database.
3. Import and release tests with rollback/failure injection.
4. UI tests with the server and browser dependencies installed.
5. Dependency, secret, static-code, container, and dynamic API scans in CI.

Recommended CI gates include `ruff`, `mypy` or Pyright, Bandit/Semgrep, `pip-audit`, Gitleaks, Trivy, and OWASP ZAP against a disposable deployment. Pin GitHub Actions by commit SHA and store reports as artifacts.

## 12. Security and reliability status

This table is the refreshed status, including the most recent changes.

| Finding | Status | Priority | Technical action |
|---|---|---:|---|
| Game session access lacked reliable ownership checks | FIXED | — | Canonical repositories and game routes now verify the authenticated owner; keep regression tests |
| Battle turns could be replayed/raced | FIXED | — | Server-issued single-use `turn_id`, expiry, and optimistic session version are present; keep concurrent tests |
| Defeat retry could reset unrelated states | FIXED | — | Retry now requires a defeated player with a living boss |
| Username accepted stored-XSS characters | FIXED | — | Strict allowlist is enforced for signup and admin credential changes; DOMPurify and escapeHtml implemented |
| Browser admin token stored in `localStorage` | FIXED | — | Browser login now uses HttpOnly cookies and removes the legacy stored token |
| PostgreSQL credential is committed in settings/env files and Git history | FIXED | Critical | Rotated, removed from `settings.py`, `admin.py`, `README.md`, environment files untracked, and Git history rewritten with git-filter-repo |
| Player, admin, import, and migration work share an overly powerful database identity | FIXED | Critical | Least-privilege roles (`ob_player`, `ob_admin_api`, `ob_content_ingest`, `ob_migrator`) provisioned in Supabase, table grants/RLS policies enforced, and dedicated role URLs routed |
| Predictable seeded admin accounts/passwords | TODO | Critical | Remove automatic production seeding; require one-time bootstrap secret; force password change; invalidate existing sessions |
| Admin system API can switch the database at runtime | TODO | Critical | Remove from production builds or require step-up auth, strict destination allowlist, no raw password response, and audited approval |
| User-controlled custom content folders can escape intended content flow and poison cache | TODO / PARTIALLY FIXED | High | Cache key poisoning is **FIXED** by `{track_id}:{source_identity}:{release_id}` isolation; removing custom folder input from player API remains a **TODO** |
| `/battle/next-turn` can advance while the current boss is alive | TODO | High | Require `boss_hp <= 0`, use optimistic update, and add negative authorization/state tests |
| Redis cache deserializes pickle | FIXED | High | Replaced with schema-validated JSON with zlib; `ob:` key prefixing, non-blocking SCAN, credential masking, and TLS verification enforced |
| Content import is destructive and not atomic | TODO | High | Insert a complete immutable draft release in one transaction, validate counts/checksum, atomically flip active release, retain old release |
| Release fallback can mix rows from other releases | TODO | High | Never remove the release predicate; fail closed if active release is empty or invalid |
| Attempts identify questions by non-unique prompt text | TODO | High | Persist stable question and release IDs in turn state and submit them with attempts; add foreign keys/uniqueness rules |
| Admin cookie explicitly lacks `Secure`; admin password minimum is five; RBAC not enforced | TODO | High | Use shared secure cookie settings, require 12+ characters or passkeys, add role dependencies per route, consider MFA |
| Generic 500 response exposes exception text | TODO | Medium | Return a fixed public message; log sanitized details with request ID server-side |
| Readiness/system endpoints expose operational detail publicly | TODO | Medium | Keep liveness minimal; protect or network-restrict readiness, metrics, database, folder, and log endpoints |
| Rate limiting is process-local and proxy-sensitive | TODO | Medium | Use Redis-backed limits, trusted-proxy configuration, account/device dimensions, and progressive lockouts |
| CSP permits inline scripts/styles and CDN script lacks SRI | TODO | Medium | Move inline code to static files, use nonces/hashes, self-host Phaser or pin with SRI, narrow CSP |
| Docker image copies the entire repository and runs as root | TODO | Medium | Add `.dockerignore`, multi-stage build, non-root UID, read-only filesystem, healthcheck, pinned base digest, and image scanning |
| No committed migration history | FIXED | Medium | Added Alembic migration revisions (0001 through 0008) covering least-privilege roles, RLS, and schema baselines |
| Startup-warming flag is unused | TODO | Low | Wire it into lifespan with bounded parallelism or remove it and document the warm-cache job |

These statuses come from source/configuration review and the available test suite. They are not a penetration-test certification.

## 13. Production deployment checklist

Do not call the current Dockerfile production-ready. It copies the whole repository into the image, installs as root, and runs the process as root. There is no `.dockerignore`.

Before production:

- Rotate the exposed database credential and remove every committed secret/default password.
- Replace the shared `postgres` application connection with separate player, admin, ingestion, and migration identities; verify both allow and deny cases.
- Disable automatic admin seeding and bootstrap the first admin out of band.
- Fix the four content-integrity issues: custom folder input, non-atomic import, cross-release fallback, and prompt-based identity.
- Fix boss advancement authorization and Redis serialization.
- Add Alembic migrations and an ephemeral PostgreSQL integration environment.
- Build a minimal non-root image with only runtime code/assets and locked dependencies.
- Terminate TLS at a trusted proxy; set secure cookies and HSTS; configure forwarded headers only from that proxy.
- Restrict admin, readiness, metrics, log, folder, and database-management surfaces by network and role.
- Back up PostgreSQL, test point-in-time recovery, and rehearse release rollback.
- Centralize structured logs and metrics without tokens, passwords, verification codes, answer content, or database URLs.
- Run secret, dependency, SAST, container, and DAST scans on every release.

## 14. Troubleshooting

| Symptom | Likely cause | Check/fix |
|---|---|---|
| Track returns 503 | DB unavailable, no validated cache, JSON fallback disabled | Check readiness/DB; restore DB or deliberately enable fallback in development |
| Wrong environment settings | `local.env` was auto-selected first | Set process variables or explicit `ENV_FILE`; do not rely on `ENVIRONMENT` alone |
| Pool exhaustion | Worker/replica multiplier exceeds provider limit | Calculate total pool ceiling and reduce worker pool or add an external pooler |
| Import leaves missing/partial content | Current import commits delete and batches separately | Restore backup; redesign importer before retrying production |
| Analytics links attempt to wrong question | Duplicate prompt text used as lookup key | Migrate to stable question/release IDs |
| Cache differs between workers | No Redis, or stale/version/source collision | Inspect cache status, invalidate, and include release/source in keys |
| Login email never arrives | SMTP unset or rejected | Configure `SMTP_*`; avoid logging secrets or codes |
| Tests unexpectedly contact the internet | Live DB tests are included in ordinary selection | Use an ephemeral DB and add explicit pytest markers |

## 15. Recommended implementation order

1. Rotate secrets, remove committed defaults, and secure administrator bootstrap.
2. Create separate player, admin, ingestion, and migration database identities; add explicit grants and RLS tests.
3. Remove runtime database switching and user-supplied content paths from production APIs.
4. Enforce boss state transitions and stable question identity.
5. Make releases immutable and imports transactional, with checksums and atomic activation.
6. Replace pickle and correct cache key isolation.
7. Add Alembic plus isolated PostgreSQL integration tests.
8. Harden admin cookies/RBAC, error responses, diagnostics, rate limits, CSP, and the container.
9. Add repeatable CI security gates and a documented incident/restore runbook.

That order closes direct credential and authorization risks first, then protects question integrity and learning analytics, and finally strengthens deployment and operations.
