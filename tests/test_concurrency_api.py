"""
Multiplayer API Concurrency & Load Test Suite.

Verifies that multiple concurrent virtual players can authenticate, create game sessions,
select spells, answer questions, and resolve combat turns in parallel without deadlocks,
data corruption, or state leakage.
"""

import asyncio
import time
import uuid
import httpx
import pytest
from app.main import app
from app.infrastructure.database.engine import SessionLocal
from app.infrastructure.database.models import User, AuthSession
from app.infrastructure.identity.crypto import hash_password, code_hash, generate_session_token


def _seed_virtual_player(player_index: int):
    """Pre-seeds a verified user and auth session for concurrent testing."""
    user_id = str(uuid.uuid4())
    username = f"api_concurrent_{player_index}_{uuid.uuid4().hex[:6]}"
    token = generate_session_token()
    thash = code_hash(token)

    with SessionLocal() as db:
        user = User(
            id=user_id,
            email=f"{username}@concurrency.edu",
            username=username,
            password_hash=hash_password("ConcurrentPass123!"),
            verified=1,
            created_at=int(time.time()),
        )
        db.add(user)
        auth_sess = AuthSession(
            token_hash=thash,
            user_id=user_id,
            expires_at=int(time.time()) + 86400 * 7,
            created_at=int(time.time()),
        )
        db.add(auth_sess)
        db.commit()

    return user_id, username, token


def test_concurrent_player_authentication_and_initialization():
    """Verify 5 players can concurrently initialize game sessions and set avatars without deadlock."""
    num_players = 5

    async def _simulate_player(idx: int):
        user_id, username, token = _seed_virtual_player(idx)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Auth check
            me_resp = await client.get("/api/auth/me", headers=headers)
            assert me_resp.status_code == 200, f"Player {idx} auth verification failed"
            assert me_resp.json()["user"]["username"] == username

            # 2. Create game session concurrently
            game_resp = await client.post("/api/game/new", headers=headers, json={})
            assert game_resp.status_code == 200, f"Player {idx} game initialization failed"
            sess_data = game_resp.json()
            session_id = sess_data["session_id"]
            assert session_id is not None

            # 3. Finalize avatar concurrently
            avatar_payload = {
                "session_id": session_id,
                "character": "alchemist",
                "body": "arc",
                "skin": "warm",
                "hair": "nebula",
                "outfit": "coat",
                "accessory": "goggles",
                "aura": "teal",
            }
            avatar_resp = await client.post("/api/avatar/finalize", headers=headers, json=avatar_payload)
            assert avatar_resp.status_code == 200, f"Player {idx} avatar finalization failed"

            # 4. Synchronize game state
            state_resp = await client.get(f"/api/game/state?session_id={session_id}", headers=headers)
            assert state_resp.status_code == 200, f"Player {idx} get state failed"
            state_data = state_resp.json()
            assert state_data["session_id"] == session_id
            assert state_data["boss"]["hp"] > 0
            assert state_data["player"]["hp"] > 0

            return session_id

    async def _run_all():
        session_ids = await asyncio.gather(*(_simulate_player(i) for i in range(num_players)))
        assert len(session_ids) == num_players
        assert len(set(session_ids)) == num_players, "Session IDs must be strictly unique across players"

    asyncio.run(_run_all())


def test_concurrent_combat_turn_resolution():
    """Verify multiple concurrent players can execute combat turns simultaneously."""
    num_players = 4

    async def _execute_combat_turn(idx: int):
        user_id, username, token = _seed_virtual_player(idx)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. New game
            new_res = await client.post("/api/game/new", headers=headers, json={})
            session_id = new_res.json()["session_id"]

            # 2. Select spell concurrently
            spell_res = await client.post(
                "/api/battle/select-spell",
                headers=headers,
                json={"session_id": session_id, "spell_id": "fire-spark"}
            )
            assert spell_res.status_code == 200, f"Player {idx} spell select failed"
            spell_data = spell_res.json()
            turn_id = spell_data.get("turn_id")
            assert turn_id is not None
            assert spell_data.get("question") is not None

            # 3. Answer question concurrently
            ans_res = await client.post(
                "/api/battle/answer",
                headers=headers,
                json={
                    "session_id": session_id,
                    "turn_id": turn_id,
                    "answer": "A",
                    "expected_version": spell_data.get("version", 1),
                }
            )
            assert ans_res.status_code == 200, f"Player {idx} answer submission failed"
            ans_data = ans_res.json()
            assert "boss" in ans_data
            assert "player" in ans_data
            assert ans_data["turn_id"] is None  # Turn ID must be cleared after resolution

            return True

    async def _run_combat():
        results = await asyncio.gather(*(_execute_combat_turn(i) for i in range(num_players)))
        assert all(results)

    asyncio.run(_run_combat())
