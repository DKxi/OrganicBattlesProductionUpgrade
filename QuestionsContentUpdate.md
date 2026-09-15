# Question & Answer Content Update Guide (`chapter_xx.json`)

**Date:** September 15, 2026  
**Topic:** Step-by-Step Instructions for Updating Questions, Answers, Tracks, Chapters, and Bosses Without Schema Changes  

---

## 1. Overview & Architectural Guarantee

The Organic Battles platform employs an **Atomic Content Release Architecture**. 
- **Zero Schema Changes**: Updating question text, options, correct answers, explanations, damage spells, boss health, or boss names **never** requires running database migrations or altering database schemas.
- **Zero Downtime**: When new or modified questions are ingested from `chapter_xx.json`, the system creates a draft release in `OB_content_releases`, inserts the questions into `OB_questions`, and atomically activates the release.
- **Cache Invalidation**: The cluster-wide distributed cache (`SharedTrackCacheManager`) automatically purges old track bundles, causing all Gunicorn workers to serve the updated questions instantly.
- **Player Session Safety**: Active player battles and account progression in `OB_users` and `OB_sessions` remain intact.

---

## 2. Structure of `chapter_xx.json`

Before ingesting, ensure your updated `chapter_xx.json` adheres to the required schema:

```json
{
  "schema_version": "2.0",
  "chapter": 1,
  "chapter_title": "A Review of General Chemistry: Electrons, Bonds, and Molecular Properties",
  "assigned_boss": "Orbital Ogre",
  "question_count": 50,
  "questions": [
    {
      "id": "ch01_q001",
      "chapter": 1,
      "chapter_title": "A Review of General Chemistry: Electrons, Bonds, and Molecular Properties",
      "boss": "Orbital Ogre",
      "topic": "pi bond",
      "difficulty": "easy",
      "question_type": "term_to_definition",
      "question": "Which statement most accurately describes “pi bond”?",
      "options": [
        { "label": "A", "text": "A measure of how strongly a bonded atom attracts shared electron density." },
        { "label": "B", "text": "A bond produced by sideways overlap of parallel p orbitals above and below the bonding axis." },
        { "label": "C", "text": "A bookkeeping charge assigned by comparing valence count with electrons assigned." },
        { "label": "D", "text": "A covalent bond in which electron density is shared unequally." }
      ],
      "correct_option": "B",
      "correct_answer": "A bond produced by sideways overlap of parallel p orbitals above and below the bonding axis.",
      "explanation": "A bond produced by sideways overlap of parallel p orbitals above and below the bonding axis.",
      "spells": [20, 30, 45],
      "health": [100],
      "images": ["orbital_ogre.png"]
    }
  ]
}
```

### Validation Rules Enforced During Ingestion:
1. **Options**: Minimum of 2 choices. Each must have unique labels (`A`, `B`, `C`, `D`).
2. **Correct Option & Answer**: `correct_option` must match the label of one of the options, and `correct_answer` must match that option's text.
3. **Spells**: Array of integers representing damage tiers for player spells (e.g., `[20, 30, 45]`).
4. **Health**: Positive integers representing boss HP (e.g., `[100]`).
5. **Boss & Images**: The boss name in `"boss"` or `"assigned_boss"` automatically registers in `OB_bosses`, and `"images"` links to the boss asset.

---

## 3. Step-by-Step Instructions to Update Content

### Step 1: Save Your Updated `chapter_xx.json`
Save the updated file matching the track's chapter naming convention (e.g., `chapter_01.json`, `chapter_02.json`, ..., `chapter_27.json`).

### Step 2: Place the File in the Target Content Source

Depending on whether your deployment uses local disk storage or remote S3 / Supabase Object Storage:

#### Path A: Local Disk / Server Deployments
Place the updated file into the track's data directory:
```bash
# Default track:
cp chapter_01.json /app/data/tracks/default/chapter_01.json

# Advanced track:
cp chapter_01.json /app/data/tracks/advanced/chapter_01.json
```

#### Path B: S3 / Supabase Object Storage Deployments
Upload the updated JSON file to your designated S3 bucket and track prefix:
```bash
# Example using AWS CLI or Supabase S3 API:
aws s3 cp chapter_01.json s3://DefaultBosses/tracks/default/chapter_01.json
```

---

### Step 3: Trigger Ingestion to Update Database Tables

You can trigger ingestion either through the **Admin Console** or via the **CLI Ingestion Script**.

#### Method 1: Using the Web Admin Console (No Terminal Needed)
1. Navigate to the Admin Portal in your browser: `http://localhost:8000/admin` (or click the **ADMIN** button on the bottom bar).
2. Authenticate using admin credentials (`ADMIN_USERNAME` / `ADMIN_PASSWORD`).
3. Scroll to the **DATA LOADS // BATCH INGESTION** card.
4. In the **Target Track** dropdown, select the track you updated (e.g., `Default Track` or `All Tracks`).
5. Set the **Batch Size** (default `1000` is recommended).
6. Click **START BATCH INGESTION**.
7. The status prompt will display:
   ```text
   Parsing and ingesting questions into draft release…
   Successfully processed X questions across 1 track(s)!
   ```
