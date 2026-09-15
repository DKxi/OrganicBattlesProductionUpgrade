# Organic Battles — Technical Documentation & Architecture Reference

**Organic Battles** is a production-grade, browser-based educational role-playing game (RPG) designed to teach and master organic chemistry through turn-based boss battles. Players select companion avatars, cast tiered chemistry spells, and answer curriculum-aligned multiple-choice questions to defeat bosses and progress across 20 distinct curriculum tracks spanning 27 chapters and over 27,000 questions.

---

## Table of Contents
1. [System Architecture & High-Level Topology](#1-system-architecture--high-level-topology)
2. [Technology Stack & Runtime Dependencies](#2-technology-stack--runtime-dependencies)
3. [Repository Directory & Modular Structure](#3-repository-directory--modular-structure)
4. [Architecture Flow Diagrams](#4-architecture-flow-diagrams)
   - [4.1 End-to-End System & Asset Delivery Topology](#41-end-to-end-system--asset-delivery-topology)
   - [4.2 Turn-Based Combat & Concurrency State Machine](#42-turn-based-combat--concurrency-state-machine)
   - [4.3 Content Ingestion, Validation & Atomic Release Lifecycle](#43-content-ingestion-validation--atomic-release-lifecycle)
   - [4.4 Least-Privilege Database Role Access Flow](#44-least-privilege-database-role-access-flow)
   - [4.5 Boss Image S3 CDN Resolution & Browser CSP Flow](#45-boss-image-s3-cdn-resolution--browser-csp-flow)
5. [Core Engineering Subsystems](#5-core-engineering-subsystems)
   - [5.1 Pure Domain Combat Engine & P0 Invariant Guards](#51-pure-domain-combat-engine--p0-invariant-guards)
   - [5.2 Versioned Content Releases & Shared Cache Manager](#52-versioned-content-releases--shared-cache-manager)
   - [5.3 Database Connection Pooling & Least-Privilege Roles](#53-database-connection-pooling--least-privilege-roles)
   - [5.4 S3 Storage Asset Decoupling & Lean Containers](#54-s3-storage-asset-decoupling--lean-containers)
   - [5.5 Security Hardening & Observability Telemetry](#55-security-hardening--observability-telemetry)
6. [REST API Reference (`/api/v1/`)](#6-rest-api-reference-apiv1)
7. [Design Pros and Cons](#7-design-pros-and-cons)
8. [Points to Remember & Operational Guidelines](#8-points-to-remember--operational-guidelines)
9. [Local Development, Environment Setup & Testing](#9-local-development-environment-setup--testing)
10. [Database Migration Safety & Content Ingestion Operational Guides](#10-database-migration-safety--content-ingestion-operational-guides)
   - [10.1 Alembic Schema Migrations & Remote Supabase Safety](#101-alembic-schema-migrations--remote-supabase-safety)
   - [10.2 Question & Answer Content Updates (`chapter_xx.json`)](#102-question--answer-content-updates-chapter_xxjson)
   - [10.3 S3 / Object Storage Content Update Workflow](#103-s3--object-storage-content-update-workflow)
   - [10.4 Architecture Scalability Scorecard & Roadmap Status](#104-architecture-scalability-scorecard--roadmap-status)

---

## 1. System Architecture & High-Level Topology

```mermaid
flowchart TB
    subgraph ClientLayer["Client Layer (Modern Browsers: Safari · Chrome · Firefox · Edge)"]
        UI["HTML5 Glassmorphic UI<br/>(static/js/main.js · static/css/game.css)"]
        Phaser["Phaser 3 Visual Arena<br/>(Dynamic Chapter Auras · RESIZE Scale)"]
        Audio["Web Audio Synthesizer<br/>(static/js/audio.js · Zero External Assets)"]
        UI <--> Phaser
        UI --> Audio
    end

    subgraph EdgeLayer["Edge Delivery & Storage Layer"]
        SupabaseS3[("Supabase S3 Object Storage<br/>Buckets: DefaultBosses · AdvancedBosses · FoundationalBosses")]
        CloudCDN["Public HTTPS CDN Edge<br/>(*.supabase.co / *.storage.supabase.co)"]
        SupabaseS3 --> CloudCDN
    end

    subgraph WebCompute["Stateless Modular Monolith (FastAPI)"]
        SecurityMW["Security Middleware<br/>(CSP · HSTS · X-Frame · X-Content-Type · Slowapi)"]
        RouterLayer["API Router Layer (/api/v1/)<br/>(auth.py · battle.py · game.py · admin.py)"]
        DomainLayer["Pure Domain Rules<br/>(app/domain/combat/rules.py · spells.py)"]
        SharedCache["SharedTrackCacheManager<br/>(Versioned (track_id, release_id) Keys · Lock Protection)"]
        Metrics["Prometheus Metrics Registry<br/>(Query Latency · Saturation · Fallbacks)"]
        
        SecurityMW --> RouterLayer
        RouterLayer --> DomainLayer
        RouterLayer --> SharedCache
        RouterLayer --> Metrics
    end

    subgraph DataPlane["Data & Persistence Layer"]
        Pooler["Supabase IPv4 Pooler (:5432 / :6543)<br/>(QueuePool: pool_size=10 · max_overflow=20)"]
        PostgreSQL[("PostgreSQL 15+ Database<br/>Unified OB_ Table Prefix · Alembic Migrations 0001-0009")]
        LocalCache[("Redis / Valkey / Bounded Memory Cache")]
        
        Pooler --> PostgreSQL
    end

    ClientLayer <-->|"REST API / JSON / HttpOnly Cookies"| SecurityMW
    ClientLayer <-->|"Direct Boss Image Fetch"| CloudCDN
    WebCompute <--> Pooler
    SharedCache <--> LocalCache
    RouterLayer -.->|"307 Redirect (/static/assets/bosses/*)"| CloudCDN
```

---

## 2. Technology Stack & Runtime Dependencies

| Layer | Technology | Version | Purpose & Description |
|---|---|---|---|
| **Backend Framework** | **FastAPI** | `0.115.6` | High-performance asynchronous API server with modular routers and OpenAPI documentation. |
| **Validation & Settings** | **Pydantic V2 & Settings** | `2.10.4` | Strictly typed environment validation ([app/settings.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/settings.py)) and schema serialization (`model_dump`). |
| **Production Web Server** | **Gunicorn + Uvicorn Workers** | `gunicorn 26.2.0` / `uvicorn 0.34.0` | Production multi-worker process manager supervising high-performance `uvloop` ASGI workers with process self-healing, automatic memory leak mitigation (`max_requests`), and zero-downtime rolling reloads (`SIGHUP`). |
| **Database & ORM** | **SQLAlchemy 2.x** | `2.0.36` | Fully typed models with unified `OB_` table naming and native `JSONB` column variants. |
| **Database Engine** | **PostgreSQL / SQLite3** | `psycopg2` / Native | Managed PostgreSQL via Supabase IPv4 Pooler (`aws-0-us-west-2.pooler.supabase.com:5432`) with connection pooling and local SQLite3 fallback. |
| **Schema Migrations** | **Alembic** | `1.14.1` | Programmatic migration engine ([app/infrastructure/database/alembic_runner.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/infrastructure/database/alembic_runner.py)) managing revisions `0001` through `0009`. |
| **Object Storage** | **AWS S3 / Supabase Storage** | `boto3` `1.36.3` | Direct streaming reader ([app/infrastructure/storage/s3_reader.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/infrastructure/storage/s3_reader.py)) for track chapters and public CDN buckets for boss PNGs. |
| **Distributed Cache** | **Redis / In-Memory Tier** | `redis` `5.2.1` | Versioned caching keyed by `(track_id, release_id)` with zlib compression and thundering-herd lock protection. |
| **Audio Synthesizer** | **Web Audio API** | Native Browser | Procedural, zero-download sound engine in [static/js/audio.js](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/static/js/audio.js). |
| **Game Engine** | **Phaser 3** | `3.60.0` (CDN) | 2D WebGL/Canvas arena rendering dynamic chapter auras and responsive canvas scaling (`Phaser.AUTO`, `Phaser.Scale.RESIZE`). |
| **Rate Limiting** | **Slowapi** | `0.1.9` | Token-bucket rate limiting defending `/auth/signup`, `/auth/login`, and `/admin/login` with multi-worker Redis/memory backend. |
| **Testing Suite** | **Pytest & Playwright** | `8.3.4` / `0.9.0` | 391 automated tests covering combat mechanics, concurrency, security, Gunicorn multi-worker lifecycle, database roles, and UI rendering. |

---

## 3. Repository Directory & Modular Structure

The codebase is organized as a **Clean Modular Monolith**:

```text
OrganicBattles/
├── app/                                        # Modular Application Core
│   ├── main.py                                 # FastAPI factory, CORS, CSP middleware, boss 307 redirects
│   ├── settings.py                             # Centralized Pydantic Settings & environment resolver
│   ├── api/                                    # Controller Layer
│   │   ├── deps.py                             # Dependency injection (get_db, auth_admin, limiter)
│   │   └── v1/                                 # Version 1 API Endpoints
│   │       ├── auth.py                         # Account registration, login, verification, logout
│   │       ├── battle.py                       # Spell selection, question grading, advance, retry
│   │       ├── game.py                         # Active session state, curriculum track catalog
│   │       ├── admin.py                        # Admin telemetry, user credentials, live DB switch
│   │       └── questions_admin.py              # Schema-validated question CRUD operations
│   ├── domain/                                 # Pure Business Logic (Zero Framework / DB Dependencies)
│   │   ├── combat/                             # Turn resolution, 9-spell catalog, cooldowns, damage
│   │   │   ├── entities.py                     # Spell, CombatTurnResult dataclasses
│   │   │   ├── rules.py                        # evaluate_combat_turn, grade_answer, P0 invariant guards
│   │   │   └── spells.py                       # Spell tier configurations and damage profiles
│   │   ├── content/                            # Question parsing, schema validation, bundle loading
│   │   │   ├── entities.py                     # ContentBundle dataclass
│   │   │   ├── loader.py                       # load_db_bundle, S3 & DB track resolution
│   │   │   └── validator.py                    # validate_question_payload (options, health, spells)
│   │   └── progression/                        # Progression tracking and boss victory rules
│   ├── infrastructure/                         # External I/O and Persistence Layer
│   │   ├── database/                           # Database engine and ORM repositories
│   │   │   ├── models.py                       # Unified OB_ declarative models with JSONB variants
│   │   │   ├── engine.py                       # Pooler setup, connection pooling, NullPool runners
│   │   │   ├── migrator.py                     # Repeatable SQLite <-> PostgreSQL migration engine
│   │   │   ├── alembic_runner.py               # Standalone programmatic Alembic execution
│   │   │   ├── releases_repo.py                # ReleasesRepository (draft, publish, rollback)
│   │   │   ├── session_repository.py           # GameSessionRepository with optimistic locking
│   │   │   └── tracks_repo.py                  # TracksRepository (curricula and track metadata)
│   │   ├── cache/                              # Caching Subsystem
│   │   │   ├── shared_cache.py                 # SharedTrackCacheManager (versioned keying, locks)
│   │   │   ├── track_cache.py                  # Bounded in-memory LRU track cache
│   │   │   └── memory.py                       # In-memory admin tokens and verification codes
│   │   ├── storage/                            # Cloud Object Storage Subsystem
│   │   │   └── s3_reader.py                    # Boto3 reader for S3 chapter streaming and buckets
│   │   ├── identity/                           # Cryptography & Token Helpers
│   │   │   └── crypto.py                       # PBKDF2-HMAC-SHA256 (310k rounds), token generator
│   │   └── messaging/                          # SMTP & Notifications
│   │       └── smtp.py                         # Asynchronous SMTP delivery with console fallback
│   └── observability/                          # Observability & Diagnostics
│       ├── middleware.py                       # Security headers (CSP, HSTS) & request latency logger
│       └── metrics.py                          # MetricsRegistry (query latency, pool saturation, RED)
├── migrations/                                 # Alembic Database Migrations
│   ├── env.py                                  # Dynamic Alembic environment runner
│   └── versions/                               # Migration revisions 0001 through 0009
├── scripts/                                    # Standalone Maintenance & Ingestion Tools
│   ├── ingest_questions_to_postgres.py         # S3 streaming question ingestion & atomic publishing
│   ├── warm_cache.py                           # Standalone cache warming CLI
│   └── setup_supabase_least_privilege_roles.sql# SQL script establishing 5 least-privilege DB roles
├── static/                                     # Static Browser Frontend
│   ├── css/game.css                            # Glassmorphic RPG design system and arena styling
│   ├── js/
│   │   ├── main.js                             # Game orchestrator, DOM event routing, modal renderer
│   │   ├── avatars.js                          # Companion avatar customizer and sprite renderer
│   │   ├── audio.js                            # Web Audio procedural synthesizer (SFX & mute)
│   │   └── tracks-config.js                    # Client track catalog and S3 boss CDN URL mappings
│   └── assets/                                 # Arena backgrounds and fallback SVG placeholders
├── templates/index.html                        # Single-Page Application HTML shell
├── tests/                                      # 384 Automated Regression Tests
├── ProdUpgradeTasks.md                         # Audited production roadmap with [FIXED] / [TODO] tags
└── GetawayfromDatafolder.md                    # Data folder decoupling audit with [FIXED] / [TODO] tags
```

---

## 4. Architecture Flow Diagrams

### 4.1 End-to-End System & Asset Delivery Topology

```mermaid
flowchart TD
    Player["Player Browser<br/>(Safari / Chrome / Firefox)"]
    
    subgraph CDNNetwork["Supabase Storage S3 Edge"]
        DefaultBosses["DefaultBosses Bucket"]
        AdvancedBosses["AdvancedBosses Bucket"]
        FoundationalBosses["FoundationalBosses Bucket"]
    end

    subgraph AppServer["FastAPI Modular Application Layer"]
        MainApp["app/main.py"]
        BossRoute["GET /static/assets/bosses/{filename}.png"]
        CSPFilter["Observability Middleware (CSP Header)"]
        CombatAPI["POST /api/v1/battle/*"]
        AdminAPI["POST /api/v1/admin/*"]
    end

    subgraph StorageLayer["Database & Cache Engine"]
        Pooler["Supabase IPv4 Pooler (:5432)"]
        PostgresDB[("PostgreSQL Database<br/>OB_users · OB_game_sessions · OB_questions")]
        RedisCache[("Redis / Local Shared Cache")]
    end

    Player -->|"1. Request boss image"| BossRoute
    BossRoute -->|"2. 307 Temporary Redirect"| MainApp
    MainApp -->|"3. Redirect URL"| Player
    Player -->|"4. Direct GET from CDN"| CDNNetwork
    CDNNetwork -->|"5. Serve PNG Image"| Player

    Player -->|"Combat action"| CSPFilter
    CSPFilter --> CombatAPI
    CombatAPI --> Pooler --> PostgresDB
    CombatAPI <--> RedisCache
```

---

### 4.2 Turn-Based Combat & Concurrency State Machine

```mermaid
stateDiagram-v2
    [*] --> IdleAwaitingSpell: Battle Initialized (Player HP: 150)

    IdleAwaitingSpell --> QuestionRevealed: Player selects spell (POST /battle/select-spell)
    note right of QuestionRevealed: Question primed from bank.<br/>Correct answer secret stripped server-side.

    QuestionRevealed --> AnswerGrading: Player submits answer (POST /battle/answer)
    
    state AnswerGrading {
        [*] --> CheckOptimisticLock: Compare expected_version with DB
        CheckOptimisticLock --> Conflict409: Version mismatch
        CheckOptimisticLock --> EvaluateAnswer: Version match
        
        EvaluateAnswer --> CorrectTurn: Submitted choice matches answer
        EvaluateAnswer --> FizzleTurn: Submitted choice incorrect
        
        CorrectTurn --> ApplyBossDamage: Boss HP -= Spell Damage
        ApplyBossDamage --> BossCounterattack: 50% chance boss strikes
        
        FizzleTurn --> ApplySelfDamage: Player HP -= Spell Power (Backfire)
    }

    AnswerGrading --> BossDefeated: Boss HP <= 0
    AnswerGrading --> PlayerDefeated: Player HP <= 0
    AnswerGrading --> IdleAwaitingSpell: Both alive, cooldowns updated, version++

    state BossDefeated {
        [*] --> DefeatedAwaitingAdvance
        DefeatedAwaitingAdvance --> AdvanceTurn: POST /battle/next-turn
    }

    state AdvanceTurn {
        [*] --> ValidateDefeatGuard: Invariant check (Boss HP <= 0, Player HP > 0)
        ValidateDefeatGuard --> Reject400: Boss still alive or Player dead
        ValidateDefeatGuard --> AdvanceBoss: Record victory, advance cursor, restore Player HP to 150
    }

    AdvanceBoss --> IdleAwaitingSpell: Next Boss Arena Ready
    
    PlayerDefeated --> DefeatModal: Show DEFEAT & Unlock Retry
    DefeatModal --> IdleAwaitingSpell: POST /battle/retry (Reset HP & Cooldowns)
```

---

### 4.3 Content Ingestion, Validation & Atomic Release Lifecycle

```mermaid
flowchart LR
    subgraph IngestionSource["Question Source"]
        S3Buckets["S3 Buckets:<br/>DefaultTracks<br/>AdvancedTracks<br/>FoundationalTracks"]
    end

    subgraph IngestionPipeline["Standalone Ingestion (scripts/ingest_questions_to_postgres.py)"]
        StreamJSON["Stream chapter_*.json via boto3"]
        Validator["validate_question_payload()<br/>(>=2 choices · unique labels · safe images · valid numbers)"]
        DraftRelease["Create Draft Release in OB_content_releases<br/>(status = 'draft')"]
        BatchInsert["Batch Insert into OB_questions<br/>(linked to release_id)"]
        Publish["Atomically set status = 'published'<br/>(prior releases archived)"]
    end

    subgraph RuntimeServing["Active Serving Layer"]
        CacheMgr["SharedTrackCacheManager<br/>Key: (track_id, release_id)"]
        Players["Connected Players"]
    end

    S3Buckets --> StreamJSON --> Validator --> DraftRelease --> BatchInsert --> Publish
    Publish -->|"Cache Key Advances Cluster-Wide"| CacheMgr --> Players
    Publish -.->|"Instant Rollback if needed"| DraftRelease
```

---

### 4.4 Least-Privilege Database Role Access Flow

```mermaid
flowchart TD
    subgraph Roles["PostgreSQL Database Roles (SUPABASE_LEAST_PRIVILEGE_SETUP.md)"]
        OB_Owner["ob_owner (NOLOGIN)<br/>Schema & DDL Owner"]
        OB_Player["ob_player (LOGIN)<br/>Web Application Pool"]
        OB_Admin["ob_admin (LOGIN)<br/>Admin Portal Pool"]
        OB_Ingest["ob_content_ingest (LOGIN)<br/>Standalone Ingestion CLI"]
        OB_Migrator["ob_migrator (LOGIN)<br/>CI/CD Alembic Runner"]
    end

    subgraph Tables["Database Tables (Unified OB_ Prefix)"]
        ContentTables["Content Tables:<br/>OB_curricula · OB_tracks<br/>OB_questions · OB_bosses<br/>OB_content_releases"]
        PlayerTables["Player Gameplay Tables:<br/>OB_users · OB_game_sessions<br/>OB_auth_sessions · OB_verification_codes<br/>OB_answer_attempts"]
        MigrationTables["Migration Tables:<br/>alembic_version"]
    end

    OB_Player -->|"SELECT, INSERT, UPDATE, DELETE"| PlayerTables
    OB_Player -->|"SELECT ONLY"| ContentTables

    OB_Admin -->|"SELECT, INSERT, UPDATE, DELETE"| PlayerTables
    OB_Admin -->|"SELECT, INSERT, UPDATE, DELETE"| ContentTables

    OB_Ingest -->|"SELECT, INSERT, UPDATE, DELETE"| ContentTables
    OB_Ingest -.->|"NO ACCESS"| PlayerTables

    OB_Migrator -->|"DDL & Migrations (MEMBER OF ob_owner)"| ContentTables & PlayerTables & MigrationTables
```

---

### 4.5 Boss Image S3 CDN Resolution & Browser CSP Flow

```mermaid
sequenceDiagram
    autonumber
    actor Browser as Player Browser (Safari / Chrome)
    participant Server as FastAPI Server (app/main.py)
    participant CSP as Security Middleware (app/observability/middleware.py)
    participant CDN as Supabase S3 CDN (DefaultBosses / AdvancedBosses / FoundationalBosses)

    Browser->>Server: GET /static/assets/bosses/orbital-ogre.png
    Server->>Server: Resolve bucket priority: DefaultBosses -> FoundationalBosses -> AdvancedBosses
    Server-->>Browser: HTTP 307 Temporary Redirect<br/>Location: https://aamwrwbsrmorllisdffc.supabase.co/.../orbital-ogre.png

    Browser->>CSP: Check Content-Security-Policy (img-src)
    note over CSP: CSP includes: 'self' data: https://*.supabase.co https://*.storage.supabase.co
    CSP-->>Browser: CSP Check Passed (Whitelisted)

    Browser->>CDN: GET https://aamwrwbsrmorllisdffc.supabase.co/.../orbital-ogre.png
    CDN-->>Browser: HTTP 200 OK (image/png) with Cache-Control headers
    Browser->>Browser: Render Boss Asset on Phaser Arena Stage
```

---

## 5. Core Engineering Subsystems

### 5.1 Pure Domain Combat Engine & P0 Invariant Guards
- **Zero Framework Dependency**: Combat logic in [app/domain/combat/rules.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/domain/combat/rules.py) is pure Python with zero imports of FastAPI, Starlette, or SQLAlchemy, enabling ultra-fast unit testing.
- **P0 Advance Without Victory Invariant**:
  - `POST /api/v1/battle/next-turn` is protected by strict pre-condition checks and atomic database filters.
  - Advancing requires:
    1. `game_session.boss_hp <= 0` (current boss must be dead; returns `HTTP 400` if alive).
    2. `game_session.player_hp > 0` (player must be alive; returns `HTTP 400` if defeated).
    3. `game_session.active_spell is None and turn_id is None` (no question turn may be in flight).
  - The database `UPDATE` executes with an atomic predicate:
    ```python
    stmt = (
        update(GameSession)
        .where(
            GameSession.id == session_id,
            GameSession.boss_hp <= 0,
            GameSession.player_hp > 0,
            GameSession.version == expected_version,
        )
        ...
    )
    ```
- **Optimistic Concurrency Control**:
  - Every combat mutation (`select-spell`, `answer`, `next-turn`) requires matching the `version` column.
  - Concurrent submissions or double-clicks produce a clean `HTTP 409 Conflict` rather than corrupted game state.

### 5.2 Versioned Content Releases & Shared Cache Manager
- **Immutable Releases**: Managed via `OB_content_releases` and [app/infrastructure/database/releases_repo.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/infrastructure/database/releases_repo.py). Questions are imported into draft releases and validated prior to activation.
- **Cluster-Wide Invalidation**: [app/infrastructure/cache/shared_cache.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/infrastructure/cache/shared_cache.py) keys cached track bundles by `(track_id, release_id)`. Publishing or rolling back a release instantly changes the key across all instances with zero cache invalidation drift.
- **Thundering-Herd Defense**: Thread-safe locks ensure only one worker rebuilds a given track bundle on cache miss. Concurrent requests await the single build and read from the freshly populated cache.

### 5.3 Database Connection Pooling & Least-Privilege Roles
- **Production Connection Pooler**: Configured in [app/infrastructure/database/engine.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/infrastructure/database/engine.py) to target the Supabase IPv4 Pooler (`aws-0-us-west-2.pooler.supabase.com:5432`) with:
  - `pool_size=10`
  - `max_overflow=20`
  - `pool_pre_ping=True` (verifies connection liveness before checkout)
  - `pool_recycle=1800` (recycles connections every 30 minutes to prevent stale TCP drops)
- **Role Isolation**:
  - `ob_player`: DML on user sessions; read-only on question catalogs.
  - `ob_admin`: User and session administration; storage management.
  - `ob_content_ingest`: Full access to content releases and question banks; zero access to user credentials.
  - `ob_migrator`: Executes Alembic migrations via NullPool as a member of `ob_owner`.

### 5.4 S3 Storage Asset Decoupling & Lean Containers
- **Zero Local Question Footprint**: Production Docker images exclude `data/tracks/` via `.dockerignore`.
- **Untracked Binaries**: 216 boss PNGs and 568 `chapter_*.json` files are excluded in `.gitignore` and untracked from Git, keeping repository clones lightweight.
- **Direct S3 Streaming**: [app/infrastructure/storage/s3_reader.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/infrastructure/storage/s3_reader.py) streams questions directly from Supabase/AWS S3 buckets (`DefaultTracks`, `AdvancedTracks`, `FoundationalTracks`).

### 5.5 Security Hardening & Observability Telemetry
- **Content-Security-Policy (CSP)**: Configured in [app/observability/middleware.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/observability/middleware.py) with explicit whitelists for Supabase CDN:
  ```python
  "img-src 'self' data: https://*.supabase.co https://*.storage.supabase.co;"
  ```
- **Security Headers**: Enforces `HSTS`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, and secure cookie attributes (`HttpOnly`, `SameSite=Lax`, `Secure`).
- **Prometheus Metrics Registry**: [app/observability/metrics.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/observability/metrics.py) tracks query latency, slow queries (>100ms), pool utilization, JSON fallback counts, and combat concurrency conflicts.

---

## 6. REST API Reference (`/api/v1/`)

### Authentication (`/api/v1/auth`)
| Endpoint | Method | Payload | Response | Description |
|---|---|---|---|---|
| `/api/v1/auth/signup` | `POST` | `{"email": str, "username": str, "password": str}` | `200 OK` | Registers a new player and dispatches a 6-digit OTP code via SMTP. |
| `/api/v1/auth/verify` | `POST` | `{"code": str}` | `200 OK` | Validates OTP, activates account, and issues `session_token` cookie. |
| `/api/v1/auth/login` | `POST` | `{"username": str, "password": str}` | `200 OK` | Authenticates user; sets `HttpOnly` session cookie and returns token. |
| `/api/v1/auth/logout` | `POST` | *None* | `200 OK` | Revokes the active session token in the database and clears the cookie. |

### Gameplay & Tracks (`/api/v1/game`, `/api/v1/avatar`)
| Endpoint | Method | Payload | Response | Description |
|---|---|---|---|---|
| `/api/v1/game/new` | `POST` | *None* | `200 OK` | Creates or loads the player's active chapter and boss session. |
| `/api/v1/game/state` | `GET` | *None* | `200 OK` | Returns authoritative battle state (HP, boss info, active spells, version). |
| `/api/v1/game/tracks` | `GET` | *None* | `200 OK` | Lists all 20 configured tracks across curricula from the database. |
| `/api/v1/avatar/finalize` | `POST` | `{"character": str, "config": dict}` | `200 OK` | Selects and equips companion avatar equipment. |

### Combat & Turns (`/api/v1/battle`)
| Endpoint | Method | Payload | Response | Description |
|---|---|---|---|---|
| `/api/v1/battle/select-spell` | `POST` | `{"spell_id": str, "expected_version": int?}` | `200 OK` | Verifies cooldowns and primes the next sequential chemistry question. |
| `/api/v1/battle/answer` | `POST` | `{"answer": str, "expected_version": int?}` | `200 OK` | Grades submitted choice, resolves damage, and advances turn version. |
| `/api/v1/battle/next-turn` | `POST` | `{"expected_version": int?}` | `200 OK` | **Requires defeated boss.** Advances to next boss and restores player HP. |
| `/api/v1/battle/retry` | `POST` | *None* | `200 OK` | Restores player to 150 HP, resets boss HP, and clears cooldowns after defeat. |

### Admin Management (`/api/v1/admin`)
| Endpoint | Method | Payload | Response | Description |
|---|---|---|---|---|
| `/api/v1/admin/login` | `POST` | `{"username": str, "password": str}` | `200 OK` | Authenticates administrator; issues `admin_token` cookie. |
| `/api/v1/admin/users` | `GET` | *None* | `200 OK` | Lists registered users with companion avatars and verification statuses. |
| `/api/v1/admin/sessions` | `GET` | *None* | `200 OK` | Real-time monitoring of active gameplay sessions. |
| `/api/v1/admin/storage/stats` | `GET` | *None* | `200 OK` | Reports database dialect, connection pool telemetry, and row counts. |
| `/api/v1/admin/system/stats` | `GET` | *None* | `200 OK` | Reports server uptime, OS platform, memory RSS/VMS, and CPU utilization. |
| `/api/v1/admin/tracks/{id}/releases` | `GET` | *None* | `200 OK` | Lists all immutable content releases for a track. |
| `/api/v1/admin/tracks/{id}/releases/{ver}/rollback` | `POST` | *None* | `200 OK` | Instantly rolls back active questions to a previous release version. |

---

## 7. Design Pros and Cons

### 1. Stateless Modular Monolith vs Microservices
* **Pros**:
  - High operational velocity: Single codebase, single test suite, single deployment pipeline.
  - Zero inter-service network latency or distributed transaction overhead.
  - Strict domain boundaries ([app/domain/](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/domain/)) allow future extraction into microservices if scaling requires it.
* **Cons**:
  - Resource scaling is coupled: Scaling background workloads or heavy admin queries scales the web API.
  - Single process failure point if an unhandled exception or native memory leak occurs.

### 2. S3 Object Storage & Cloud CDN vs Local Filesystem Assets
* **Pros**:
  - Container images are lean (<100 MB vs >1 GB with assets).
  - Web browsers load images directly from CDN edge caches, reducing server network egress and CPU load to zero.
  - Content can be updated, versioned, and rolled back without redeploying container images.
* **Cons**:
  - Requires reliable external S3 connectivity during content ingestion.
  - Local requests require an initial 307 temporary redirect hop to the CDN.

### 3. Optimistic Concurrency Control vs Pessimistic DB Locking
* **Pros**:
  - Maximum database throughput: Transactions never hold row locks while waiting for client input.
  - Eliminates database deadlocks during high-concurrency combat sessions.
  - Clean client error semantics via `HTTP 409 Conflict`.
* **Cons**:
  - Rapid double-clicks or concurrent requests from multiple tabs will abort the second request, requiring client-side retry or notification.

### 4. Versioned Content Releases (`OB_content_releases`) vs Direct In-Place Table Updates
* **Pros**:
  - Zero partial imports: Questions are staged and validated in draft releases before atomic activation.
  - Zero cache invalidation drift: Cluster-wide cache keys automatically change upon release publication.
  - Instant rollback capability without redeploying code.
* **Cons**:
  - Requires additional database rows and foreign keys linking questions to releases.
  - Older draft and archived releases require periodic background pruning.

### 5. Least-Privilege Database Roles vs Single Superuser Connection
* **Pros**:
  - Hardened security blast radius: A compromised web request (`ob_player`) cannot drop tables, alter schemas, or tamper with question banks.
  - Administrative operations and schema migrations are strictly compartmentalized.
* **Cons**:
  - Requires managing multiple connection string secrets (`DATABASE_URL_PLAYER`, `DATABASE_URL_ADMIN`, `DATABASE_URL_INGEST`, `DATABASE_URL_MIGRATION`).

---

## 8. Points to Remember & Operational Guidelines

> [!IMPORTANT]
> **1. P0 Advance Without Victory Guard**: Never call `POST /api/v1/battle/next-turn` while the current boss has HP remaining (`boss_hp > 0`), the player is defeated (`player_hp <= 0`), or a question turn is in progress. The API will reject the request with `HTTP 400 Bad Request`.

> [!WARNING]
> **2. Content Security Policy (CSP) Whitelisting**: If you introduce new asset storage buckets or CDN domains, you **must** update the `img-src` directive in [app/observability/middleware.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/observability/middleware.py). Failing to whitelist a domain will cause browsers (especially Safari and Chrome) to block boss images with `net::ERR_BLOCKED_BY_CSP`.

> [!NOTE]
> **3. Bucket Name Case Sensitivity**: Supabase Storage buckets are strictly case-sensitive:
> - `DefaultBosses`
> - `AdvancedBosses`
> - `FoundationalBosses`
> Ensure all references in `.env`, [app/settings.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/settings.py), and `tracks_config.json` match this exact casing.

> [!TIP]
> **4. Decoupled Data Folder**: Never commit `data/tracks/` files back to Git. Both `.gitignore` and `.dockerignore` intentionally exclude this directory. Question releases must be published to PostgreSQL via `scripts/ingest_questions_to_postgres.py`.

> [!CAUTION]
> **5. Database Migrations via `ob_migrator`**: Always run Alembic migrations using `app.infrastructure.database.alembic_runner` with `DATABASE_URL_MIGRATION` (`ob_migrator` role). Running migrations under `ob_player` will fail with permission denied on `alembic_version` or DDL operations.

---

## 9. Local Development, Environment Setup & Testing

### 9.1 Prerequisites
- **Python 3.11+**
- **uv** (recommended package runner) or standard `pip`
- **PostgreSQL 15+** (or default Supabase connection)

### 9.2 Environment Configuration
Copy the template or configure your local environment file (`local.env` or `env`):

```ini
# --- Application Environment ---
ENVIRONMENT=development
PORT=8000
SECRET_KEY=change-this-to-a-secure-random-32-character-secret

# --- Database Connections (Least-Privilege Roles) ---
DATABASE_URL=postgresql+psycopg2://postgres.aamwrwbsrmorllisdffc:[PASSWORD]@aws-0-us-west-2.pooler.supabase.com:5432/postgres
DATABASE_URL_PLAYER=postgresql+psycopg2://ob_player:[PASSWORD]@aws-0-us-west-2.pooler.supabase.com:5432/postgres
DATABASE_URL_ADMIN=postgresql+psycopg2://ob_admin:[PASSWORD]@aws-0-us-west-2.pooler.supabase.com:5432/postgres
DATABASE_URL_INGEST=postgresql+psycopg2://ob_content_ingest:[PASSWORD]@aws-0-us-west-2.pooler.supabase.com:5432/postgres
DATABASE_URL_MIGRATION=postgresql+psycopg2://ob_migrator:[PASSWORD]@aws-0-us-west-2.pooler.supabase.com:5432/postgres

# --- S3 Object Storage Configuration ---
S3_ENDPOINT_URL=https://aamwrwbsrmorllisdffc.supabase.co/storage/v1/s3
S3_REGION=us-west-2
S3_ACCESS_KEY_ID=[ACCESS-KEY]
S3_SECRET_ACCESS_KEY=[SECRET-KEY]
S3_DEFAULT_BOSSES_BUCKET=DefaultBosses
S3_ADVANCED_BOSSES_BUCKET=AdvancedBosses
S3_FOUNDATIONAL_BOSSES_BUCKET=FoundationalBosses

# --- Admin Portal Credentials ---
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin
ADMIN_SESSION_TTL_HOURS=24
```

### 9.3 Launching the Server

#### Production Deployment (Gunicorn Multi-Worker)
```bash
# Launch with production Gunicorn process manager (default dynamic worker scaling)
uv run gunicorn -c gunicorn.conf.py app.main:app

# Or specify 2 workers explicitly via CLI flag:
uv run gunicorn -c gunicorn.conf.py -w 2 app.main:app

# Or override worker count and port via environment variables:
WEB_CONCURRENCY=4 PORT=8000 uv run gunicorn -c gunicorn.conf.py app.main:app
```

#### Docker Container Execution
```bash
# Build production Docker container
docker build -t organicbattles:latest .

# Run container (runs Gunicorn with 2 workers by default as defined in Dockerfile)
docker run -p 8000:8000 organicbattles:latest
```

#### Local Development (Live Reload)
```bash
# Run with single-process live reload for fast development iteration
uv run uvicorn app.main:app --reload --port 8000
```
Open [http://localhost:8000](http://localhost:8000) in your web browser.

### 9.4 Running the Test Suite
The repository includes 391 automated unit, integration, concurrency, and UI tests:

```bash
# Run complete test suite
uv run pytest

# Run quick summary
uv run pytest -q

# Run targeted Gunicorn configuration and multi-worker lifecycle tests
uv run pytest tests/test_gunicorn_config.py -v

# Run targeted combat concurrency tests
uv run pytest tests/test_combat_concurrency_and_optimistic_locking.py -v

# Run targeted battle retry and advance tests
uv run pytest tests/test_battle_retry_and_restart.py -v
```

---

## 10. Database Migration Safety & Content Ingestion Operational Guides

Detailed standalone guides have been established to ensure safe production database operations, zero-downtime content delivery, and architectural auditability:

### 10.1 Alembic Schema Migrations & Remote Supabase Safety
*Reference Document: [alembichelp.md](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/alembichelp.md)*

- **Zero DDL on Server Boot**: The application factory `create_app()` in [app/main.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/main.py) explicitly does **not** execute DDL migrations or `create_all()` when the server boots.
- **Least-Privilege Runtime Mode**: Gunicorn and Uvicorn workers execute only application queries (`SELECT`, `INSERT`, `UPDATE`), ensuring zero risk of accidental schema alterations on production databases.
- **Existing Supabase Data is 100% Preserved**: When connecting to a physically network-separated Supabase host, the application reads existing records in `OB_tracks`, `OB_curricula`, `OB_content_releases`, `OB_questions`, and `OB_users` without dropping, truncating, or altering existing data.
- **Additive & Non-Destructive Migrations**: All 9 Alembic revisions in `migrations/versions/` use `IF NOT EXISTS` constructs and state tracking via the `alembic_version` table.

### 10.2 Question & Answer Content Updates (`chapter_xx.json`)
*Reference Document: [QuestionsContentUpdate.md](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/QuestionsContentUpdate.md)*

- **Atomic Content Release Architecture**: Question updates from `chapter_xx.json` are ingested into draft releases in `OB_content_releases`, validated for integrity, and atomically published.
- **Zero Downtime & Zero Migrations**: Updates to questions, options, answers, explanations, damage spells, boss health, or boss names never alter database table schemas.
- **Admin Console Capabilities**:
  - Batch re-ingestion trigger (`POST /api/v1/admin/questions/ingest`).
  - Individual question search & inline editing (`PUT /api/v1/admin/questions/{id}`).
  - Question reordering with atomic release publishing.
  - One-click release rollback.
- **Feature Gap Analysis**: Documents future enhancements for in-browser drag-and-drop file upload, single-chapter update scoping, and pre-flight schema diff validation.

### 10.3 S3 / Object Storage Content Update Workflow
*Reference Document: [QuestionsContentUpdateS3.md](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/QuestionsContentUpdateS3.md)*

- **Distinct Tracks Buckets vs. Bosses Buckets**: The Supabase S3 storage topology strictly separates JSON questions from PNG image assets across 6 distinct public buckets:
  - **Tracks Buckets (JSON Questions & Curricula)**:
    - `AdvancedTracks`: Grouped into topic subfolders (`VocabularyConceptsData/`, `MechanismsIntermediatesData/`, `LabTechniquesGreenExpansionData/`, `ReactionOutcomeTypesData/`, etc.), each containing `chapter_01.json` through `chapter_27.json`.
    - `FoundationalTracks`: Grouped into topic subfolders (`VocabularyConceptsData/`, `ReactionOutComeTypesData/`, etc.).
    - `DefaultTracks`: Flat root-level `chapter_01.json` through `chapter_27.json`.
  - **Bosses Buckets (PNG Image Assets Only)**:
    - `DefaultBosses`, `AdvancedBosses`, `FoundationalBosses`: Flat root directory containing all boss portrait `.png` files (e.g. `1-3-diaxial-dreadnought.png`, `aldol-alchemist.png`, `orbital_ogre.png`). No chapter subfolders exist in Bosses buckets.
- **Passive S3 Drops Do Not Auto-Update Live Gameplay**: Uploading a `chapter_xx.json` file to S3 does not auto-update live gameplay on its own. Live combat queries PostgreSQL and cluster RAM caches for sub-2ms combat latency and S3 cost control.
- **The Intentional 2-Step Workflow**:
  1. **Upload to S3**:
     - For Advanced Tracks: `s3://AdvancedTracks/<TrackFolder>/chapter_xx.json` (e.g. `VocabularyConceptsData/chapter_01.json`).
     - For Default Track: `s3://DefaultTracks/chapter_xx.json`.
     - For New Bosses: Upload the companion `.png` directly to the root of `AdvancedBosses/` (or `DefaultBosses/`).
  2. **Trigger Ingestion**: Click **START BATCH INGESTION** in the Admin Console (or run `uv run python scripts/ingest_questions_to_postgres.py --track <id> --source s3`).
- **Architectural Protections**:
  - *Partial Upload Guard*: Prevents players from seeing half-uploaded or incomplete chapters while uploads are in flight.
  - *Cluster Cache Invalidation*: Triggering ingestion executes `shared_track_cache.invalidate_track()`, notifying all Gunicorn workers simultaneously with zero downtime.


### 10.4 Architecture Scalability Scorecard & Roadmap Status
*Reference Document: [todo.md](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/todo.md) & [walkthroughchange-09152026.md](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/walkthroughchange-09152026.md)*

- **Audit Metrics**: 77 items `[FIXED]` vs 15 items `[TODO]` (**83.7%** production readiness achieved).
- **Key Completed Subsystems**: In-memory state externalization to PostgreSQL `OB_sessions`, optimistic locking (`state_version`), Gunicorn multi-worker orchestration (`gunicorn.conf.py`), Alembic migrations, S3 CDN boss decoupling, and 391 green automated tests.
- **Pending Roadmap**: Background email outbox task worker, self-service password reset, dedicated CSRF token header, non-root Docker user, and cloud secret manager integration.

