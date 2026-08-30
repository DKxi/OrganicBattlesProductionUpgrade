import uuid
import pytest
from fastapi.testclient import TestClient
from app import app, code_hash

client = TestClient(app)

@pytest.fixture
def client_instance():
    return TestClient(app)

@pytest.fixture
def auth_headers(client_instance, monkeypatch):
    username = f"test_{uuid.uuid4().hex[:12]}"
    email = f"{username}@example.com"
    password = "password123"

    codes = []
    def mock_send(email_addr, uname, code):
        codes.append(code)

    import app as app_mod
    monkeypatch.setattr(app_mod, "send_verification_email", mock_send)

    # 1. Signup
    signup_res = client_instance.post("/api/auth/signup", json={
        "email": email,
        "username": username,
        "password": password
    })
    assert signup_res.status_code == 200
    
    assert len(codes) > 0, "No verification code was sent"
    code = codes[0]

    # 2. Verify
    verify_res = client_instance.post("/api/auth/verify", json={"code": code})
    assert verify_res.status_code == 200
    token = verify_res.json()["token"]
    
    # Return auth headers dict and also ensure cookie is set (which TestClient does)
    return {"Authorization": f"Bearer {token}"}

def start(client_instance, auth_headers):
    return client_instance.post('/api/game/new', headers=auth_headers).json()

def avatar():
    return {'body':'arc','skin':'warm','hair':'nebula','outfit':'coat','accessory':'goggles','aura':'teal'}

def find_correct_answer(prompt_text):
    import app as app_mod
    sources = []
    if app_mod.APP_DATA.get("questions"):
        sources.append(app_mod.APP_DATA["questions"])
    if app_mod.JSON_DATA.get("questions"):
        sources.append(app_mod.JSON_DATA["questions"])
    sources.extend(list(app_mod.QUESTION_BANK_BY_CHAPTER.values()))
    sources.extend(list(app_mod.QUESTION_BANK_BY_BOSS.values()))
    for bank in sources:
        for q_prompt, _choices, correct in bank:
            if prompt_text == q_prompt or prompt_text.startswith(q_prompt) or q_prompt.startswith(prompt_text):
                return correct
    raise ValueError(f"Could not find answer for question: {prompt_text}")

def test_new_game_defaults(client_instance, auth_headers):
    import app as app_mod
    s = start(client_instance, auth_headers)
    assert s['player']['hp'] == 150
    expected_boss = app_mod.CHAPTERS[0]['bosses'][0][1]
    assert s['boss']['name'] == expected_boss

