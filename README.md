# Organic Battles — Technical Documentation & Architecture Reference

**Organic Battles** is a browser-based educational role-playing game (RPG) designed to reinforce organic chemistry concepts through boss battles. Players choose alchemist companion avatars, cast chemistry spells across progressive difficulty tiers, and answer chapter-aligned chemistry vocabulary trials to defeat bosses and progress through 27 organic chemistry chapters.

---

## 1. System Overview & Technology Stack

```mermaid
flowchart TB
    subgraph Client["Client Browser (Single Page Application)"]
        UI["HTML5 UI & DOM Controls<br/>(main.js · avatars.js · game.css)"]
        Phaser["Phaser 3 Visual Arena<br/>(2D WebGL/Canvas · Dynamic Aura FX)"]
        AudioEngine["Web Audio Synthesizer<br/>(audio.js · Procedural SFX · Mute)"]
        AdminUI["Admin Configuration Portal<br/>(Users · Sessions · Reset/Delete)"]
        UI <--> Phaser
        UI --> AudioEngine
        UI --- AdminUI
    end

    subgraph Server["FastAPI Modular Backend (app/)"]
        Router["FastAPI Application Layer (app/main.py)"]
        SecurityMW["Security & Rate Limiting Middleware<br/>(HSTS · CSP · X-Frame · Slowapi)"]
        
        subgraph APILayer["API / Router Layer (app/api/v1/)"]
            AuthRouter["auth.py<br/>(/api/v1/auth/*)"]
            BattleRouter["battle.py<br/>(/api/v1/battle/*)"]
            GameRouter["game.py<br/>(/api/v1/game/*)"]
            AdminRouter["admin.py<br/>(/api/v1/admin/*)"]
        end

        subgraph DomainLayer["Pure Domain Logic (app/domain/)"]
            CombatRules["combat/rules.py & spells.py<br/>(Pure Python · 0 Framework Dependencies)"]
            ContentEngine["content/loader.py & resolver.py<br/>(27 Chapters · Boss Strategy Engine)"]
            AccountRules["accounts/entities.py"]
        end

        subgraph InfraLayer["Infrastructure Layer (app/infrastructure/)"]
            DBModels["database/models.py & session.py"]
            Repositories["database/repositories.py<br/>(UserRepository · SessionRepository)"]
            EmailService["messaging/smtp.py<br/>(Async SMTP / Worker Queue)"]
        end

        Router --> SecurityMW --> APILayer
        AuthRouter --> Repositories & EmailService
        BattleRouter --> CombatRules & Repositories & ContentEngine
        GameRouter --> ContentEngine & Repositories
        AdminRouter --> Repositories & ContentEngine
    end

    subgraph Persistence["Storage & Data"]
        subgraph DB["Relational Database (PostgreSQL / SQLite3)"]
            UsersTable[("OB_users")]
            SessionsTable[("OB_game_sessions")]
            AuthTable[("OB_auth_sessions")]
            OTPTable[("OB_verification_codes")]
            CurriculaTable[("OB_curricula")]
            TracksTable[("OB_tracks")]
            QuestionsTable[("OB_questions<br/>(27,000 Questions)")]
        end

        subgraph ContentFiles["Content Archive (data/tracks/)"]
            ConfigJSON["data/tracks_config.json"]
            TrackDirs["data/tracks/*<br/>(20 Tracks · 2 Curricula · 27 Chapters each)"]
        end
    end

    Client <-->|"REST API / JSON / Bearer & Cookies"| Router
    Repositories <--> DB
    ContentEngine <--> DB
    ContentEngine -.->|"Fallback"| TrackDirs
```

