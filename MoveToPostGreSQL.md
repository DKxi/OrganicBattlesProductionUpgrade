# Step-by-Step Guide: Moving Organic Battles to PostgreSQL & Adding Admin Storage Switches

This document provides complete, production-ready, step-by-step instructions to integrate **PostgreSQL** as a primary database for **Organic Battles (V4P)** while adding **live admin controls** to switch the database location (SQLite vs. PostgreSQL) and content file folders directly from the Admin Configuration screen.

---

## Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [Phase 1: PostgreSQL Setup & Provisioning](#2-phase-1-postgresql-setup--provisioning)
3. [Phase 2: Dynamic Database Engine (Hot-Swapping Engine)](#3-phase-2-dynamic-database-engine-hot-swapping-engine)
4. [Phase 3: SQLite to PostgreSQL Data Migration Engine](#4-phase-3-sqlite-to-postgresql-data-migration-engine)
5. [Phase 4: Admin API Endpoints for System & Folder Switches](#5-phase-4-admin-api-endpoints-for-system--folder-switches)
6. [Phase 5: Admin UI Controls in Dashboard](#6-phase-5-admin-ui-controls-in-dashboard)
7. [Phase 6: Frontend Controller Event Handlers](#7-phase-6-frontend-controller-event-handlers)
8. [Phase 7: Verification & Testing Checklist](#8-phase-7-verification--testing-checklist)

---

## 1. Architecture Overview

```mermaid
graph TD
    AdminUI[Admin Config Screen // System Tab] -->|1. Select DB Dialect & Set URI| AdminAPI[FastAPI /api/admin/system/database]
    AdminAPI -->|2. Test Connection & Validate| NewEngine[SQLAlchemy Engine: create_engine]
    NewEngine -->|3. Auto-Create Schema| Schema[Base.metadata.create_all]
    NewEngine -->|4. Optional Data Migration| Migrator[SQLite-to-PostgreSQL Data Transfer]
    AdminAPI -->|5. Hot-Rebind Session Factory| SessionLocal[SessionLocal.configure: bind=new_engine]
    AdminUI -->|6. Set Data & Boss Folder Paths| FolderAPI[FastAPI /api/admin/system/folders]
    FolderAPI -->|7. Persist & Hot-Reload| TracksConfig[tracks_config.json & TRACK_BUNDLES.clear]
```

### Key Design Principles:
1. **Zero-Restart Live Switching**: The database engine and session factory can be reconfigured dynamically without restarting the FastAPI ASGI process.
2. **Schema Auto-Provisioning**: When switching to PostgreSQL for the first time, all tables (`users`, `auth_sessions`, `game_sessions`, `verification_codes`) are created automatically.
3. **Selective Data Migration**: Admins can check a box to copy existing user accounts, progress, and battle states from the active SQLite database directly into PostgreSQL during the switch.
4. **Dynamic Folder Mapping**: Admins can retarget chapter JSON folders and boss image folders for any track and immediately flush in-memory caches.

---

## 2. Phase 1: PostgreSQL Setup & Provisioning

### 2.1 Start a PostgreSQL Instance

#### Option A: Local Docker Container (Recommended)
```bash
docker run --name organic-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=organic_battles \
  -p 5432:5432 -d postgres:16-alpine
```

#### Option B: macOS Homebrew
```bash
brew install postgresql@16
brew services start postgresql@16
createdb organic_battles
```

#### Option C: Cloud Hosted PostgreSQL (AWS RDS / Supabase / Neon)
Obtain your connection URI in the following standard format:
```
postgresql+psycopg2://<username>:<password>@<host>:<port>/<database_name>
```

### 2.2 Verify Driver in Python Virtual Environment
Verify `psycopg2` is installed:
```bash
.venv/bin/python -c "import psycopg2; print('PostgreSQL driver ready:', psycopg2.__version__)"
```

---

## 3. Phase 2: Dynamic Database Engine (Hot-Swapping Engine)

Update [app/infrastructure/database/engine.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/infrastructure/database/engine.py) to replace the static single engine with a **rebindable session factory**:

```python
import os
import sqlite3
import logging
from typing import Generator, Dict, Any
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import sessionmaker, Session as DBSession
from app.settings import settings
from app.infrastructure.database.models import Base

logger = logging.getLogger("organicbattles.database")

def build_engine(url: str) -> Engine:
    """Build a SQLAlchemy engine with dialect-specific connection pool settings."""
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(
        url,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_size=10 if not url.startswith("sqlite") else 5,
        max_overflow=20 if not url.startswith("sqlite") else 10,
    )

# Global active engine and session factory
current_db_url: str = settings.database_url
engine: Engine = build_engine(current_db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def switch_database(new_url: str) -> Dict[str, Any]:
    """
    Live-switch the active database engine and session factory.
    Creates schema tables on target if not present.
    """
    global engine, current_db_url
    logger.info("Switching database from %s to %s", current_db_url, new_url)

    # 1. Test connectivity
    test_engine = build_engine(new_url)
    with test_engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    # 2. Auto-create schema on target database
    Base.metadata.create_all(bind=test_engine)

    # 3. Dispose old engine and rebind sessionmaker
    engine.dispose()
    engine = test_engine
    current_db_url = new_url
    SessionLocal.configure(bind=engine)

    dialect = "postgresql" if new_url.startswith("postgresql") else "sqlite"
    return {"status": "ok", "dialect": dialect, "url": new_url}

def ensure_db_schema() -> None:
    """Ensure database tables exist on startup."""
    Base.metadata.create_all(bind=engine)

def get_db() -> Generator[DBSession, None, None]:
    """FastAPI dependency yielding a thread-safe database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## 4. Phase 3: SQLite to PostgreSQL Data Migration Engine

Create a new module at [app/infrastructure/database/migrator.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/infrastructure/database/migrator.py) to handle relational table copying:

```python
import logging
from sqlalchemy.orm import Session
from app.infrastructure.database.models import User, VerificationCode, AuthSession, GameSession

logger = logging.getLogger("organicbattles.migration")

def migrate_sqlite_to_postgres(source_engine, target_engine):
    """
    Copy all user accounts, credentials, auth tokens, and battle sessions
    from SQLite into PostgreSQL with preserved foreign keys.
    """
    with Session(source_engine) as src, Session(target_engine) as dst:
        # 1. Users
        users = src.query(User).all()
        for u in users:
            if not dst.query(User).filter(User.id == u.id).first():
                dst.merge(u)
        dst.commit()

        # 2. Verification Codes
        for vc in src.query(VerificationCode).all():
            dst.merge(vc)
        dst.commit()

        # 3. Auth Sessions
        for s in src.query(AuthSession).all():
            dst.merge(s)
        dst.commit()

        # 4. Game Sessions
        for gs in src.query(GameSession).all():
            dst.merge(gs)
        dst.commit()

    logger.info("Successfully migrated %d users and game sessions to PostgreSQL.", len(users))
```

---

## 5. Phase 4: Admin API Endpoints for System & Folder Switches

Add the following endpoints to [app/api/v1/admin.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/api/v1/admin.py):

### 5.1 Request Models
```python
class DatabaseSwitchRequest(BaseModel):
    dialect: str  # "sqlite" or "postgresql"
    connection_url: Optional[str] = None
    migrate_data: bool = False

class FolderSwitchRequest(BaseModel):
    track_id: Optional[str] = None  # None for default/all, or specific track
    data_folder: str
    boss_folder: Optional[str] = None
```

### 5.2 API Routes
```python
from app.infrastructure.database.engine import switch_database, current_db_url, build_engine
from app.infrastructure.database.migrator import migrate_sqlite_to_postgres
from app.domain.content.loader import load_tracks_config

@router.get("/admin/system/config")
def get_system_config(admin_info: dict = Depends(auth_admin)):
    """Return active database dialect and all track folder mappings."""
    dialect = "postgresql" if current_db_url.startswith("postgresql") else "sqlite"
    # Mask password for display
    display_url = current_db_url.split("@")[-1] if "@" in current_db_url else current_db_url
    return {
        "active_database": {
            "dialect": dialect,
            "url": display_url,
        },
        "tracks": load_tracks_config(settings.root_dir).get("tracks", []),
    }

@router.post("/admin/system/database")
def admin_switch_database(
    body: DatabaseSwitchRequest,
    admin_info: dict = Depends(auth_admin),
):
    """Switch active database between SQLite and PostgreSQL with optional live data migration."""
    if body.dialect == "sqlite":
        target_url = body.connection_url or f"sqlite:///{settings.root_dir / 'organic_battles.sqlite3'}"
    elif body.dialect == "postgresql":
        default_pg = "postgresql+psycopg2://postgres:postgres@localhost:5432/organic_battles"
        target_url = body.connection_url or default_pg
    else:
        raise HTTPException(400, "Unsupported dialect. Choose 'sqlite' or 'postgresql'.")

    old_url = current_db_url
    if body.migrate_data and old_url != target_url:
        source_engine = build_engine(old_url)
        target_engine = build_engine(target_url)
        from app.infrastructure.database.models import Base
        Base.metadata.create_all(bind=target_engine)
        migrate_sqlite_to_postgres(source_engine, target_engine)

    result = switch_database(target_url)
    return result

@router.post("/admin/system/folders")
def admin_switch_folders(
    body: FolderSwitchRequest,
    admin_info: dict = Depends(auth_admin),
):
    """Update data_folder and boss_folder paths in tracks_config.json and clear bundle cache."""
    config_path = settings.root_dir / "data" / "tracks_config.json"
    cfg = json.loads(config_path.read_text(encoding="utf-8"))

    updated = False
    for t in cfg.get("tracks", []):
        if not body.track_id or t.get("id") == body.track_id:
            t["data_folder"] = body.data_folder
            if body.boss_folder:
                t["boss_folder"] = body.boss_folder
            updated = True

    if not updated:
        raise HTTPException(404, f"Track '{body.track_id}' not found")

    config_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    # Invalidate in-memory cache so new paths are loaded immediately
    from app.api.deps import TRACK_BUNDLES
    TRACK_BUNDLES.clear()

    return {"status": "ok", "message": "Folder locations updated and bundle cache refreshed"}
```

---

## 6. Phase 5: Admin UI Controls in Dashboard

In [templates/index.html](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/templates/index.html), add a third tab to the Admin Dashboard:

```html
<!-- Inside .admin-tab-nav -->
<button id="admin-tab-system" class="admin-tab-btn" type="button">⚙ SYSTEM & STORAGE</button>

<!-- Inside #admin-dashboard-view -->
<div id="admin-system-tab-content" class="admin-tab-content hidden">
  <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">
    
    <!-- Left Column: Database Switch -->
    <div class="admin-card" style="margin: 0;">
      <div class="eyebrow">STORAGE // ENGINE LOCATION</div>
      <h3>DATABASE ENGINE</h3>
      <p style="font-size: 0.8rem; color: var(--muted); margin-bottom: 16px;">
        Switch the runtime database engine between local SQLite and network/cloud PostgreSQL.
      </p>

      <form id="admin-db-switch-form">
        <div style="display: flex; gap: 16px; margin: 12px 0;">
          <label style="cursor: pointer;">
            <input type="radio" name="db_dialect" value="sqlite"> SQLite (Local File)
          </label>
          <label style="cursor: pointer;">
            <input type="radio" name="db_dialect" value="postgresql"> PostgreSQL (Production DB)
          </label>
        </div>

        <label style="margin-top: 10px;">CONNECTION URI
          <input type="text" id="admin-db-uri-input" placeholder="postgresql+psycopg2://user:pass@localhost:5432/organic_battles" style="font-family: monospace; font-size: 0.8rem;">
        </label>

        <label style="margin-top: 12px; display: flex; align-items: center; gap: 8px; font-size: 0.8rem; cursor: pointer;">
          <input type="checkbox" id="admin-db-migrate-check" checked>
          <span>Copy existing records to new database on switch</span>
        </label>

        <button type="submit" class="primary" style="margin-top: 18px; width: 100%;">APPLY DATABASE SWITCH</button>
        <div id="admin-db-status" class="admin-modal-status" style="min-height: 18px; margin-top: 10px;"></div>
      </form>
    </div>

    <!-- Right Column: Track Folders Switch -->
    <div class="admin-card" style="margin: 0;">
      <div class="eyebrow">CONTENT // DIRECTORY MAPPINGS</div>
      <h3>CONTENT FOLDERS</h3>
      <p style="font-size: 0.8rem; color: var(--muted); margin-bottom: 16px;">
        Configure where chapter JSON files and boss image artwork are loaded from on the server.
      </p>

      <form id="admin-folder-switch-form">
        <label>SELECT TRACK
          <select id="admin-folder-track-select"></select>
        </label>

        <label style="margin-top: 10px;">CHAPTER DATA FOLDER
          <input type="text" id="admin-folder-data-input" placeholder="e.g. data/tracks/default" style="font-family: monospace; font-size: 0.8rem;" required>
        </label>

        <label style="margin-top: 10px;">BOSS IMAGES FOLDER
          <input type="text" id="admin-folder-boss-input" placeholder="e.g. data/tracks/default/bosses" style="font-family: monospace; font-size: 0.8rem;">
        </label>

        <button type="submit" class="primary" style="margin-top: 18px; width: 100%;">UPDATE FOLDER PATHS</button>
        <div id="admin-folder-status" class="admin-modal-status" style="min-height: 18px; margin-top: 10px;"></div>
      </form>
    </div>

  </div>
</div>
```

---

## 7. Phase 6: Frontend Controller Event Handlers

In [static/js/main.js](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/static/js/main.js), wire up the UI elements:

```javascript
// Tab Switching
$('#admin-tab-system')?.addEventListener('click', () => {
  $$('.admin-tab-btn').forEach(b => b.classList.remove('active'));
  $$('.admin-tab-content').forEach(c => c.classList.add('hidden'));
  $('#admin-tab-system')?.classList.add('active');
  $('#admin-system-tab-content')?.classList.remove('hidden');
  loadSystemStorageConfig();
});

// Load Active Config
async function loadSystemStorageConfig() {
  try {
    const res = await api('/api/admin/system/config');
    if (!res) return;
    
    // Set Database Radio & URI
    const isPg = res.active_database.dialect === 'postgresql';
    const radio = document.querySelector(`input[name="db_dialect"][value="${res.active_database.dialect}"]`);
    if (radio) radio.checked = true;
    const uriInput = $('#admin-db-uri-input');
    if (uriInput) uriInput.value = isPg ? res.active_database.url : '';
    
    // Populate Track Select
    const select = $('#admin-folder-track-select');
    if (select && res.tracks) {
      select.innerHTML = res.tracks.map(t => `<option value="${t.id}">${t.title} (${t.id})</option>`).join('');
      select.onchange = () => {
        const trk = res.tracks.find(t => t.id === select.value);
        if (trk) {
          $('#admin-folder-data-input').value = trk.data_folder || '';
          $('#admin-folder-boss-input').value = trk.boss_folder || '';
        }
      };
      select.dispatchEvent(new Event('change'));
    }
  } catch (err) {
    console.error('Failed to load storage config:', err);
  }
}

// Handle Database Switch
$('#admin-db-switch-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const dialect = document.querySelector('input[name="db_dialect"]:checked')?.value;
  const connection_url = $('#admin-db-uri-input')?.value.trim();
  const migrate_data = $('#admin-db-migrate-check')?.checked;
  const status = $('#admin-db-status');
  
  if (status) status.textContent = 'Switching database…';
  try {
    const res = await api('/api/admin/system/database', { dialect, connection_url, migrate_data });
    if (status) {
      status.textContent = `Switched to ${res.dialect.toUpperCase()} successfully!`;
      status.className = 'admin-modal-status hint';
    }
  } catch (err) {
    if (status) {
      status.textContent = `Error: ${err.message}`;
      status.className = 'admin-modal-status error';
    }
  }
});

// Handle Folder Switch
$('#admin-folder-switch-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const track_id = $('#admin-folder-track-select')?.value;
  const data_folder = $('#admin-folder-data-input')?.value.trim();
  const boss_folder = $('#admin-folder-boss-input')?.value.trim();
  const status = $('#admin-folder-status');

  if (status) status.textContent = 'Updating paths…';
  try {
    await api('/api/admin/system/folders', { track_id, data_folder, boss_folder });
    if (status) {
      status.textContent = 'Folders updated and cache cleared!';
      status.className = 'admin-modal-status hint';
    }
  } catch (err) {
    if (status) {
      status.textContent = `Error: ${err.message}`;
      status.className = 'admin-modal-status error';
    }
  }
});
```

---

## 8. Phase 7: Verification & Testing Checklist

### 1. Test PostgreSQL Switch via API
```bash
curl -X POST http://localhost:8000/api/admin/system/database \
  -H "Cookie: admin_token=<TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "dialect": "postgresql",
    "connection_url": "postgresql+psycopg2://postgres:postgres@localhost:5432/organic_battles",
    "migrate_data": true
  }'
```
*Expected Response*: `{"status": "ok", "dialect": "postgresql", "url": "..."}`

### 2. Verify Schema & Data in PostgreSQL
```bash
psql -U postgres -d organic_battles -c "\dt"
psql -U postgres -d organic_battles -c "SELECT username, email, verified FROM users;"
```
*Expected Output*: Tables `users`, `auth_sessions`, `game_sessions`, and `verification_codes` exist and contain all existing player rows.

### 3. Test Folder Switch via API
```bash
curl -X POST http://localhost:8000/api/admin/system/folders \
  -H "Cookie: admin_token=<TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "track_id": "default",
    "data_folder": "data/tracks/default",
    "boss_folder": "data/tracks/default/bosses"
  }'
```
*Expected Response*: `{"status": "ok", "message": "Folder locations updated and bundle cache refreshed"}`

### 4. Run Pytest Regression
```bash
.venv/bin/pytest
```
*Expected Result*: All 198 tests execute and pass cleanly.