def test_avatar_selection_and_update(client_instance, auth_headers):
    s = start(client_instance, auth_headers); sid = s['session_id']
    assert client_instance.post('/api/avatar/finalize', params={'session_id':sid}, json=avatar(), headers=auth_headers).status_code == 200
    res = client_instance.post('/api/avatar/finalize', params={'session_id':sid}, json={**avatar(), 'character': 'player-catalysis-adept'}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()['avatar']['character'] == 'player-catalysis-adept'


def test_avatar_v3_configuration_persists(client_instance, auth_headers):
    s = start(client_instance, auth_headers); sid = s['session_id']
    config = {'baseCharacter': 'organic-apprentice', 'skinTone': 'medium-deep', 'hair': {'style': 'spiky', 'color': 'dark-purple'}, 'glasses': 'thin-silver', 'coat': 'blue-trim', 'flask': 'blue-catalyst'}
    payload = {**avatar(), 'config': config}
    response = client_instance.post('/api/avatar/finalize', params={'session_id': sid}, json=payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()['avatar']['config'] == config

def test_correct_answer_deals_damage(client_instance, auth_headers):
    s = start(client_instance, auth_headers); sid = s['session_id']
    client_instance.post('/api/avatar/finalize', params={'session_id':sid}, json=avatar(), headers=auth_headers)
    q = client_instance.post('/api/battle/select-spell', params={'session_id':sid}, json={'spell_id':'fire-spark'}, headers=auth_headers).json()
    answer = find_correct_answer(q['question']['prompt'])
    result = client_instance.post('/api/battle/answer', params={'session_id':sid}, json={'answer':answer}, headers=auth_headers).json()
    assert result['correct'] is True
    assert result['damage'] > 0

def test_favicon_endpoint_exists():
    # Public endpoint, doesn't need auth
    response = client.get('/favicon.ico')
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('image/')

def test_page_uses_versioned_static_assets():
    # Public endpoint, doesn't need auth
    html = client.get('/').text
    assert '/static/css/game.css?v=' in html
    assert '/static/js/main.js?v=' in html

# --- Avatar-only regression tests ---

def test_avatar_with_missing_config_still_works_like_a_legacy_save(client_instance, auth_headers):
    s = start(client_instance, auth_headers); sid = s['session_id']
    response = client_instance.post('/api/avatar/finalize', params={'session_id': sid}, json=avatar(), headers=auth_headers)
    assert response.status_code == 200
    assert response.json()['avatar']['config'] == {}
    spell = client_instance.post('/api/battle/select-spell', params={'session_id': sid}, json={'spell_id': 'fire-spark'}, headers=auth_headers)
    assert spell.status_code == 200

def test_avatar_customization_does_not_change_damage_or_cooldowns(client_instance, auth_headers):
    outcomes = []
    # Create different sessions/clients to avoid conflict on same session
    for config in ({}, {'skinTone': 'deep', 'hair': {'style': 'curly', 'color': 'blue-black'}, 'coat': 'reaction-coat', 'accessory': 'wrist-device'}):
        # We need a fresh user session for each iteration to test finalize separately
        username = f"test_{uuid.uuid4().hex[:12]}"
        email = f"{username}@example.com"
        password = "password123"
        codes = []
        import app as app_mod
        from unittest.mock import patch
        
        with patch.object(app_mod, "send_verification_email", side_effect=lambda email, username, code: codes.append(code)):
            client_instance.post("/api/auth/signup", json={"email": email, "username": username, "password": password})
            code = codes[0]
            verify_res = client_instance.post("/api/auth/verify", json={"code": code})
            token = verify_res.json()["token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            s = start(client_instance, headers)
            sid = s['session_id']
            client_instance.post('/api/avatar/finalize', params={'session_id': sid}, json={**avatar(), 'config': config}, headers=headers)
            q = client_instance.post('/api/battle/select-spell', params={'session_id': sid}, json={'spell_id': 'fire-spark'}, headers=headers).json()
            answer = find_correct_answer(q['question']['prompt'])
            result = client_instance.post('/api/battle/answer', params={'session_id': sid}, json={'answer': answer}, headers=headers).json()
            outcomes.append((result['damage'], result['correct'], round(result['cooldowns']['fire-spark'])))
            
    assert outcomes[0] == outcomes[1]

def test_avatar_config_persists_unchanged_across_subsequent_state_reads(client_instance, auth_headers):
    s = start(client_instance, auth_headers); sid = s['session_id']
    config = {'skinTone': 'light', 'hair': {'style': 'medium-layered', 'color': 'brown'}, 'flask': 'orange-energy', 'accentColor': 'crimson'}
    client_instance.post('/api/avatar/finalize', params={'session_id': sid}, json={**avatar(), 'config': config}, headers=auth_headers)
    client_instance.post('/api/battle/select-spell', params={'session_id': sid}, json={'spell_id': 'fire-spark'}, headers=auth_headers)
    state = client_instance.get('/api/game/state', params={'session_id': sid}, headers=auth_headers).json()
    assert state['avatar']['config'] == config

def test_avatar_endpoints_do_not_expose_boss_or_progression_regressions(client_instance, auth_headers):
    s = start(client_instance, auth_headers); sid = s['session_id']
    before = client_instance.get('/api/progression', params={'session_id': sid}, headers=auth_headers).json()
    client_instance.post('/api/avatar/finalize', params={'session_id': sid}, json={**avatar(), 'config': {'coat': 'advanced-chemist'}}, headers=auth_headers)
    after = client_instance.get('/api/progression', params={'session_id': sid}, headers=auth_headers).json()
    assert before['boss']['hp'] == after['boss']['hp']
    assert before['chapter'] == after['chapter']
    assert before['completed'] == after['completed'] == []


def test_concurrency_optimistic_locking(client_instance, auth_headers):
    from database import SessionLocal
    from session_repository import get_session_by_id, save_session
    from fastapi import HTTPException

    s = start(client_instance, auth_headers)
    sid = s['session_id']

    db = SessionLocal()
    try:
        # Load the session context twice (obtaining the same base version)
        session_a = get_session_by_id(db, sid)
        session_b = get_session_by_id(db, sid)

        # Verify they have the same version
        assert session_a._db_version == session_b._db_version

        # Modify and save session_a
        session_a.player_hp = 140
        save_session(db, session_a)

        # Now try to save session_b, which holds the stale version.
        # This must raise HTTPException with status code 409!
        session_b.player_hp = 130
        with pytest.raises(HTTPException) as exc_info:
            save_session(db, session_b)
        assert exc_info.value.status_code == 409
        assert "Conflict" in exc_info.value.detail
    finally:
        db.close()


# --- Additional Security, Validation and Gameplay Tests ---

def test_signup_validation_errors(client_instance):
    # Invalid email
    res = client_instance.post("/api/auth/signup", json={"email": "invalid-email", "username": "testuser", "password": "password123"})
    assert res.status_code == 422
    assert "email address" in res.json()["detail"]

    # Password too short
    res = client_instance.post("/api/auth/signup", json={"email": "test@example.com", "username": "testuser", "password": "123"})
    assert res.status_code == 422
    assert "at least 8 characters" in res.json()["detail"]

def test_duplicate_user_registration(client_instance, auth_headers):
    username = f"dup_{uuid.uuid4().hex[:12]}"
    email = f"{username}@example.com"
    
    res = client_instance.post("/api/auth/signup", json={"email": email, "username": username, "password": "password123"})
    assert res.status_code == 200

    # Duplicate username
    res = client_instance.post("/api/auth/signup", json={"email": f"other@{username}.com", "username": username, "password": "password123"})
    assert res.status_code == 409
    assert "Username taken" in res.json()["detail"]

    # Duplicate email
    res = client_instance.post("/api/auth/signup", json={"email": email, "username": f"other_{username}", "password": "password123"})
    assert res.status_code == 409
    assert "email already exists" in res.json()["detail"]

def test_verify_code_validation(client_instance):
    # Invalid non-digit code
    res = client_instance.post("/api/auth/verify", json={"code": "abcde1"})
    assert res.status_code == 400
    assert "6-digit" in res.json()["detail"]

    # Wrong code
    res = client_instance.post("/api/auth/verify", json={"code": "000000"})
    assert res.status_code == 400
    assert "Invalid confirmation code" in res.json()["detail"]

def test_unauthenticated_access_protection(client_instance):
    # Missing Auth
    res = client_instance.post("/api/game/new")
    assert res.status_code == 401
    assert "Authentication required" in res.json()["detail"]

    res = client_instance.get("/api/game/state", params={"session_id": "some-id"})
    assert res.status_code == 401

    res = client_instance.post("/api/avatar/finalize", params={"session_id": "some-id"}, json=avatar())
    assert res.status_code == 401

def test_battle_flow_cooldown_and_duplicate_spells(client_instance, auth_headers):
    s = start(client_instance, auth_headers)
    sid = s["session_id"]
    client_instance.post('/api/avatar/finalize', params={'session_id':sid}, json=avatar(), headers=auth_headers)

    # 1. Select spell
    q1 = client_instance.post('/api/battle/select-spell', params={'session_id':sid}, json={'spell_id':'fire-spark'}, headers=auth_headers).json()
    assert q1["active_spell"] == "fire-spark"

    # 2. Selecting another spell while question is active should fail (409)
    res = client_instance.post('/api/battle/select-spell', params={'session_id':sid}, json={'spell_id':'resonance-burst'}, headers=auth_headers)
    assert res.status_code == 409
    assert "Answer the active" in res.json()["detail"]

    # 3. Answer correctly
    answer = find_correct_answer(q1['question']['prompt'])
    ans_res = client_instance.post('/api/battle/answer', params={'session_id':sid}, json={'answer':answer}, headers=auth_headers).json()
    assert ans_res["correct"] is True
    assert ans_res["damage"] > 0

    # 4. Selecting it again immediately should raise 409 due to cooldown
    res = client_instance.post('/api/battle/select-spell', params={'session_id':sid}, json={'spell_id':'fire-spark'}, headers=auth_headers)
    assert res.status_code == 409
    assert "cooling down" in res.json()["detail"]


def test_healthcheck_endpoints(client_instance):
    # Live probe
    res = client_instance.get("/health/live")
    assert res.status_code == 200
    assert res.json() == {"status": "alive"}

    # Ready probe
    res = client_instance.get("/health/ready")
    assert res.status_code == 200
    assert res.json() == {"status": "ready"}


# --- User Content Mode Database Switching & Priority Tests ---

def test_user_content_mode_database_switching(client_instance, auth_headers, monkeypatch):
    # Ensure environment override is clean for this test
    monkeypatch.delenv("GAME_CONTENT_SOURCE", raising=False)
    import app as app_mod
    app_mod.sync_global_content_views()

    # 1. Check default is json mode (data/chapters)
    me_res = client_instance.get("/api/auth/me", headers=auth_headers).json()
    assert me_res["user"]["content_source"] is None
    assert me_res["user"]["effective_mode"] == "json"

    # Start game, verify json boss
    s = start(client_instance, auth_headers)
    assert s["boss"]["name"] == "Orbital Ogre"
    assert s["mode"] == "json"

    # 2. Switch user to APP mode in database
    switch_res = client_instance.post("/api/user/mode", json={"mode": "app"}, headers=auth_headers)
    assert switch_res.status_code == 200
    data = switch_res.json()
    assert data["content_source"] == "app"
    assert data["effective_mode"] == "app"
    assert data["state"]["boss"]["name"] == "Hybridization Goblin"
    assert data["state"]["mode"] == "app"

    # Verify user profile reflects app mode
    me_res2 = client_instance.get("/api/auth/me", headers=auth_headers).json()
    assert me_res2["user"]["content_source"] == "app"
    assert me_res2["user"]["effective_mode"] == "app"

    # Verify game state reflects app mode
    state_res = client_instance.get("/api/game/state", params={"session_id": s["session_id"]}, headers=auth_headers).json()
    assert state_res["boss"]["name"] == "Hybridization Goblin"

    # 3. Switch user back to JSON mode in database
    switch_back = client_instance.post("/api/user/content-source", json={"content_source": "json"}, headers=auth_headers)
    assert switch_back.status_code == 200
    data_back = switch_back.json()
    assert data_back["content_source"] == "json"
    assert data_back["effective_mode"] == "json"
    assert data_back["state"]["boss"]["name"] == "Orbital Ogre"



def test_env_priority_overrides_database_user_setting(client_instance, auth_headers, monkeypatch):
    import app as app_mod
    # 1. Set user in DB to "json" mode
    monkeypatch.delenv("GAME_CONTENT_SOURCE", raising=False)
    client_instance.post("/api/user/mode", json={"mode": "json"}, headers=auth_headers)

    # 2. Set .env / process env to "app" -> should OVERRIDE DB user setting
    monkeypatch.setenv("GAME_CONTENT_SOURCE", "app")
    app_mod.sync_global_content_views()

    me_res = client_instance.get("/api/auth/me", headers=auth_headers).json()
    assert me_res["user"]["content_source"] == "json"  # DB value preserved
    assert me_res["user"]["effective_mode"] == "app"   # .env override applied

    s = start(client_instance, auth_headers)
    assert s["boss"]["name"] == "Hybridization Goblin"
    assert s["mode"] == "app"

    # 3. Set user in DB to "app" mode, but .env to "json" -> should OVERRIDE DB user setting
    monkeypatch.delenv("GAME_CONTENT_SOURCE", raising=False)
    client_instance.post("/api/user/mode", json={"mode": "app"}, headers=auth_headers)

    monkeypatch.setenv("GAME_CONTENT_SOURCE", "json")
    app_mod.sync_global_content_views()

    me_res2 = client_instance.get("/api/auth/me", headers=auth_headers).json()
    assert me_res2["user"]["content_source"] == "app"  # DB value preserved
    assert me_res2["user"]["effective_mode"] == "json"  # .env override applied

    s2 = start(client_instance, auth_headers)
    assert s2["boss"]["name"] == "Orbital Ogre"
    assert s2["mode"] == "json"


def test_user_mode_validation_errors(client_instance, auth_headers):
    # Invalid mode string
    res = client_instance.post("/api/user/mode", json={"mode": "xml"}, headers=auth_headers)
    assert res.status_code == 400
    assert "Content mode must be 'app' or 'json'" in res.json()["detail"]

    # Empty payload
    res2 = client_instance.post("/api/user/mode", json={}, headers=auth_headers)
    assert res2.status_code == 400


# --- Admin User Configuration Screen & Mode Switching Tests ---

def test_admin_authentication_and_protection(client_instance):
    # 1. Unauthenticated access fails
    unauth_res = client_instance.get("/api/admin/status")
    assert unauth_res.status_code == 401

    # 2. Invalid login
    res = client_instance.post("/api/admin/login", json={"username": "admin", "password": "wrongpassword"})
    assert res.status_code == 401
    assert "Incorrect admin username" in res.json()["detail"]

    # 3. Valid login
    login_res = client_instance.post("/api/admin/login", json={"username": "admin", "password": "admin"})
    assert login_res.status_code == 200
    admin_token = login_res.json()["token"]
    assert login_res.json()["username"] == "admin"

    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 4. Access admin status with auth
    status_res = client_instance.get("/api/admin/status", headers=admin_headers)
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "ok"

    # 5. Admin logout
    logout_res = client_instance.post("/api/admin/logout", headers=admin_headers)
    assert logout_res.status_code == 200

    # Token should now be invalid
    after_logout = client_instance.get("/api/admin/status", headers=admin_headers)
    assert after_logout.status_code == 401


def test_admin_change_user_content_source(client_instance, auth_headers, monkeypatch):
    # Ensure env override is unset
    monkeypatch.delenv("GAME_CONTENT_SOURCE", raising=False)
    import app as app_mod
    app_mod.sync_global_content_views()

    # Get current regular user id
    me = client_instance.get("/api/auth/me", headers=auth_headers).json()["user"]
    user_id = me["id"]

    # Log in as admin
    admin_login = client_instance.post("/api/admin/login", json={"username": "admin", "password": "admin"}).json()
    admin_headers = {"Authorization": f"Bearer {admin_login['token']}"}

    # Admin lists users
    users_res = client_instance.get("/api/admin/users", headers=admin_headers)
    assert users_res.status_code == 200
    users = users_res.json()["users"]
    target_user = next((u for u in users if u["id"] == user_id), None)
    assert target_user is not None

    # Admin changes user to "json" mode
    update_res = client_instance.post(
        f"/api/admin/users/{user_id}/config",
        json={"content_source": "json"},
        headers=admin_headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["content_source"] == "json"
    assert update_res.json()["effective_mode"] == "json"

    # User starts game and receives JSON boss
    s = start(client_instance, auth_headers)
    assert s["boss"]["name"] == "Orbital Ogre"
    assert s["mode"] == "json"

    # Admin changes user back to "app" mode
    update_res2 = client_instance.post(
        f"/api/admin/users/{user_id}/config",
        json={"content_source": "app"},
        headers=admin_headers
    )
    assert update_res2.status_code == 200
    assert update_res2.json()["content_source"] == "app"
    assert update_res2.json()["effective_mode"] == "app"

    # User state reflects app boss
    s2 = start(client_instance, auth_headers)
    assert s2["boss"]["name"] == "Hybridization Goblin"
    assert s2["mode"] == "app"

    # Admin sends invalid content_source
    bad_res = client_instance.post(
        f"/api/admin/users/{user_id}/config",
        json={"content_source": "invalid_mode"},
        headers=admin_headers
    )
    assert bad_res.status_code == 400


def test_admin_sessions_management_and_reset(client_instance, auth_headers):
    # 1. Start a game session for the user
    s = start(client_instance, auth_headers)
    sid = s["session_id"]
    client_instance.post('/api/avatar/finalize', params={'session_id': sid}, json=avatar(), headers=auth_headers)

    # Damage the boss and answer a question to dirty session state
    q = client_instance.post('/api/battle/select-spell', params={'session_id': sid}, json={'spell_id': 'fire-spark'}, headers=auth_headers).json()
    ans = find_correct_answer(q['question']['prompt'])
    client_instance.post('/api/battle/answer', params={'session_id': sid}, json={'answer': ans}, headers=auth_headers)

    # 2. Log in as admin
    admin_login = client_instance.post("/api/admin/login", json={"username": "admin", "password": "admin"}).json()
    admin_headers = {"Authorization": f"Bearer {admin_login['token']}"}

    # 3. List sessions
    sessions_res = client_instance.get("/api/admin/sessions", headers=admin_headers)
    assert sessions_res.status_code == 200
    sessions_list = sessions_res.json()["sessions"]
    target_session = next((sess for sess in sessions_list if sess["session_id"] == sid), None)
    assert target_session is not None
    assert target_session["chapter"] == 1
    assert len(target_session["available_chapters"]) >= 3

    # 4. Reset session to Chapter 2
    reset_res = client_instance.post(
        f"/api/admin/sessions/{sid}/reset",
        json={"chapter": 2},
        headers=admin_headers
    )
    assert reset_res.status_code == 200
    reset_data = reset_res.json()
    assert reset_data["chapter"] == 2
    assert reset_data["boss_index"] == 0
    assert reset_data["player_hp"] == 150
    assert reset_data["boss_hp"] > 0

    # 5. User checks their game state and confirms Chapter 2, Boss 1
    user_state = client_instance.get("/api/game/state", params={"session_id": sid}, headers=auth_headers).json()
    assert user_state["chapter"] == 2
    assert user_state["boss"]["name"] == reset_data["boss_name"]
    assert user_state["question"] is None
    assert user_state["active_spell"] is None


def test_admin_sessions_delete(client_instance, auth_headers):
    # 1. Start a game session for the user
    s = start(client_instance, auth_headers)
    sid = s["session_id"]

    # 2. Log in as admin
    admin_login = client_instance.post("/api/admin/login", json={"username": "admin", "password": "admin"}).json()
    admin_headers = {"Authorization": f"Bearer {admin_login['token']}"}

    # 3. Delete the session
    del_res = client_instance.delete(f"/api/admin/sessions/{sid}", headers=admin_headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "ok"

    # 4. Trying to fetch the deleted session fails with 404
    state_res = client_instance.get("/api/game/state", params={"session_id": sid}, headers=auth_headers)
    assert state_res.status_code == 404

    # 5. User starting a new game gets a brand-new session
    new_s = start(client_instance, auth_headers)
    assert new_s["session_id"] != sid
    assert new_s["chapter"] == 1
    assert new_s["boss"]["hp"] > 0



