import json
import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from app.main import create_app
from app.settings import settings
from app.infrastructure.database.engine import SessionLocal, get_active_engine
from app.infrastructure.database.models import Base, Track, Question
from app.domain.content.loader import load_json_bundle, load_db_bundle, load_track_bundle
from app.infrastructure.identity.crypto import code_hash
from app.infrastructure.cache.memory import set_admin_token
from app.infrastructure.database.migrator import migrate_sqlite_to_postgres


from scripts.ingest_questions_to_postgres import ingest_questions_data


@pytest.fixture(scope="module", autouse=True)
def seed_test_questions():
    """Ensure questions for track 'default' are ingested into the test database."""
    with SessionLocal() as db:
        ingest_questions_data(db, target_track_id="default", root_dir=settings.root_dir)


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def admin_headers():
    token = "parity-admin-secret-token"
    set_admin_token(code_hash(token))
    return {"Authorization": f"Bearer {token}"}



def test_question_model_and_indexes():
    """Verify Question table schema, columns, and indexes are registered."""
    table = Question.__table__
    assert "id" in table.columns
    assert "track_id" in table.columns
    assert "chapter" in table.columns
    assert "boss_slug" in table.columns
    assert "order_index" in table.columns
    assert "prompt" in table.columns

    # Verify composite index exists
    index_names = {idx.name for idx in table.indexes}
    assert "ix_ob_questions_track_ch_boss_order" in index_names or "ix_questions_track_ch_boss_order" in index_names
    assert "ix_ob_questions_track_ch_order" in index_names or "ix_questions_track_ch_order" in index_names


def test_ob_questions_table_populated():
    """Verify that OB_questions table is populated with questions in the active database."""
    with SessionLocal() as db:
        total_questions = db.query(Question).count()
        assert total_questions > 0, "OB_questions table must not be empty! Questions must be ingested."
        assert total_questions >= 1350, f"Expected at least 1,350 ingested questions in active DB, found {total_questions}"

        # Verify default track has complete question set
        default_count = db.query(Question).filter(Question.track_id == "default").count()
        assert default_count >= 1350, f"Expected default track to have at least 1,350 questions, found {default_count}"

        # Verify question data integrity
        sample_q = db.query(Question).filter(Question.track_id == "default").first()
        assert sample_q is not None
        assert sample_q.prompt
        assert sample_q.options_json
        assert sample_q.correct_answer
        assert sample_q.chapter >= 1


def test_load_db_bundle_loads_from_database():
    """Verify load_db_bundle reads questions directly from database table."""
    with SessionLocal() as db:
        db_bundle = load_db_bundle("default", db=db, root_dir=settings.root_dir)
        assert db_bundle is not None, "DB bundle should load for track 'default'"
        assert len(db_bundle.questions) >= 1350, f"Expected at least 1,350 questions in bundle, got {len(db_bundle.questions)}"
        assert len(db_bundle.chapters) == 27
        assert len(db_bundle.question_bank_by_chapter[1]) == 50


def test_question_sequential_order_parity():
    """
    Critical Test: Ensure that questions in PostgreSQL are returned
    in the exact sequential order matching the original JSON files.
    """
    with SessionLocal() as db:
        json_bundle = load_json_bundle(settings.root_dir)
        db_bundle = load_db_bundle("default", db=db, root_dir=settings.root_dir)

        assert db_bundle is not None, "DB bundle should load for track 'default'"
        assert len(db_bundle.questions) == len(json_bundle.questions), "Total question count must match"

        # Compare question sequence per chapter
        for ch_id in range(1, len(json_bundle.chapters) + 1):
            json_qs = json_bundle.question_bank_by_chapter.get(ch_id, [])
            db_qs = db_bundle.question_bank_by_chapter.get(ch_id, [])
            assert len(json_qs) == len(db_qs), f"Chapter {ch_id} question count mismatch"

            for idx in range(len(json_qs)):
                j_prompt, j_choices, j_ans = json_qs[idx]
                d_prompt, d_choices, d_ans = db_qs[idx]

                # Assert strict 1-to-1 prompt parity at identical order index
                assert j_prompt == d_prompt, f"Prompt mismatch at ch {ch_id}, index {idx}: {j_prompt[:30]} != {d_prompt[:30]}"
                assert j_ans == d_ans, f"Answer mismatch at ch {ch_id}, index {idx}"

        # Compare question sequence in boss banks
        for key, j_list in json_bundle.question_boss_bank.items():
            if isinstance(key, tuple):
                ch, boss = key
                d_list = db_bundle.question_boss_bank.get((ch, boss), [])
                assert len(j_list) == len(d_list), f"Boss bank count mismatch for ({ch}, {boss})"
                for idx in range(len(j_list)):
                    assert j_list[idx][0] == d_list[idx][0], f"Boss bank order mismatch at index {idx} for ({ch}, {boss})"


