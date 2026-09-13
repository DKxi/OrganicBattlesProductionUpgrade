import pytest
from starlette.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.settings import settings
from app.infrastructure.database.engine import SessionLocal, build_engine
from app.infrastructure.database.models import Base, Curriculum, Track
from app.infrastructure.database.tracks_repo import TracksRepository
from app.infrastructure.database.migrator import migrate_sqlite_to_postgres
from tests.test_database_connection import get_database_env, resolve_postgres_url


@pytest.fixture
def admin_client():
    client = TestClient(app)
    login_res = client.post(
        "/api/admin/login",
        json={"username": settings.admin_username, "password": settings.admin_password},
    )
    assert login_res.status_code == 200
    token = login_res.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_tracks_and_curricula_seeded_in_database():
    """Verify that curricula and tracks are seeded into the active database."""
    with SessionLocal() as db:
        curricula = db.query(Curriculum).all()
        tracks = db.query(Track).all()

        assert len(curricula) >= 2
        assert len(tracks) == 20

        # Verify specific curriculum
        advanced = db.query(Curriculum).filter_by(id="advanced").first()
        assert advanced is not None
        assert advanced.name == "Advanced Mechanistic Mastery"
        assert advanced.code == "A"
        assert len(advanced.tracks) == 12

        # Verify specific track
        default_track = db.query(Track).filter_by(id="default").first()
        assert default_track is not None
        assert default_track.title == "Default Track"
        assert default_track.curriculum_id == "foundational"
        assert default_track.data_folder == "data/tracks/default"
        assert "DefaultBosses" in default_track.boss_folder or default_track.boss_folder == "data/tracks/default/bosses"


def test_tracks_repository_operations():
    """Verify TracksRepository methods for querying and updating tracks."""
    with SessionLocal() as db:
        repo = TracksRepository(db)

        # 1. get_tracks_config format
        cfg = repo.get_tracks_config()
        assert "curricula" in cfg
        assert "tracks" in cfg
        assert len(cfg["curricula"]) >= 2
        assert len(cfg["tracks"]) == 20

        # 2. get_track
        trk = repo.get_track("adv-vocab")
        assert trk is not None
        assert trk.id == "adv-vocab"
        assert trk.accent == "violet"

        # 3. get_track_dict
        d = repo.get_track_dict("adv-vocab")
        assert d["id"] == "adv-vocab"
        assert d["curriculum"] == "advanced"
        assert "VocabularyConceptsData" in d["data_folder"]


def test_game_tracks_endpoint_reads_from_database():
    """Verify that GET /api/game/tracks returns curricula and tracks from the database."""
    client = TestClient(app)
    res = client.get("/api/game/tracks")
    assert res.status_code == 200
    data = res.json()
    assert "curricula" in data
    assert "tracks" in data
    assert len(data["tracks"]) == 20
    track_ids = {t["id"] for t in data["tracks"]}
    assert "default" in track_ids
    assert "adv-vocab" in track_ids
    assert "found-nomenclature" in track_ids


def test_admin_tracks_and_curricula_apis(admin_client):
    """Verify admin endpoints for tracks and curricula."""
    # 1. GET /api/admin/tracks
    tracks_res = admin_client.get("/api/admin/tracks")
    assert tracks_res.status_code == 200
    tracks = tracks_res.json()["tracks"]
    assert len(tracks) == 20

    # 2. GET /api/admin/curricula
    curr_res = admin_client.get("/api/admin/curricula")
    assert curr_res.status_code == 200
    curricula = curr_res.json()["curricula"]
    assert len(curricula) >= 2

    # 3. PUT /api/admin/tracks/{track_id}
    orig_track = next(t for t in tracks if t["id"] == "adv-vocab")
    orig_detail = orig_track["detail"]

    try:
        update_res = admin_client.put(
            "/api/admin/tracks/adv-vocab",
            json={"detail": "Updated concepts and nomenclature"},
        )
        assert update_res.status_code == 200
        data = update_res.json()
        assert data["status"] == "ok"
        assert data["track"]["detail"] == "Updated concepts and nomenclature"

        # Verify database reflection
        with SessionLocal() as db:
            t = db.query(Track).filter_by(id="adv-vocab").first()
            assert t.detail == "Updated concepts and nomenclature"
    finally:
        # Restore detail
        admin_client.put(
            "/api/admin/tracks/adv-vocab",
            json={"detail": orig_detail},
        )