8. The database is now updated!

#### Method 2: Using the Command-Line Script
If you prefer running from a server terminal, SSH session, or deployment pipeline:

```bash
# Ingest from local filesystem for a specific track:
uv run python scripts/ingest_questions_to_postgres.py --track default --source local

# Ingest from S3 / Supabase storage:
uv run python scripts/ingest_questions_to_postgres.py --track default --source s3

# Ingest all tracks with auto-detection:
uv run python scripts/ingest_questions_to_postgres.py --source auto
```

---

### Step 4: Verification & Cache Warming

1. **Verify Release Version**:
   - In the Admin Console under the **Releases** tab, check the latest release for your track. You will see the new release marked as `published`, and the previous version archived.
2. **Warm Cache (Optional)**:
   - Click **WARM CACHE** on the Admin Console (or run `uv run python scripts/warm_cache.py`). This preloads the updated question bundles into worker memory for zero cold-start latency.
3. **Verify Question Content**:
   - In the Admin Console under **Questions & Content**, search for a question from the updated chapter to verify that the prompt, options, and answers reflect the new JSON.

---

## 4. What Happens to the Database Tables (Under the Hood)

During the update, the following database tables are updated in a single transaction:

| Table Name | Changes Applied During Update |
|---|---|
| **`OB_content_releases`** | Creates a new draft release version. Once all questions pass validation, the status is flipped to `published`. |
| **`OB_questions`** | Questions are inserted with the new `release_id` and strict `order_index`. Questions from previous releases remain archived for rollback capability. |
| **`OB_tracks`** | `questions` total count and `chapters` count are synchronized. |
| **`OB_bosses`** | Populates any new boss names found in the `chapter_xx.json` into the bosses directory. |
| **`OB_boss_question_assignments`**| Maps boss relationships and chapter numbers for combat arena rendering. |
| **`OB_audit_log`** | Records an `INGEST_QUESTIONS` entry with timestamp, admin identity, and question count. |

---

## 5. Current Admin Console Capabilities vs. Missing Features

### What the Admin Console CAN Do Today:
- **Batch Re-Ingestion Trigger**: Has a UI form to trigger ingestion from the filesystem/S3 (`POST /api/v1/admin/questions/ingest`).
- **Individual Question Editing**: Search any question and edit prompt text, options, answers, explanations, spells, and health directly via `PUT /api/v1/admin/questions/{id}`.
- **Question Reordering**: Move questions before/after each other or submit a reordered permutation (`POST /api/v1/admin/tracks/{track_id}/chapters/{chapter}/reorder`).
- **One-Click Rollback**: Instantly revert the live track to a previous release version (`POST /api/v1/admin/tracks/{track_id}/releases/{version}/rollback`).

---

### Missing Features in the Admin Console (Feature Gaps & Potential Enhancements):

If you want to update questions **exclusively through the browser without touching disk files or S3**, the following capabilities are currently not present and would be candidates for future implementation:

1. **Direct Drag-and-Drop Browser File Upload (`chapter_xx.json`)**:
   - *Current limitation*: The admin UI only triggers ingestion from existing files already on the server disk or S3 bucket.
   - *Required enhancement*: Add a file upload input (`<input type="file" accept=".json">`) in the admin portal that accepts a `chapter_xx.json` file from the administrator's desktop, uploads it via a multipart form endpoint (`POST /api/v1/admin/content/upload`), and triggers ingestion in memory.
2. **Single-Chapter Ingestion Scope**:
   - *Current limitation*: Ingestion currently re-processes all chapters in the track folder to publish an atomic full-track release.
   - *Required enhancement*: Add a `chapter` parameter to `IngestQuestionsRequest` (`POST /api/v1/admin/questions/ingest?chapter=5`) to allow updating a single chapter while copying the remaining chapters forward into the new release.
3. **In-Browser JSON Syntax & Schema Validator / Diff Preview**:
   - *Current limitation*: If a JSON file has syntax errors or missing required fields, ingestion fails with an error toast after processing.
   - *Required enhancement*: Provide an interactive preview modal showing:
     - Questions added / modified / removed.
     - Validation warnings (e.g. invalid image filename or missing distractor).
     - "Confirm & Publish Release" button.
4. **Boss Image Asset Upload in Admin Console**:
   - *Current limitation*: If a new boss is specified in `chapter_xx.json`, its PNG image must be uploaded to the S3 bucket or `/static/assets/bosses/` manually.
   - *Required enhancement*: Allow uploading boss portrait PNGs directly through the Admin Portal Storage tab.