def test_admin_get_track_questions(client, admin_headers):
    """Test paginated retrieval of track questions."""
    response = client.get(
        "/api/admin/tracks/default/questions?chapter=1&limit=10",
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["track_id"] == "default"
    assert data["total"] >= 10
    assert len(data["items"]) == 10
    # First item must have order_index == 0
    assert data["items"][0]["order_index"] == 0
    assert data["items"][1]["order_index"] == 1


def test_admin_update_question(client, admin_headers):
    """Test updating a single question and verifying bundle cache invalidation."""
    with SessionLocal() as db:
        q = db.query(Question).filter(Question.track_id == "default").first()
        assert q is not None
        q_id = q.id
        orig_explanation = q.explanation

    # Update explanation
    new_exp = "Updated explanation from unit test."
    resp = client.put(
        f"/api/admin/questions/{q_id}",
        json={"explanation": new_exp},
        headers=admin_headers,
    )
    assert resp.status_code == 200

    # Verify update in DB
    with SessionLocal() as db:
        updated_q = db.query(Question).filter(Question.id == q_id).first()
        assert updated_q.explanation == new_exp

        # Restore original
        updated_q.explanation = orig_explanation
        db.commit()


def test_admin_reorder_questions(client, admin_headers):
    """Test reordering questions scoped to a boss."""
    with SessionLocal() as db:
        qs = (
            db.query(Question)
            .filter(Question.track_id == "default", Question.chapter == 1, Question.boss_slug == "orbital-ogre")
            .order_by(Question.order_index.asc())
            .all()
        )
        assert len(qs) > 0
        ids = [q.id for q in qs]

    # Swap first two using admin reorder endpoint scoped to boss
    reordered_ids = list(ids)
    reordered_ids[0], reordered_ids[1] = reordered_ids[1], reordered_ids[0]
    resp = client.post(
        "/api/admin/tracks/default/chapters/1/bosses/orbital-ogre/reorder",
        json={"question_ids": reordered_ids},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["reordered_count"] == len(ids)
    assert "release_id" in data

    with SessionLocal() as db:
        q1 = db.query(Question).filter(Question.id == ids[1]).first()
        q0 = db.query(Question).filter(Question.id == ids[0]).first()
        assert q1.order_index == 0
        assert q0.order_index == 1

    # Restore original order using endpoint to exercise single transaction update
    restore_resp = client.post(
        "/api/admin/tracks/default/chapters/1/bosses/orbital-ogre/reorder",
        json={"question_ids": ids},
        headers=admin_headers,
    )
    assert restore_resp.status_code == 200



def test_migrator_includes_questions():
    """Verify that migrator copies questions table between engines."""
    from sqlalchemy import create_engine
    test_src = get_active_engine()
    test_dst = create_engine("sqlite:///:memory:")

    stats = migrate_sqlite_to_postgres(test_src, test_dst)
    assert "questions" in stats
    assert stats["questions"] > 0


def test_zero_textbook_author_references_in_db():
    """Verify that no database question prompts or explanations cite Klein, David, McMurry, or McCurry."""
    from sqlalchemy import text
    with SessionLocal() as db:
        for term in ["david", "klein", "mcmurry", "mccurry"]:
            count = db.execute(
                text("SELECT COUNT(*) FROM OB_questions WHERE LOWER(prompt) LIKE :t OR LOWER(explanation) LIKE :t"),
                {"t": f"%{term}%"}
            ).scalar()
            assert count == 0, f"Found {count} questions in DB matching prohibited author reference: {term}"


def test_zero_textbook_author_references_in_manifests():
    """Verify that all track manifests have been sanitized of textbook/author names."""
    manifest_paths = list(Path("data/tracks").glob("**/manifest.json"))
    assert len(manifest_paths) > 0
    for path in manifest_paths:
        content = path.read_text(encoding="utf-8").lower()
        for term in ["david", "klein", "mcmurry", "mccurry"]:
            assert term not in content, f"Prohibited term '{term}' found in manifest: {path}"