def test_migration_engine_copies_tracks_and_curricula(tmp_path):
    """Verify that migrate_sqlite_to_postgres copies curricula and tracks between engines."""
    src_path = tmp_path / "src_tracks.sqlite3"
    dst_path = tmp_path / "dst_tracks.sqlite3"

    src_engine = build_engine(f"sqlite:///{src_path}")
    dst_engine = build_engine(f"sqlite:///{dst_path}")

    # Initialize source and seed tracks
    Base.metadata.create_all(bind=src_engine)
    with Session(src_engine) as src:
        repo = TracksRepository(src)
        repo.seed_if_empty(settings.root_dir / "data" / "tracks_config.json")

    # Migrate to destination
    stats = migrate_sqlite_to_postgres(src_engine, dst_engine)
    assert stats["curricula"] >= 2
    assert stats["tracks"] == 20

    # Verify destination database
    with Session(dst_engine) as dst:
        assert dst.query(Curriculum).count() >= 2
        assert dst.query(Track).count() == 20
        default_t = dst.query(Track).filter_by(id="default").first()
        assert default_t is not None
        assert default_t.curriculum_id == "foundational"

    src_engine.dispose()
    dst_engine.dispose()


def test_tracks_postgresql_live_seeding_and_query():
    """Verify that PostgreSQL in Supabase has curricula and tracks seeded and queryable."""
    values = get_database_env()
    db_url = values.get("DATABASE_URL")
    if not db_url or "postgresql" not in db_url.lower():
        pytest.skip("PostgreSQL not configured in env")

    resolved_url = resolve_postgres_url(db_url)
    pg_engine = build_engine(resolved_url)
    from app.infrastructure.database.engine import _migrate_legacy_table_names
    # Ensure schema on PostgreSQL
    _migrate_legacy_table_names(pg_engine)
    Base.metadata.create_all(bind=pg_engine)

    with Session(pg_engine) as db:
        repo = TracksRepository(db)
        repo.seed_if_empty(settings.root_dir / "data" / "tracks_config.json")

        cfg = repo.get_tracks_config()
        assert len(cfg["curricula"]) >= 2
        assert len(cfg["tracks"]) == 20

        # Verify OB_questions table is populated in PostgreSQL
        from app.infrastructure.database.models import Question
        q_count = db.query(Question).count()
        assert q_count >= 27000, f"Expected at least 27,000 questions in live PostgreSQL, got {q_count}"

    pg_engine.dispose()


def test_ob_questions_table_populated_in_postgres():
    """Verify that live PostgreSQL database has OB_questions populated across all 20 tracks."""
    values = get_database_env()
    db_url = values.get("DATABASE_URL")
    if not db_url or "postgresql" not in db_url.lower():
        pytest.skip("PostgreSQL not configured in env")

    resolved_url = resolve_postgres_url(db_url)
    pg_engine = build_engine(resolved_url)
    with Session(pg_engine) as db:
        from app.infrastructure.database.models import Question, Track
        total = db.query(Question).count()
        assert total >= 27000, f"Expected at least 27,000 questions in PostgreSQL, found {total}"

        tracks = db.query(Track).all()
        assert len(tracks) == 20
        for trk in tracks:
            trk_count = db.query(Question).filter(Question.track_id == trk.id).count()
            assert trk_count >= 1350, f"Track {trk.id} has {trk_count} questions in PostgreSQL, expected >= 1350"

    pg_engine.dispose()
