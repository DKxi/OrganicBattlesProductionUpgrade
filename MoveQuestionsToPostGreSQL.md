# Step-by-Step Guide: Moving Question Banks to PostgreSQL

This document provides a comprehensive, production-grade, step-by-step roadmap to migrate all **28,400+ questions** across **20 tracks** from flat JSON files into **PostgreSQL**.

> [!IMPORTANT]
> **Sequential Question Ordering is Critical**:
> In Organic Battles, combat progression relies on session cursors (`game_session.question_cursors_json`), which track how many questions a player has answered for a specific chapter and boss (`f"{chapter}:{boss_slug}"`). 
> The database schema, indexes, ingestion pipeline, and query resolvers **must maintain strict, deterministic question order** (`order_index ASC`) matching the original JSON array order so players receive questions in the exact intended pedagogical sequence.

---

## Table of Contents
1. [Question Bank & Source Code Analysis](#1-question-bank--source-code-analysis)
2. [Database Schema & Ordering Strategy](#2-database-schema--ordering-strategy)
3. [Phase 1: SQLAlchemy Model Definition](#3-phase-1-sqlalchemy-model-definition)
4. [Phase 2: High-Performance Batch Ingestion Script](#4-phase-2-high-performance-batch-ingestion-script)
5. [Phase 3: Content Loader Integration & In-Memory Caching](#5-phase-3-content-loader-integration--in-memory-caching)
6. [Phase 4: SQLite-to-PostgreSQL Migrator Extension](#6-phase-4-sqlite-to-postgresql-migrator-extension)
7. [Phase 5: Admin REST APIs for Question Browsing & Reordering](#7-phase-5-admin-rest-apis-for-question-browsing--reordering)
8. [Phase 6: Verification, Parity Tests & Rollback Strategy](#8-phase-6-verification-parity-tests--rollback-strategy)

---

## 1. Question Bank & Source Code Analysis

### 1.1 JSON Dataset Metrics
- **Location**: `data/tracks/{track_id}/chapter_*.json` and root fallback `data/chapter_*.json`.
- **Total Tracks**: 20 tracks (Foundational Chemistry, Advanced Organic Chemistry, MCAT Prep, etc.).
- **Total Questions**: **28,400 questions** (~43 MB total JSON payload).
- **Structure per Track**:
  - Foundational tracks: 31 chapters × 50 questions = 1,550 questions per track.
  - Advanced tracks: 27 chapters × 50 questions = 1,350 questions per track.
  - Default / Template tracks: 3–31 chapters.

### 1.2 Structure of a Question Object in JSON
Each question in `chapter_XX.json` contains:
```json
{
  "id": "ch01_q001",
  "chapter": 1,
  "chapter_title": "Atomic Structure & Chemical Bonding",
  "boss": "Orbital Ogre",
  "topic": "Electron Configurations & Quantum Numbers",
  "difficulty": "Easy",
  "question_type": "Multiple Choice",
  "question": "What is the maximum number of electrons that can occupy a set of p orbitals?",
  "options": [
    {"label": "A", "text": "2"},
    {"label": "B", "text": "6"},
    {"label": "C", "text": "10"},
    {"label": "D", "text": "14"}
  ],
  "correct_option": "B",
  "correct_answer": "6",
  "explanation": "A p subshell contains 3 p orbitals (px, py, pz). Each orbital can hold up to 2 electrons with opposite spins...",
  "spells": [20, 30, 45],
  "health": [100],
  "images": ["orbital-ogre.png"]
}
```

### 1.3 Key Finding: ID Collision Across Tracks
- The field `"id": "ch01_q001"` is **not unique across tracks**; multiple tracks have their own question `ch01_q001`.
- **Requirement**: The PostgreSQL table must use either:
  1. An autoincrementing `BigInteger` surrogate primary key (`id`).
  2. A composite unique constraint on `(track_id, chapter, boss_slug, order_index)`.
  3. Preservation of `raw_id` (`"ch01_q001"`) for external reference.

### 1.4 How the Battle Engine Delivers Questions
In `app/api/v1/battle.py`:
```python
# 1. Look up questions bank for (chapter, boss_slug)
bank = bundle.question_boss_bank.get((game_session.chapter, boss_slug)) or bundle.question_boss_bank.get(boss_slug)

# 2. Extract player's sequential cursor for this boss
cursors = json.loads(game_session.question_cursors_json)
cursor_key = f"{game_session.chapter}:{boss_slug}"
q_idx = cursors.get(cursor_key, 0) % len(bank)

# 3. Retrieve question tuple: (prompt, choices, correct_answer)
q_tuple = bank[q_idx]

# 4. On correct/incorrect answer submission:
cursors[cursor_key] = cursors.get(cursor_key, 0) + 1
game_session.question_cursors_json = json.dumps(cursors)
```

**Why Order Matters**:
- `q_idx = cursors.get(cursor_key, 0) % len(bank)` assumes that `bank` is a list where index `0` is the 1st question, index `1` is the 2nd question, etc.
- If rows in PostgreSQL are returned in arbitrary order (e.g. natural disk heap order without `ORDER BY`), players will receive questions out of pedagogical sequence, or repeat questions unpredictably.
- **Solution**: Explicit column `order_index INT NOT NULL` (0, 1, 2, ..., 49) representing the exact zero-based position in the chapter JSON array.

---

## 2. Database Schema & Ordering Strategy

### 2.1 Table Definition: `questions`

```sql
CREATE TABLE questions (
    id BIGSERIAL PRIMARY KEY,
    track_id VARCHAR NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    raw_id VARCHAR(64) NOT NULL,            -- e.g. "ch01_q001"
    chapter INTEGER NOT NULL,               -- 1 to 31
    chapter_title VARCHAR(255) NOT NULL,
    boss_name VARCHAR(255) NOT NULL,        -- e.g. "Orbital Ogre"
    boss_slug VARCHAR(255) NOT NULL,        -- e.g. "orbital-ogre"
    order_index INTEGER NOT NULL,           -- 0 to 49 (Sequential order!)
    topic VARCHAR(255),
    difficulty VARCHAR(64),
    question_type VARCHAR(64) DEFAULT 'Multiple Choice',
    prompt TEXT NOT NULL,
    options_json JSONB NOT NULL,            -- [{"label":"A","text":"..."}, ...]
    correct_option VARCHAR(8) NOT NULL,     -- "A", "B", "C", "D"
    correct_answer TEXT NOT NULL,
    explanation TEXT NOT NULL,
    spells_json JSONB NOT NULL,             -- [20, 30, 45]
    health_json JSONB NOT NULL,             -- [100]
    images_json JSONB NOT NULL,             -- ["orbital-ogre.png"]
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 Critical Ordering & Performance Indexes

```sql
-- 1. Deterministic Battle Query Index (Composite)
-- Solves: SELECT * FROM questions WHERE track_id = :tid AND chapter = :ch AND boss_slug = :boss ORDER BY order_index ASC;
CREATE INDEX ix_questions_track_ch_boss_order 
ON questions (track_id, chapter, boss_slug, order_index ASC);

-- 2. Chapter-level Question Bank Index
-- Solves: SELECT * FROM questions WHERE track_id = :tid AND chapter = :ch ORDER BY order_index ASC;
CREATE INDEX ix_questions_track_ch_order 
ON questions (track_id, chapter, order_index ASC);

-- 3. Integrity Constraint: Guarantee no duplicate order_index per boss in a chapter
CREATE UNIQUE INDEX uq_questions_track_ch_boss_order 
ON questions (track_id, chapter, boss_slug, order_index);
```

---

## 3. Phase 1: SQLAlchemy Model Definition

Update [app/infrastructure/database/models.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/infrastructure/database/models.py) to add the `Question` model and link it with `Track`:

```python
# app/infrastructure/database/models.py
from sqlalchemy import (
    Column, String, Integer, BigInteger, Text, ForeignKey,
    UniqueConstraint, Index, DateTime, func
)
from sqlalchemy.orm import relationship

class Question(Base):
    __tablename__ = "questions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    track_id = Column(String, ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False, index=True)
    raw_id = Column(String(64), nullable=False)
    chapter = Column(Integer, nullable=False)
    chapter_title = Column(String(255), nullable=False)
    boss_name = Column(String(255), nullable=False)
    boss_slug = Column(String(255), nullable=False)
    order_index = Column(Integer, nullable=False)  # Preserves JSON question sequence
    topic = Column(String(255), nullable=True)
    difficulty = Column(String(64), nullable=True)
    question_type = Column(String(64), nullable=False, default="Multiple Choice")
    prompt = Column(Text, nullable=False)
    options_json = Column(Text, nullable=False)    # Stored as JSON string or JSONB
    correct_option = Column(String(8), nullable=False)
    correct_answer = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    spells_json = Column(Text, nullable=False, default="[20, 30, 45]")
    health_json = Column(Text, nullable=False, default="[100]")
    images_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship back to Track
    track = relationship("Track", back_populates="questions_rel")

    __table_args__ = (
        Index("ix_questions_track_ch_boss_order", "track_id", "chapter", "boss_slug", "order_index"),
        Index("ix_questions_track_ch_order", "track_id", "chapter", "order_index"),
        UniqueConstraint("track_id", "chapter", "boss_slug", "order_index", name="uq_questions_order"),
    )
```

In the existing `Track` model:
```python
# In Track model:
questions_rel = relationship(
    "Question", 
    back_populates="track", 
    cascade="all, delete-orphan", 
    order_by="Question.order_index"
)
```

---

## 4. Phase 2: High-Performance Batch Ingestion Script

Because there are **28,400 questions**, inserting them one-by-one with `db.add()` would take minutes. Using SQLAlchemy's `session.bulk_insert_mappings()` or PostgreSQL batch insert takes **under 3 seconds**.

Create `scripts/ingest_questions_to_postgres.py`:

```python
#!/usr/bin/env python3
"""
Batch Ingest Question Banks into PostgreSQL.
Preserves strict order_index from JSON arrays.
"""
import os
import sys
import json
import logging
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.infrastructure.database.engine import SessionLocal, get_active_engine
from app.infrastructure.database.models import Base, Track, Question
from app.domain.content.loader import _slug

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest")

def ingest_all_questions(batch_size: int = 1000):
    engine = get_active_engine()
    Base.metadata.create_all(bind=engine)
    
    data_tracks_dir = ROOT_DIR / "data" / "tracks"
    if not data_tracks_dir.exists():
        logger.error("No data/tracks directory found at %s", data_tracks_dir)
        return

    with SessionLocal() as db:
        tracks = {t.id: t for t in db.query(Track).all()}
        if not tracks:
            logger.warning("No tracks found in database! Ensure tracks_config has been synced first.")
            return

        total_ingested = 0

        for track_id, track in tracks.items():
            track_dir = ROOT_DIR / track.data_folder if not Path(track.data_folder).is_absolute() else Path(track.data_folder)
            if not track_dir.is_dir():
                logger.warning("Track %s folder not found: %s", track_id, track_dir)
                continue

            chapter_files = sorted(list(track_dir.glob("chapter_*.json")))
            if not chapter_files:
                continue

            logger.info("Processing track '%s' (%d chapter files)...", track_id, len(chapter_files))
            
            # Wipe existing questions for clean idempotent ingestion
            db.query(Question).filter(Question.track_id == track_id).delete()
            db.commit()

            buffer = []
            for ch_file in chapter_files:
                try:
                    payload = json.loads(ch_file.read_text(encoding="utf-8"))
                except Exception as exc:
                    logger.error("Failed to parse %s: %s", ch_file, exc)
                    continue

                ch_num = int(payload.get("chapter", 1))
                ch_title = payload.get("chapter_title", f"Chapter {ch_num}")
                default_boss = payload.get("assigned_boss", "Organic Chemistry Boss")
                raw_questions = payload.get("questions", [])

                # Map order_index sequentially per (chapter, boss_slug)
                boss_counters = {}

                for q_data in raw_questions:
                    boss_name = q_data.get("boss") or default_boss
                    boss_slug = _slug(boss_name)
                    
                    # Sequential order index within this boss's question pool
                    current_order = boss_counters.get(boss_slug, 0)
                    boss_counters[boss_slug] = current_order + 1

                    choices = [opt.get("text", "") for opt in q_data.get("options", [])]
                    correct_ans = q_data.get("correct_answer", choices[0] if choices else "")

                    buffer.append({
                        "track_id": track_id,
                        "raw_id": q_data.get("id", f"ch{ch_num:02d}_q{current_order:03d}"),
                        "chapter": ch_num,
                        "chapter_title": ch_title,
                        "boss_name": boss_name,
                        "boss_slug": boss_slug,
                        "order_index": current_order,  # STRICT ORDER
                        "topic": q_data.get("topic", "General Organic Chemistry"),
                        "difficulty": q_data.get("difficulty", "Medium"),
                        "question_type": q_data.get("question_type", "Multiple Choice"),
                        "prompt": q_data.get("question", ""),
                        "options_json": json.dumps(q_data.get("options", [])),
                        "correct_option": q_data.get("correct_option", "A"),
                        "correct_answer": correct_ans,
                        "explanation": q_data.get("explanation", ""),
                        "spells_json": json.dumps(q_data.get("spells", [20, 30, 45])),
                        "health_json": json.dumps(q_data.get("health", [100])),
                        "images_json": json.dumps(q_data.get("images", [f"{boss_slug}.png"])),
                    })

                    if len(buffer) >= batch_size:
                        db.bulk_insert_mappings(Question, buffer)
                        db.commit()
                        total_ingested += len(buffer)
                        buffer.clear()

            if buffer:
                db.bulk_insert_mappings(Question, buffer)
                db.commit()
                total_ingested += len(buffer)
                buffer.clear()

        logger.info("Successfully ingested %d questions into PostgreSQL!", total_ingested)

if __name__ == "__main__":
    ingest_all_questions()
```

---

## 5. Phase 3: Content Loader Integration & In-Memory Caching

To keep combat response times under **5 milliseconds**, we maintain the high-performance `ContentBundle` in-memory structure while backing it directly with PostgreSQL.

### 5.1 Add DB Loader to `app/domain/content/loader.py`

```python
def load_db_bundle(track_id: str, db: DBSession) -> Optional[ContentBundle]:
    """
    Build a ContentBundle directly from PostgreSQL questions table.
    Preserves exact order_index sequence for question_boss_bank.
    """
    from app.infrastructure.database.models import Question, Track
    
    questions = (
        db.query(Question)
        .filter(Question.track_id == track_id)
        .order_by(Question.chapter.asc(), Question.order_index.asc())
        .all()
    )
    if not questions:
        return None

    chapters_map = {}
    question_bank = {}
    question_boss_bank = {}
    boss_spell_values = {}
    explanations = {}
    boss_images = {}
    spell_values = {}
    spell_damage = {}

    for q in questions:
        ch_id = q.chapter
        options = json.loads(q.options_json)
        choices = [opt["text"] for opt in options]
        prompt = q.prompt
        correct = q.correct_answer
        q_tuple = (prompt, choices, correct)

        explanations[prompt] = q.explanation
        images = json.loads(q.images_json)
        boss_image = images[0] if images else f"{q.boss_slug}.png"
        boss_images[prompt] = boss_image
        boss_images[q.boss_slug] = boss_image
        boss_images[q.boss_name] = boss_image

        sp_vals = [int(v) for v in json.loads(q.spells_json)]
        spell_values[(ch_id, q.boss_slug, prompt)] = sp_vals
        spell_values.setdefault(prompt, sp_vals)
        for dmg in sp_vals:
            spell_damage[int(dmg)] = int(dmg)

        # STRICT ORDER PRESERVATION:
        # Since query is ORDER BY Question.order_index ASC,
        # appending to list retains the exact sequence.
        question_bank.setdefault(ch_id, []).append(q_tuple)
        question_boss_bank.setdefault((ch_id, q.boss_slug), []).append(q_tuple)
        question_boss_bank.setdefault(q.boss_slug, []).append(q_tuple)
        boss_spell_values.setdefault((ch_id, q.boss_slug), sp_vals)
        boss_spell_values.setdefault(q.boss_slug, sp_vals)

        # Build chapter metadata dynamically
        if ch_id not in chapters_map:
            chapters_map[ch_id] = {
                "id": ch_id,
                "name": q.chapter_title,
                "subtitle": "PostgreSQL Neural Archive",
                "color": ["#27d9cb", "#9a7cff", "#e34dff", "#ff9f5a"][(ch_id - 1) % 4],
                "bosses_map": {},
            }
        
        b_map = chapters_map[ch_id]["bosses_map"]
        if q.boss_slug not in b_map:
            health = max([int(h) for h in json.loads(q.health_json)] or [100])
            b_map[q.boss_slug] = (
                q.boss_slug,
                q.boss_name,
                health,
                15,
                "Mini-Boss",
                f"{q.chapter_title} // {q.topic}",
                boss_image,
            )

    # Finalize chapters list
    chapters = []
    for ch_id in sorted(chapters_map.keys()):
        ch_meta = chapters_map[ch_id]
        bosses_list = list(ch_meta["bosses_map"].values())
        if bosses_list:
            # Mark the last boss as MAJOR BOSS
            last_boss = bosses_list[-1]
            bosses_list[-1] = (
                last_boss[0], last_boss[1], last_boss[2], last_boss[3],
                "MAJOR BOSS", last_boss[5], last_boss[6]
            )
        ch_meta["bosses"] = bosses_list
        del ch_meta["bosses_map"]
        chapters.append(ch_meta)

    return ContentBundle(
        source_name=f"postgres:{track_id}",
        chapters=chapters,
        questions=[q for q_list in question_bank.values() for q in q_list],
        question_bank_by_chapter=question_bank,
        question_boss_bank=question_boss_bank,
        boss_spell_values=boss_spell_values,
        explanations=explanations,
        boss_images=boss_images,
        spell_values=spell_values,
        spells=dict(BUILTIN_SPELLS),
        json_spell_damage=spell_damage,
        data_dir=None,
        boss_dir=None,
    )
```

### 5.2 Hot-Caching in `load_track_bundle`
In `app/domain/content/loader.py`:
```python
def load_track_bundle(root_dir: Path, track_id: str, db: Optional[DBSession] = None) -> ContentBundle:
    # 1. If database connection is active, try loading from PostgreSQL
    if db is not None:
        try:
            bundle = load_db_bundle(track_id, db)
            if bundle and bundle.questions:
                return bundle
        except Exception as exc:
            logger.warning("Falling back to JSON files for track %s: %s", track_id, exc)

    # 2. Fallback to existing JSON bundle reader
    return load_json_track_bundle(root_dir, track_id)
```

---

## 6. Phase 4: SQLite-to-PostgreSQL Migrator Extension

Update [app/infrastructure/database/migrator.py](file:///Users/nkoneru/Downloads/AIApps/OrganicBattles/app/infrastructure/database/migrator.py) so that when an admin switches dialects via the Admin Dashboard, the `questions` table is transferred cleanly.

```python
# In migrator.py
TABLES_TO_MIGRATE = [
    "users",
    "verification_codes",
    "auth_sessions",
    "game_sessions",
    "curricula",
    "tracks",
    "questions",  # Added to migration manifest
]

def migrate_questions(sqlite_session, pg_session, batch_size=1000):
    from app.infrastructure.database.models import Question
    
    count = sqlite_session.query(Question).count()
    if count == 0:
        return 0
    
    logger.info("Migrating %d questions from SQLite to PostgreSQL...", count)
    pg_session.query(Question).delete()
    pg_session.commit()
    
    offset = 0
    while offset < count:
        rows = sqlite_session.query(Question).order_by(Question.id.asc()).offset(offset).limit(batch_size).all()
        if not rows:
            break
        mappings = [
            {col.name: getattr(r, col.name) for col in Question.__table__.columns if col.name != "id"}
            for r in rows
        ]
        pg_session.bulk_insert_mappings(Question, mappings)
        pg_session.commit()
        offset += len(rows)
        
    return count
```

---

## 7. Phase 5: Admin REST APIs for Question Browsing & Reordering

Create `app/api/v1/questions_admin.py` to allow teachers and administrators to search, edit, and reorder questions directly:

### 7.1 Paginated Question Search & Filtering
```python
@router.get("/api/admin/tracks/{track_id}/questions")
def get_track_questions(
    track_id: str,
    chapter: Optional[int] = None,
    boss_slug: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    db: DBSession = Depends(get_db)
):
    query = db.query(Question).filter(Question.track_id == track_id)
    if chapter:
        query = query.filter(Question.chapter == chapter)
    if boss_slug:
        query = query.filter(Question.boss_slug == boss_slug)
    if search:
        query = query.filter(Question.prompt.ilike(f"%{search}%"))

    total = query.count()
    items = (
        query.order_by(Question.chapter.asc(), Question.order_index.asc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
        "items": items
    }
```

### 7.2 Drag-and-Drop Reorder API
When a question's sequence is modified in the UI, this endpoint updates `order_index` deterministically:
```python
class ReorderRequest(BaseModel):
    question_ids: List[int]  # List of primary key IDs in new desired order

@router.post("/api/admin/tracks/{track_id}/chapters/{chapter}/reorder")
def reorder_questions(
    track_id: str,
    chapter: int,
    body: ReorderRequest,
    db: DBSession = Depends(get_db)
):
    for new_index, q_id in enumerate(body.question_ids):
        db.query(Question).filter(
            Question.id == q_id,
            Question.track_id == track_id,
            Question.chapter == chapter
        ).update({"order_index": new_index})
    
    db.commit()
    # Invalidate cached content bundle
    from app.domain.content.loader import invalidate_bundle_cache
    invalidate_bundle_cache(track_id)
    return {"status": "ok", "reordered_count": len(body.question_ids)}
```

---

## 8. Phase 6: Verification, Parity Tests & Rollback Strategy

### 8.1 Automated Parity Test
Create `tests/test_question_parity.py` to ensure that questions retrieved from PostgreSQL are **100% identical in content and sequential index** to the JSON files:

```python
import json
import pytest
from app.domain.content.loader import load_json_bundle, load_db_bundle
from app.infrastructure.database.engine import SessionLocal

def test_question_order_parity(root_dir):
    """Verify that DB question ordering exactly matches JSON array sequence."""
    with SessionLocal() as db:
        json_bundle = load_json_bundle(root_dir)
        db_bundle = load_db_bundle("default", db)
        
        assert len(json_bundle.questions) == len(db_bundle.questions)
        
        # Test each chapter's boss question bank order
        for (ch, boss), json_q_list in json_bundle.question_boss_bank.items():
            if isinstance(ch, int):
                db_q_list = db_bundle.question_boss_bank.get((ch, boss), [])
                assert len(json_q_list) == len(db_q_list), f"Count mismatch in Ch {ch}, Boss {boss}"
                
                for idx in range(len(json_q_list)):
                    json_prompt, json_opts, json_ans = json_q_list[idx]
                    db_prompt, db_opts, db_ans = db_q_list[idx]
                    assert json_prompt == db_prompt, f"Order mismatch at index {idx} in Ch {ch}, Boss {boss}"
                    assert json_ans == db_ans
```

### 8.2 Rollback Strategy
1. **Fallback Circuit Breaker**: If PostgreSQL is unreachable or the `questions` table is empty, `load_track_bundle()` automatically falls back to `load_json_bundle()` from disk without downtime.
2. **Read-Only Ingestion**: Ingesting into PostgreSQL does not alter or delete any original `.json` files in `data/tracks/`. The JSON files remain the immutable source of truth.
3. **Database Dialect Switch**: Admins can immediately switch the active dialect back to SQLite with one click in the Admin Dashboard System Tab (`/admin`).

---

## 9. Next Steps Summary

| Step | Action Item | Target File | Status |
| :--- | :--- | :--- | :--- |
| **1** | Define `Question` model & composite indexes | `app/infrastructure/database/models.py` | Ready to implement |
| **2** | Create fast batch ingestion script (28,400 questions) | `scripts/ingest_questions_to_postgres.py` | Ready to implement |
| **3** | Add `load_db_bundle()` with strict `order_index` | `app/domain/content/loader.py` | Ready to implement |
| **4** | Extend SQLite-to-PostgreSQL migrator | `app/infrastructure/database/migrator.py` | Ready to implement |
| **5** | Add Admin Question Search & Reorder APIs | `app/api/v1/questions_admin.py` | Ready to implement |
| **6** | Run sequential parity tests | `tests/test_question_parity.py` | Ready to implement |