### Core Technologies

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| **Backend Framework** | **FastAPI** | `0.115.6` | High-performance async REST API with automatic OpenAPI docs and dependency injection. |
| **Settings & Validation** | **Pydantic V2 & Settings** | `2.10.4` | Strictly typed environment validation (`pydantic-settings`) and request/response serialization (`model_dump`). |
| **ASGI Server** | **Uvicorn** | `0.34.0` | Production ASGI web server supporting hot-reloading and multi-worker execution. |
| **Database & ORM** | **SQLAlchemy** | `2.0.36` | ORM repositories managing `OB_users`, `OB_game_sessions`, `OB_auth_sessions`, `OB_verification_codes`, `OB_curricula`, `OB_tracks`, and `OB_questions`. |
| **Database Engine** | **PostgreSQL / SQLite3** | `psycopg2` / Native | Default PostgreSQL via Supabase IPv4 Pooler (`aws-0-us-west-2.pooler.supabase.com:5432`) with connection pooling (`pool_size=10`, `max_overflow=20`) and local SQLite3 support with live bidirectional migration. |
| **Audio Synthesizer** | **Web Audio API** | Native Browser | Procedural, zero-download low-latency SFX engine in [`static/js/audio.js`](file:///Users/nkoneru/Downloads/AI%20Apps/OrganicBattles/static/js/audio.js). |
| **Frontend Framework** | **Vanilla JS (ES Modules)** | ES2022+ | Modular JavaScript (`main.js`, `avatars.js`, `audio.js`) without heavy node build toolchains. |
| **Styling** | **Vanilla CSS3** | Custom Theme | Glassmorphism, neon HUD accents, responsive cards, 4-tab admin portal, and dynamic battle arena. |
| **Game Engine** | **Phaser 3** | `3.60.0` (CDN) | 2D WebGL/Canvas arena rendering dynamic chapter auras and particle effects. |
| **Rate Limiting** | **Slowapi** | `0.1.9` | Token-bucket rate limiter protecting auth, signup, and combat endpoints. |
| **Test Suite** | **Pytest & HTTPX** | `8.3.4` / `0.28.1` | Automated test suite verifying combat rules, question sequential parity, tracks, PostgreSQL database, and admin management. |

---

## 2. Directory & Modular Architecture

The application is structured according to **Clean / Domain-Driven Architecture**, cleanly separating API controllers, pure domain rules, and infrastructure implementations:

```text
OrganicBattles/
├── app/                                # Modular Application Package
│   ├── main.py                         # FastAPI application factory, middleware, router mounts
│   ├── settings.py                     # Centralized Pydantic Settings (.env validator)
│   ├── api/                            # API Controller Layer
│   │   ├── deps.py                     # Dependency injection (get_db, get_current_user, get_bundle)
│   │   └── v1/                         # API Version 1 Routers
│   │       ├── auth.py                 # Signup, Login, Email OTP Verification, Logout
│   │       ├── battle.py               # Spell selection, Question answering, Next-turn, Retry
│   │       ├── game.py                 # New game initialization, State query, Avatar finalization
│   │       └── admin.py                # Admin auth, user content mode switcher, session manager
│   ├── domain/                         # Pure Business Logic (Zero Framework / DB Dependencies)
│   │   ├── accounts/                   # User entities, password hashing, session tokens
│   │   ├── combat/                     # Combat engine, spell catalog, turn damage grader, cooldowns
│   │   │   ├── entities.py             # Spell, CombatTurnResult dataclasses
│   │   │   ├── rules.py                # Pure evaluate_combat_turn, grade_answer, decrement_cooldowns
│   │   │   └── spells.py               # 9-spell catalog, tier categorization, damage defaults
│   │   ├── content/                    # Content engine and chapter loader
│   │   │   ├── entities.py             # ContentBundle dataclass
│   │   │   ├── loader.py               # JSON manifest & Chapter parser, builtin app bundle loader
│   │   │   └── resolver.py             # Content source resolution hierarchy
│   │   └── progression/                # Chapter advancing, boss progression, rewards
│   ├── infrastructure/                 # External Integrations & Data Layer
│   │   ├── database/                   # SQLAlchemy engine, session maker, declarative models
│   │   │   ├── models.py               # User, GameSession, AuthSession, VerificationCode models
│   │   │   ├── session.py              # Engine factory, get_db generator
│   │   │   └── repositories.py         # UserRepository, SessionRepository, AuthRepository
│   │   └── messaging/                  # SMTP email delivery, background workers
│   │       └── smtp.py                 # send_verification_code_email with console fallback
│   ├── observability/                  # Logging, telemetry, and health probes
│   │   ├── logging.py                  # Structured logging configuration
│   │   └── metrics.py                  # Live and ready health check probes
│   └── workers/                        # Async background job workers
│       └── email.py                    # Threaded/Async email delivery worker
├── data/                               # 27 Organic Chemistry Chapters (1,350 Questions · 135 Bosses)
│   ├── manifest.json                   # Master manifest mapping all 27 chapters
│   ├── chapter_01.json                 # Chapter 1: Foundations, Electrons, Bonds, Properties
│   ├── chapter_02.json                 # Chapter 2: Molecular Structure & Representations
│   └── ...                             # chapter_03.json through chapter_27.json
├── static/                             # Static Frontend Assets
│   ├── css/
│   │   └── game.css                    # Complete RPG design system, arena styling, admin portal
│   ├── js/
│   │   ├── main.js                     # Core application orchestrator, DOM event router, battle UI
│   │   ├── avatars.js                  # Companion avatar engine, customizable equipment, sprite states
│   │   └── audio.js                    # Web Audio procedural sound synthesizer (SFX & Mute)
│   └── assets/
│       ├── battle-arena.png            # High-resolution battle arena background
│       └── bosses/                     # 76+ boss illustrations (.png) and fallback SVG placeholder
├── templates/
│   └── index.html                      # Single-page app shell, HUD, combat modals, admin console
├── tests/                              # Automated Test Suite (41 Tests)
│   ├── conftest.py                     # Shared test fixtures, in-memory DB setup, auth helpers
│   ├── test_audio.py                   # 5 Web Audio & SFX integration tests
│   ├── test_boss_strategy.py           # 3 Boss Strategy mathematical distribution tests
│   ├── test_domain_combat.py           # 7 Pure Python domain combat & grading unit tests
│   ├── test_email_config.py            # 2 SMTP & configuration validation tests
│   └── test_game.py                    # 24 Full API integration, concurrency, and admin tests
├── pyproject.toml                      # Project metadata & Pytest configuration
├── requirements.txt                    # Pinned Python package dependencies
├── ProdUpgradeTasks.md                 # Production upgrade roadmap and completion checklist
└── README.md                           # Comprehensive architecture and technical documentation
```

---

## 3. System Architecture & Workflows

### 3.1 Content Mode Priority & Resolution Flow

Organic Battles supports both **Manifest-Driven JSON Content** (27 chapters, 135 bosses, 1,350 questions) and **Built-in App Content** (3 chapters, 14 bosses). Mode resolution occurs in strict order:

```mermaid
flowchart TD
    Req["Incoming API Request"] --> CheckEnv{"Is GAME_CONTENT_SOURCE<br/>set in environment / .env?"}

    CheckEnv -- Yes --> EnvPriority["Priority 1 (.env Override):<br/>Apply global mode (e.g. 'json' or 'app')"]
    CheckEnv -- No --> CheckDB{"Is content_source set<br/>on User record in DB?"}

    CheckDB -- Yes --> DBUser["Priority 2 (Database Setting):<br/>Apply user.content_source ('json' or 'app')"]
    CheckDB -- No --> DefaultMode["Priority 3 (Default Mode):<br/>Default to 'json' (27 Chapters Archive)"]

    EnvPriority --> LoadBundle["Retrieve Bundle from Memory Cache<br/>(JSON_BUNDLE or APP_BUNDLE)"]
    DBUser --> LoadBundle
    DefaultMode --> LoadBundle

    LoadBundle --> ServeState["Serve Game State with Resolved Chapter, Boss & Dynamic Spells"]
```

---

### 3.2 Boss Strategy & Difficulty Progression Engine

Every chapter file in `data/chapter_*.json` defines an explicit `boss_strategy` object governing difficulty distribution and scaling across 5 consecutive bosses:

$$\text{Strategy Rule:} \quad \text{Easy} = 6 - i, \quad \text{Medium} = 4, \quad \text{Hard} = i \quad (i \in [0, 4])$$

```mermaid
flowchart LR
    subgraph Chapter["Chapter Structure (50 Questions · 5 Bosses)"]
        B1["Boss 1 (e.g. Orbital Ogre)<br/>HP: 100 · Spells: [20, 30, 45]<br/>6 Easy · 4 Med · 0 Hard"]
        B2["Boss 2 (e.g. Bondbreaker Brute)<br/>HP: 200 · Spells: [25, 35, 50]<br/>5 Easy · 4 Med · 1 Hard"]
        B3["Boss 3 (e.g. Hybridization Goblin)<br/>HP: 300 · Spells: [30, 40, 55]<br/>4 Easy · 4 Med · 2 Hard"]
        B4["Boss 4 (e.g. Polarity Phantom)<br/>HP: 400 · Spells: [35, 45, 60]<br/>3 Easy · 4 Med · 3 Hard"]
        B5["Boss 5 (e.g. Molecular Property Titan)<br/>HP: 500 · Spells: [40, 50, 65]<br/>2 Easy · 4 Med · 4 Hard"]
    end

    B1 -->|Defeated| B2 -->|Defeated| B3 -->|Defeated| B4 -->|Defeated| B5
```

---

### 3.3 Combat & Turn Lifecycle Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Player as Player (Browser)
    participant UI as main.js & audio.js
    participant API as FastAPI (/api/v1/battle/*)
    participant Domain as Combat Domain (rules.py)
    participant DB as SQLite / PostgreSQL

    Player->>UI: Clicks Spell (e.g. 'fire-spark')
    UI->>UI: soundEngine.playSpellCast('basic')
    UI->>API: POST /api/v1/battle/select-spell { spell_id: "fire-spark" }
    API->>DB: Fetch GameSession & Validate (HP > 0, Cooldown expired)
    API->>API: Fetch sequential question from Chapter/Boss bank via cursor
    API->>DB: Save active_question_json, active_spell, turn_id
    API-->>UI: Return Question Prompt + 4 Choices (Answer secret stripped)
    UI->>Player: Render Vocabulary Trial Panel

    Player->>UI: Selects Answer Choice
    UI->>UI: soundEngine.playClick()
    UI->>API: POST /api/v1/battle/answer { answer: "Choice B" }
    API->>Domain: evaluate_combat_turn(spell_id, answer, secret, current_hp)
    Domain-->>API: CombatTurnResult (correct, damage, self_damage, boss_hit, defeat, defeated)

    alt Correct Answer
        API->>DB: Apply damage to Boss HP, increment question cursor, apply cooldown
        API-->>UI: Return Result (correct: True, damage dealt, remaining boss HP)
        UI->>UI: soundEngine.playBossHit()
        alt Counterattack Lands
            UI->>UI: soundEngine.playPlayerHit()
        else Counterattack Misses
            UI->>UI: soundEngine.playBossMiss()
        end
        UI->>Player: Trigger Attack Animation & Battle Report Modal
    else Incorrect Answer (Fizzle)
        API->>DB: Apply self_damage to Player HP, increment question cursor, apply cooldown
        API-->>UI: Return Result (correct: False, self_damage, explanation, defeat flag)
        UI->>UI: soundEngine.playSpellFizzle()
        UI->>UI: soundEngine.playPlayerHit()
        alt Player Depleted (Defeat)
            UI->>UI: soundEngine.playDefeat()
            UI->>Player: Show DEFEAT Modal & Unlock [ RETRY BATTLE ] button
        else Player Survives
            UI->>Player: Show SPELL FIZZLE Modal with [ VIEW EXPLANATION ]
        end
    end
```

---

## 4. Web Audio Procedural Sound Engine

Located in [`static/js/audio.js`](file:///Users/nkoneru/Downloads/AI%20Apps/OrganicBattles/static/js/audio.js), the audio engine generates procedural sound effects via the Web Audio API with zero external media files:

- **Mute Control**: Persistent toggle mapped to the `#mute` button; saved in browser `localStorage` (`orgo_audio_muted`).
- **Power Optimization**: Automatically suspends `AudioContext` on `document.visibilitychange` when the tab is hidden and resumes when active.
- **Synthesized SFX Roster**:
  - `playClick()`: High-frequency UI tap ($800\text{ Hz}$).
  - `playSpellCast(tier)`: Rising exponential sweep ($180\text{ Hz} \to 720\text{ Hz}$) scaled by spell rank.
  - `playBossHit()`: Low-frequency impact punch ($140\text{ Hz} \to 40\text{ Hz}$).
  - `playPlayerHit()`: Combat damage pulse ($120\text{ Hz} \to 60\text{ Hz}$).
  - `playSpellFizzle()`: Descending sawtooth backfire buzz ($320\text{ Hz} \to 90\text{ Hz}$).
  - `playBossMiss()`: Air whoosh sweep ($500\text{ Hz} \to 200\text{ Hz}$).
  - `playVictory()`: Ascending 4-note major fanfare ($C_5 \to E_5 \to G_5 \to C_6$).
  - `playDefeat()`: Descending 4-note minor sequence ($F_4 \to D_4 \to B\flat_3 \to A_3$).

---

## 5. REST API Reference (`/api/v1/`)

### Authentication (`/api/v1/auth`)

| Endpoint | Method | Payload | Response | Description |
|---|---|---|---|---|
| `/api/v1/auth/signup` | `POST` | `{ "email": str, "username": str, "password": str }` | `200 OK` | Registers a new account and sends a 6-digit confirmation code via SMTP. |
| `/api/v1/auth/verify` | `POST` | `{ "code": str }` | `200 OK` | Verifies the OTP, activates the account, and issues a session token. |
| `/api/v1/auth/login` | `POST` | `{ "username": str (or "email"), "password": str }` | `200 OK` | Authenticates by username or email and returns a session cookie and token. |
| `/api/v1/auth/logout` | `POST` | *None* | `200 OK` | Invalidates the active auth session and clears the cookie. |

### Game & Avatar (`/api/v1/game`, `/api/v1/avatar`)

| Endpoint | Method | Payload | Response | Description |
|---|---|---|---|---|
| `/api/v1/game/new` | `POST` | *None* | `200 OK` | Initializes or retrieves the player's active chapter and boss session. |
| `/api/v1/game/state` | `GET` | *None* (or `session_id`) | `200 OK` | Returns full formatted game state (HP, Boss, Active Spells, Cooldowns). |
| `/api/v1/avatar/finalize` | `POST` | `{ "character": str, "config": dict }` | `200 OK` | Selects or updates the player's active companion avatar. |

### Battle & Combat (`/api/v1/battle`)

| Endpoint | Method | Payload | Response | Description |
|---|---|---|---|---|
| `/api/v1/battle/select-spell`| `POST` | `{ "spell_id": str }` | `200 OK` | Validates cooldowns and primes the next sequential chemistry trial question. |
| `/api/v1/battle/answer` | `POST` | `{ "answer": str }` | `200 OK` | Evaluates the submitted answer, calculates damage, and advances turn state. |
| `/api/v1/battle/next-turn` | `POST` | *None* | `200 OK` | Advances to the next boss in the chapter or triggers chapter completion. |
| `/api/v1/battle/retry` | `POST` | *None* | `200 OK` | Resets player HP to 150, restores boss HP, and clears cooldowns after defeat. |

### Admin Management (`/api/v1/admin`)

| Endpoint | Method | Payload | Response | Description |
|---|---|---|---|---|
| `/api/v1/admin/login` | `POST` | `{ "username": str, "password": str }` | `200 OK` | Authenticates administrator (`admin` / `admin`). |
| `/api/v1/admin/users` | `GET` | *None* | `200 OK` | Lists all user accounts, companion avatars, and verification statuses. |
| `/api/v1/admin/users/{id}/credentials` | `POST` | `{ "username": str?, "password": str? }` | `200 OK` | Renames username or resets user password securely. |
| `/api/v1/admin/users/clean-test` | `POST` | *None* | `200 OK` | Safely purges automated test accounts and associated session cascades. |
| `/api/v1/admin/sessions` | `GET` | *None* | `200 OK` | Lists all active gameplay sessions across users. |
| `/api/v1/admin/sessions/{id}/reset` | `POST` | `{ "chapter": int }` | `200 OK` | Resets a session to Boss 1 of the chosen chapter with full health. |
| `/api/v1/admin/sessions/{id}` | `DELETE`| *None* | `200 OK` | Deletes a gameplay session and resets player progress. |
| `/api/v1/admin/storage/stats` | `GET` | *None* | `200 OK` | Returns database engine dialect, pooler host/port, and table row counts. |
| `/api/v1/admin/system/stats` | `GET` | *None* | `200 OK` | Returns host server uptime, OS platform, memory RSS/VMS, and CPU load. |
| `/api/v1/admin/migrate-db` | `POST` | *None* | `200 OK` | Triggers background bidirectional migration between SQLite and PostgreSQL. |
| `/api/v1/admin/migrate-db/status` | `GET` | *None* | `200 OK` | Polls active migration status, progress percentage, and copied row counts. |
| `/api/v1/admin/tracks` | `GET` | *None* | `200 OK` | Lists all 20 configured tracks across curricula from the database. |
| `/api/v1/admin/curricula` | `GET` | *None* | `200 OK` | Lists all curricula (`foundational`, `advanced`) and track counts. |


---

## 6. Environment Configuration & Setup

Configuration is validated via Pydantic Settings in [`app/settings.py`](file:///Users/nkoneru/Downloads/AI%20Apps/OrganicBattles/app/settings.py). Create an `env` or `.env` file in the project root:

```ini
# --- Application Environment ---
ENVIRONMENT=development
DEBUG=true
PORT=8000
SECRET_KEY=change-this-to-a-secure-random-32-character-secret

# --- Content Engine ---
# Questions are resolved dynamically based on user track selection

# --- Database Configuration ---
# Option 1: PostgreSQL / Supabase IPv4 Pooler (Default):
DATABASE_URL=postgresql+psycopg2://postgres.aamwrwbsrmorllisdffc:[REDACTED-PASSWORD]@aws-0-us-west-2.pooler.supabase.com:5432/postgres

# Option 2: SQLite (Local file database):
# DATABASE_URL=sqlite:///./organic_battles.sqlite3

# --- Admin Credentials ---
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin
ADMIN_SESSION_TTL_HOURS=24

# --- SMTP / Email Configuration ---
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password
SMTP_FROM=Organic Battles <your-email@gmail.com>
SMTP_TLS=true
```

---

## 7. Running the Application & Automated Tests

### 7.1 Local Development Server
```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start Uvicorn ASGI server with live reload
uvicorn app.main:app --reload --port 8000
```
Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your web browser.

### 7.2 Running the Full Automated Test Suite
```bash
# Run full automated test suite
pytest

# Run with verbose output
pytest -v

# Run targeted question parity and database tests
pytest tests/test_question_parity.py tests/test_tracks_postgresql.py -v
```
