import json
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.settings import settings
import app.infrastructure.database.engine as db_engine
from app.infrastructure.database.models import User, Track
from app.infrastructure.database.engine import SessionLocal



@pytest.fixture
def admin_client():
    client = TestClient(app)
    login_res = client.post(
        "/api/v1/admin/login",
        json={"username": settings.admin_username, "password": settings.admin_password},
    )
    assert login_res.status_code == 200
    token = login_res.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_admin_system_endpoints_require_auth():
    """Verify that unauthenticated requests to system endpoints are rejected with 401."""
    client = TestClient(app)
    assert client.get("/api/v1/admin/system/config").status_code == 401
    assert client.post("/api/v1/admin/system/database", json={"dialect": "sqlite"}).status_code == 401
    assert client.post("/api/v1/admin/system/folders", json={"data_folder": "dummy"}).status_code == 401


def test_admin_get_system_config(admin_client):
    """Verify that GET /admin/system/config returns active database and tracks list."""
    res = admin_client.get("/api/v1/admin/system/config")
    assert res.status_code == 200
    data = res.json()
    assert "active_database" in data
    assert "dialect" in data["active_database"]
    assert "url" in data["active_database"]
    assert "tracks" in data
    assert isinstance(data["tracks"], list)
    assert len(data["tracks"]) >= 2


def test_admin_switch_database_with_migration(admin_client, tmp_path):
    """Verify POST /admin/system/database live-switches database and migrates records."""
    initial_url = db_engine.current_db_url

    # Ensure a user exists in the current database
    with SessionLocal() as session:
        if not session.query(User).filter_by(id="sys_test_u1").first():
            session.add(User(
                id="sys_test_u1",
                username="sys_test_player",
                email="systest@example.com",
                password_hash="pwd123",
                verified=1,
            ))
            session.commit()

    target_db = tmp_path / "admin_switched.sqlite3"
    target_url = f"sqlite:///{target_db}"

    try:
        # Switch to target_url with migrate_data=True
        switch_res = admin_client.post(
            "/api/v1/admin/system/database",
            json={
                "dialect": "sqlite",
                "connection_url": target_url,
                "migrate_data": True,
            },
        )
        assert switch_res.status_code == 200
        data = switch_res.json()
        assert data["status"] == "ok"
        assert data["dialect"] == "sqlite"
        assert "migration" in data
        assert data["migration"]["users"] >= 1
        assert db_engine.current_db_url == target_url

        # Verify user was migrated to the new database
        with SessionLocal() as session:
            migrated_u = session.query(User).filter_by(id="sys_test_u1").first()
            assert migrated_u is not None
            assert migrated_u.email == "systest@example.com"

    finally:
        # Restore initial database
        admin_client.post(
            "/api/v1/admin/system/database",
            json={
                "dialect": "sqlite",
                "connection_url": initial_url,
                "migrate_data": False,
            },
        )
        assert db_engine.current_db_url == initial_url


def test_admin_switch_folders(admin_client):
    """Verify POST /admin/system/folders updates track data_folder and boss_folder."""
    config_path = settings.root_dir / "data" / "tracks_config.json"
    backup_text = config_path.read_text(encoding="utf-8")

    try:
        # Update a specific track
        update_res = admin_client.post(
            "/api/v1/admin/system/folders",
            json={
                "track_id": "adv-vocab",
                "data_folder": "data/tracks/advanced/CustomVocabFolder",
                "boss_folder": "data/tracks/advanced/CustomBossFolder",
            },
        )
        assert update_res.status_code == 200
        assert update_res.json()["status"] == "ok"

        # Verify tracks_config.json was modified
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        vocab_track = next(t for t in cfg["tracks"] if t["id"] == "adv-vocab")
        assert vocab_track["data_folder"] == "data/tracks/advanced/CustomVocabFolder"
        assert vocab_track["boss_folder"] == "data/tracks/advanced/CustomBossFolder"

        # Attempt to update non-existent track (should return 404)
        bad_res = admin_client.post(
            "/api/v1/admin/system/folders",
            json={
                "track_id": "non-existent-track-xyz",
                "data_folder": "some/folder",
            },
        )
        assert bad_res.status_code == 404

    finally:
        # Restore tracks_config.json and database
        config_path.write_text(backup_text, encoding="utf-8")
        with SessionLocal() as db:
            t = db.query(Track).filter_by(id="adv-vocab").first()
            if t:
                t.data_folder = "data/tracks/advanced/VocabularyConceptsData"
                t.boss_folder = "data/tracks/advanced/bosses"
                db.commit()
        from app.api.deps import TRACK_BUNDLES
        TRACK_BUNDLES.clear()



def test_admin_dashboard_template_contains_system_storage_tab():
    """Verify that index.html contains the System & Storage admin tab and configuration forms."""
    client = TestClient(app)
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    assert 'id="admin-tab-system"' in html
    assert 'id="admin-system-tab-content"' in html
    assert 'id="admin-db-switch-form"' in html
    assert 'id="admin-folder-switch-form"' in html
    assert 'id="admin-db-uri-input"' in html
    assert 'id="admin-folder-track-select"' in html


