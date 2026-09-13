# Organic Battles PostgreSQL Question-Loading Design Review

**Repository:** [DKxi/OrganicBattlesProductionUpgrade](https://github.com/DKxi/OrganicBattlesProductionUpgrade)  
**Reviewed commit:** `0ea6a1291041735f411ad5e8be603e4d8ae8a4fb`  
**Review date:** September 11, 2026

## Executive Summary

PostgreSQL is now used for question storage, but the game does not query PostgreSQL for each individual question.

The current design is best described as:

> PostgreSQL-backed question ingestion with process-local, full-track caching and filesystem JSON fallback.

When a track is first requested, the application retrieves every question for that track from `OB_questions`, converts the rows into an in-memory `ContentBundle`, and caches that bundle inside the FastAPI process. During battle, the next question is selected from the cached Python list using the player's question cursor.

This is a good transitional design. It protects the complete question banks from direct browser downloads and avoids a database call on every combat turn. Before production deployment, however, the design needs stronger credential security, atomic content publishing, distributed cache invalidation, concurrency control, schema migrations, and content versioning.

## Current Question-Loading Architecture

```mermaid
flowchart TD
    A[Player selects track] --> B{SharedTrackCache hit? (LRU / Redis)}
    B -- No --> C[Query OB_questions via ob_player role]
    C --> D[Validate JSONB schemas & build ContentBundle]
    D --> E[Cache in BoundedTrackCache + Redis (ob: prefix, zlib JSON)]
    B -- Yes --> E
    E --> F[Select next question + generate turn_id]
    F --> G[Store active question & turn_id in OB_game_sessions with version check]
```

### Active database

The database connection is selected through `DATABASE_URL`. PostgreSQL URLs are normalized to use the Psycopg2 SQLAlchemy driver.

Questions are stored in:

```text
OB_questions
```

Important columns include:

- `track_id`
- `raw_id`
- `chapter`
- `chapter_title`
- `boss_name`
- `boss_slug`
- `order_index`
- `topic`
- `difficulty`
- `question_type`
- `prompt`
- `options_json`
- `correct_option`
- `correct_answer`
- `explanation`
- `spells_json`
- `health_json`
- `images_json`

The model is defined in [app/infrastructure/database/models.py](https://github.com/DKxi/OrganicBattlesProductionUpgrade/blob/main/app/infrastructure/database/models.py).

### Runtime loading path

1. `get_content_bundle()` checks the process-local `TRACK_BUNDLES` dictionary.
2. If the track is not cached, it calls `load_track_bundle()`.
3. `load_track_bundle()` first calls `load_db_bundle()`.
4. `load_db_bundle()` executes the equivalent of:

   ```sql
   SELECT *
   FROM "OB_questions"
   WHERE track_id = :track_id
   ORDER BY chapter ASC, order_index ASC;
   ```

5. All rows for the track are converted into Python dictionaries and lists.
6. The complete `ContentBundle` is cached in the application process.
7. Combat selects the next question from that in-memory bundle using the cursor in `OB_game_sessions.question_cursors_json`.
8. If database loading fails or returns no questions, the loader falls back to chapter JSON files.

Relevant implementation files:

- [app/api/deps.py](https://github.com/DKxi/OrganicBattlesProductionUpgrade/blob/main/app/api/deps.py)
- [app/domain/content/loader.py](https://github.com/DKxi/OrganicBattlesProductionUpgrade/blob/main/app/domain/content/loader.py)
- [app/api/v1/battle.py](https://github.com/DKxi/OrganicBattlesProductionUpgrade/blob/main/app/api/v1/battle.py)
- [scripts/ingest_questions_to_postgres.py](https://github.com/DKxi/OrganicBattlesProductionUpgrade/blob/main/scripts/ingest_questions_to_postgres.py)

## PostgreSQL Usage by Data Type

| Data | Current implementation |
|---|---|
| Users | Stored in PostgreSQL |
| Authentication sessions | Stored in PostgreSQL |
| Game sessions and progress | Stored in PostgreSQL |
| Curricula and track metadata | Stored in PostgreSQL |
| Questions and answers | Stored in `OB_questions` |
| Active question | Serialized into `OB_game_sessions.active_question_json` |
| Question cursor | Serialized into `question_cursors_json` |
| Boss images | Filesystem/static assets |
| Runtime question delivery | Loaded from PostgreSQL into memory, then served from memory |
| Original JSON question banks | Retained as ingestion source and runtime fallback |

## Advantages

### 1. Better question-bank protection

The browser no longer needs to download an entire chapter JSON file. The server selects a question and returns only the current prompt and choices. This prevents effortless bulk copying through browser developer tools, although it cannot prevent determined scraping of questions during normal play.

### 2. Deterministic teaching sequence

The `order_index` column preserves the original JSON array sequence. The database query explicitly sorts by `chapter` and `order_index`, which is essential because battle progression uses a sequential cursor rather than random question selection.

### 3. Useful composite indexes

The model defines indexes for:

- `(track_id, chapter, order_index)`
- `(track_id, chapter, boss_slug, order_index)`

These support chapter-level and boss-level retrieval efficiently.

### 4. Low database traffic during combat

After the first track load, question selection is an in-memory list lookup. A player does not generate a PostgreSQL query every time a spell is selected.

### 5. Administrative content management

The admin API supports pagination, filtering, search, edits, reordering, and JSON-to-database ingestion. This is a useful foundation for a future teacher or content-management portal.

### 6. Parity testing

The repository tests compare database content and ordering with the original JSON banks. These tests reduce the chance that database migration changes question order or answer content.

## Disadvantages and Risks

### Critical: committed PostgreSQL credential (Status: FIXED)

`app/settings.py` contains a live-looking Supabase PostgreSQL URL, username, and password as a default value. Because the repository is public, this credential must be treated as compromised.

Immediate action:

1. Rotate the Supabase database password.
2. Remove the credential from the source code.
3. Review database connection and audit logs.
4. Remove the credential from Git history where practical.
5. Store `DATABASE_URL` only in deployment secrets.
6. Enable GitHub secret scanning.
7. Use a restricted application database user rather than the database owner.

A safe local default would be:

```python
database_url: str = Field(
    default_factory=lambda: get_config_value(
        "DATABASE_URL",
        default="sqlite:///./organic_battles.sqlite3",
    )
)
```

Production should fail startup if `DATABASE_URL` is missing instead of falling back to a real production credential.

### 1. Every worker loads its own full copy (Status: TODO)

The application calls `.all()` for every question in a selected track. Each Uvicorn worker and every application replica has its own `TRACK_BUNDLES` cache.

Memory therefore grows approximately with:

```text
questions × tracks accessed × worker processes × application replicas
```

The present dataset is still manageable, but the design will become increasingly wasteful as questions, tracks, languages, and application instances increase.

### 2. Cache invalidation is process-local (Status: FIXED)

When an administrator edits or reorders a question, only the worker handling that request clears its cache. Other workers and servers can continue serving stale content.

Players could therefore receive different question text or ordering depending on which server processes the request.

### 3. Silent JSON fallback can create inconsistent content (Status: FIXED)

If PostgreSQL fails, the application silently loads JSON. That improves short-term availability but creates correctness problems:

- Database edits can disappear temporarily.
- Different servers may serve different versions.
- Player cursors may refer to different questions.
- Production configuration failures may remain unnoticed.
- Old content can be served while health checks appear successful.

### 4. PostgreSQL JSON capabilities are unused (Status: FIXED)

`options_json`, `spells_json`, `health_json`, and `images_json` are stored as `Text`. This requires repeated `json.loads()` calls and permits malformed JSON strings to enter the database.

The admin update API also accepts raw JSON strings, weakening validation.

### 5. Correct answers are duplicated in session state (Status: TODO)

The cached question tuple contains:

```python
(prompt, choices, correct_answer)
```

That full tuple is serialized into `active_question_json`. It is not returned to the browser before the player answers, which is good, but duplicating the answer in session state makes auditing, editing, and content-version management harder.

### 6. No content release/version model (Status: TODO)

If an administrator edits or reorders questions during an active battle:

- The player's numeric cursor remains unchanged.
- That cursor may now identify a different question.
- The active question can be an older snapshot.
- The explanation may be resolved from a newer bundle.
- Different workers may use different content versions.

### 7. Re-ingestion is not atomic (Status: TODO)

The ingestion script deletes all questions for a track and commits before inserting the replacement data. It then commits each batch.

During ingestion, players may observe:

- No database questions
- A partially loaded track
- JSON fallback
- A partial bundle cached by a worker

If ingestion fails halfway through, the database remains incomplete.

### 8. Reorder endpoint is fragile (Status: TODO)

The reorder API commits temporary negative indexes before assigning final indexes.

Risks include:

- An interruption can leave negative order values.
- A partial ID list can collide with untouched questions.
- IDs are not fully validated before the first commit.
- Duplicate IDs are not rejected explicitly.
- The operation is scoped to a chapter but not a boss.
- Multiple individual updates increase overhead.

### 9. Combat concurrency is not protected (Status: FIXED)

`GameSession.version` is incremented, but it is not used in an optimistic locking condition. Two concurrent requests can read the same session, process the same turn, and overwrite one another.

This can occur because of:

- Double taps
- Mobile retries
- Multiple browser tabs
- Network retransmission
- Concurrent requests routed to different workers

### 10. Fixed pool sizes multiply across workers (Status: FIXED)

Each process configures:

```text
pool_size = 10
max_overflow = 20
```

Eight workers could theoretically create up to 240 database connections. Multiple replicas multiply that total, potentially exceeding a managed PostgreSQL or Supabase connection limit.

### 11. Admin search will eventually slow down (Status: TODO)

Admin search uses leading-wildcard matching:

```sql
prompt ILIKE '%search%'
OR topic ILIKE '%search%'
```

Ordinary B-tree indexes cannot efficiently serve this search pattern. The current dataset may remain acceptable, but performance will decline as the content catalog grows.

### 12. `create_all()` is not a production migration system (Status: FIXED)

`Base.metadata.create_all()` creates missing tables but does not safely evolve existing PostgreSQL schemas. It cannot replace controlled migrations for column changes, constraint changes, data conversions, and rollback.

### 13. Broad exception handling hides failures (Status: FIXED)

`load_db_bundle()` catches broad exceptions and returns `None`, which can trigger JSON fallback. Database outages, invalid JSON, schema mismatches, authentication errors, and programming defects should not all be treated identically.

### 14. Prompt text is used as a metadata key (Status: TODO)

Explanations, images, and spell information are mapped partly by prompt text. Duplicate prompts or prompt edits can cause collisions and inconsistent metadata. Stable question IDs should be used instead.

## Recommended Target Architecture

```mermaid
flowchart TD
    A[PostgreSQL source of truth (ob_player / ob_admin_api + RLS)] --> B[Versioned question service]
    B --> C[Redis shared cache (ob: prefix, zlib JSON) & Bounded LRU]
    C --> D[FastAPI workers]
    D --> E[Active question response with turn_id & optimistic locking]
    F[Admin publish / Release change] --> A
    F --> G[Cache invalidation event (scan_iter + LRU clear)]
    G --> C
```

PostgreSQL should remain the authoritative content store. Redis or another distributed cache should give every worker the same published content and allow consistent invalidation across processes and servers.

## Prioritized Recommendations

### Priority 0: Rotate and remove the exposed database credential (Status: FIXED)

This must happen before any other production work.

- Rotate the Supabase password.
- Inspect access logs.
- Remove the credential from source and Git history.
- Store it only as a deployment secret.
- Use a least-privilege database account.

### Priority 1: Make content ingestion atomic and versioned (Status: TODO)

Introduce a content-release table:

```text
OB_content_releases
- id
- track_id
- version
- status
- checksum
- created_at
- published_at
```

Add `release_id` to `OB_questions`.

Recommended publishing flow:

1. Create a draft release.
2. Insert all questions under that release.
3. Validate counts, schemas, answers, images, and ordering.
4. Atomically mark the release active.
5. Invalidate distributed caches.
6. Retain the previous release for rollback.

Players never see a partial import under this model.

### Priority 2: Add stable question identity and content versions (Status: TODO)

Add a unique constraint such as:

```text
(track_id, raw_id, release_id)
```

Store these fields in the game session:

- `active_question_id`
- `active_question_version`
- `content_release_id`
- `question_cursor`
- Optional option-order snapshot

Do not use prompt text as a unique key.

### Priority 3: Use validated JSONB (Status: FIXED)

Use PostgreSQL `JSONB` for options, spells, health, and images. If SQLite compatibility is required, use SQLAlchemy's generic JSON type with a PostgreSQL `JSONB` variant.

Validate that:

- Every question has at least two choices.
- Option labels are valid and unique.
- Exactly one correct option exists.
- `correct_option` corresponds to the correct answer.
- Health and spell values are valid positive numbers.
- Image filenames are safe and recognized.

Remove raw `options_json` and `spells_json` string inputs from the admin API.

### Priority 4: Adopt a shared cache strategy (Status: FIXED)

For the current scale, either of these is reasonable.

#### Option A: Continue caching entire tracks

Improve the current design by:

- Storing bundles in Redis or checking a shared content version.
- Caching by `(track_id, content_release_id)`.
- Adding a TTL.
- Warming popular tracks during deployment.
- Preventing multiple workers from rebuilding the same cache simultaneously.
- Measuring cache hit ratio, bundle size, and load duration.

#### Option B: Load one boss question bank at a time

Cache by:

```text
(track_id, chapter, boss_slug, content_release_id)
```

This is the recommended balance for Organic Battles. It maintains low latency without duplicating every accessed track across every application worker.

For a direct lookup, use:

```sql
SELECT *
FROM "OB_questions"
WHERE track_id = :track_id
  AND chapter = :chapter
  AND boss_slug = :boss_slug
  AND order_index = :cursor
  AND release_id = :active_release
LIMIT 1;
```

The existing composite index is close to what this query requires.

### Priority 5: Protect combat updates from concurrency (Status: FIXED)

Use either row locking or optimistic concurrency.

Example optimistic update:

```sql
UPDATE "OB_game_sessions"
SET
    boss_hp = :boss_hp,
    player_hp = :player_hp,
    question_cursors_json = :cursors,
    version = version + 1
WHERE id = :session_id
  AND version = :expected_version;
```

If no row is updated, return `409 Conflict` and have the client refresh its state.

Require the current `turn_id` with an answer:

```json
{
  "turn_id": "server-issued-turn-id",
  "answer": "submitted answer"
}
```

Reject missing, expired, or previously consumed turn IDs.

### Priority 6: Replace silent production fallback (Status: FIXED)

Recommended behavior:

- PostgreSQL unavailable but a validated cache exists: serve cached content and mark readiness degraded.
- PostgreSQL unavailable and no cache exists: return `503 Service Unavailable`.
- JSON fallback: allow only through an explicit setting such as `ALLOW_JSON_FALLBACK=true`.
- Record source, content version, and fallback status in internal health information and metrics.

Production servers should not silently serve different content versions.

### Priority 7: Correct the reorder and administration APIs (Status: TODO)

For reorder operations:

- Scope the request by track, chapter, and boss.
- Require the complete ordered set or expose explicit move-before/move-after operations.
- Validate every ID before updating anything.
- Reject duplicate and unknown IDs.
- Use one database transaction.
- Roll back completely on failure.
- Update timestamps.
- Publish changes as a new content release.
- Invalidate distributed cache only after a successful commit.

### Priority 8: Add Alembic migrations (Status: FIXED)

Create migrations for:

1. Credential-independent database configuration
2. JSONB conversion
3. Content releases
4. Stable question identity constraints
5. Game-session active question ID/version
6. Optimistic locking
7. Search indexes

Do not use `create_all()` as the production schema migration mechanism.

### Priority 9: Make connection pooling deployment-aware (Status: FIXED)

Configure through environment variables:

```text
DB_POOL_SIZE
DB_MAX_OVERFLOW
DB_POOL_TIMEOUT
DB_POOL_RECYCLE
```

Calculate the maximum connection total across all workers and replicas. When using a Supabase pooler, start conservatively, such as three to five connections per application instance, and confirm the service limit.

### Priority 10: Improve search and observability (Status: FIXED)

For admin search, add PostgreSQL trigram or full-text indexing.

Monitor:

- Database query latency
- Connection-pool utilization
- Track or boss bundle load time
- Cache hits and misses
- Cache memory consumption
- JSON fallback count
- Ingestion validation failures
- Content-version mismatches
- Concurrent combat update conflicts

## Suggested Long-Term Data Model

| Table | Responsibility |
|---|---|
| `OB_content_releases` | Immutable published content versions |
| `OB_questions` | Question content and sequence |
| `OB_question_options` or JSONB field | Answer options |
| `OB_bosses` | Boss identity, image, health, and ordering |
| `OB_boss_question_assignments` | Boss-to-question relationships |
| `OB_game_sessions` | Current chapter, boss, HP, turn, and version |
| `OB_player_question_progress` | Per-player mastery and delivery state |
| `OB_answer_attempts` | Answer history, analytics, and research data |

This separation supports:

- Spaced repetition
- Adaptive difficulty
- Mastery tracking
- Teacher analytics
- Question retirement without corrupting progress
- A/B testing
- Shared questions across curricula
- Academic learning-outcome research

## Recommended Implementation Sequence

| Phase | Work | Priority | Status |
|---|---|---|---|
| 0 | Rotate exposed credential and remove it from source | Immediate | FIXED |
| 1 | Add Alembic and baseline the current schema | Mandatory | FIXED |
| 2 | Add content releases and atomic ingestion | Mandatory | TODO |
| 3 | Add stable question IDs and session content versions | Mandatory | TODO |
| 4 | Add optimistic combat locking and turn-ID validation | Mandatory | FIXED |
| 5 | Convert structured text fields to validated JSONB | High | FIXED |
| 6 | Introduce Redis/shared cache invalidation | High | FIXED |
| 7 | Cache boss-level banks instead of all tracks | High | TODO |
| 8 | Restrict JSON fallback and expose degraded health | High | FIXED |
| 9 | Correct the reorder and admin update workflows | High | TODO |
| 10 | Tune connection pools and add metrics | Production readiness | FIXED |

## Final Assessment

The PostgreSQL addition is a meaningful improvement, and the core direction is correct. The schema preserves question order, server-side delivery offers better content protection than downloadable JSON, and in-memory caching provides low combat latency.

The implementation is not yet production-safe across multiple workers or servers. The most important gaps are the exposed credential, non-atomic ingestion, process-local cache invalidation, missing content versioning, silent JSON fallback, and unprotected concurrent combat updates.

After those issues are addressed, PostgreSQL plus a shared Redis cache can support thousands of concurrent players without querying PostgreSQL for every spell and without giving different workers inconsistent versions of the question bank.
