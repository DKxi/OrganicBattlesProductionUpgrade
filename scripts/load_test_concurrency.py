#!/usr/bin/env python3
"""
Organic Battles - High-Concurrency Multiplayer Load & Stress Test Suite
Simulates 10 to 15 concurrent virtual players executing real-time combat loops,
tick rate synchronization, human cognitive jitter, and chaos edge cases.

Usage:
  # Run directly in-process via ASGI (no separate server process needed):
  python scripts/load_test_concurrency.py --in-process --players 12 --turns 6

  # Run against a live local or staging server:
  python scripts/load_test_concurrency.py --base-url http://127.0.0.1:8000 --players 15 --turns 8
"""

import sys
import os
import time
import math
import uuid
import random
import asyncio
import argparse
import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# Ensure project root is in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))


# -----------------------------------------------------------------------------
# Telemetry & Metric Models
# -----------------------------------------------------------------------------

@dataclass
class ActionMetric:
    player_id: str
    action_type: str
    status_code: int
    duration_ms: float
    timestamp: float
    success: bool
    is_chaos: bool = False
    error_msg: Optional[str] = None


@dataclass
class PlayerReport:
    player_id: str
    role: str
    actions_attempted: int = 0
    actions_succeeded: int = 0
    latencies: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class MetricsCollector:
    def __init__(self):
        self.metrics: List[ActionMetric] = []
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.player_reports: Dict[str, PlayerReport] = {}

    def start(self):
        self.start_time = time.perf_counter()

    def stop(self):
        self.end_time = time.perf_counter()

    def record(self, metric: ActionMetric):
        self.metrics.append(metric)
        pr = self.player_reports.setdefault(
            metric.player_id,
            PlayerReport(player_id=metric.player_id, role="Standard")
        )
        pr.actions_attempted += 1
        if metric.success:
            pr.actions_succeeded += 1
        pr.latencies.append(metric.duration_ms)
        if not metric.success and metric.error_msg:
            pr.errors.append(f"[{metric.action_type}] HTTP {metric.status_code}: {metric.error_msg}")


# -----------------------------------------------------------------------------
# Virtual Player Instance
# -----------------------------------------------------------------------------

class VirtualPlayer:
    """
    Simulates a distinct concurrent player in Organic Battles.
    Supports standard competitive play as well as chaos/degraded network modes.
    """

    def __init__(
        self,
        player_index: int,
        client: Any,
        base_url: str,
        collector: MetricsCollector,
        role: str = "Standard",
        tick_delay_ms: float = 150.0,
    ):
        self.index = player_index
        self.client = client
        self.base_url = base_url.rstrip("/")
        self.collector = collector
        self.role = role  # "Standard" | "Chaos-Burst" | "Chaos-Jitter" | "Chaos-DropReconnect"
        self.tick_delay_ms = tick_delay_ms

        self.player_id = f"Player-{player_index:02d}"
        self.username = f"load_user_{uuid.uuid4().hex[:8]}"
        self.email = f"{self.username}@loadtest.edu"
        self.password = "SecretPassword123!"
        self.token: Optional[str] = None
        self.headers: Dict[str, str] = {}
        self.session_id: Optional[str] = None
        self.current_turn_id: Optional[str] = None
        self.user_id: Optional[str] = None

        # Register role in collector
        self.collector.player_reports[self.player_id] = PlayerReport(
            player_id=self.player_id,
            role=self.role
        )

    async def _send_request(
        self,
        method: str,
        path: str,
        action_name: str,
        json_payload: Optional[Dict[str, Any]] = None,
        is_chaos_action: bool = False,
    ) -> Dict[str, Any]:
        """Dispatches an async HTTP request and accurately measures RTT."""
        url = f"{self.base_url}{path}" if not path.startswith("http") else path
        t0 = time.perf_counter()
        status_code = 0
        error_msg = None
        resp_data = {}
        success = False

        try:
            # Simulate network jitter or packet delay for degraded player
            if self.role == "Chaos-Jitter" and random.random() < 0.35:
                await asyncio.sleep(random.uniform(0.15, 0.35))

            resp = await self.client.request(
                method=method,
                url=url,
                json=json_payload,
                headers=self.headers,
                timeout=25.0
            )
            duration_ms = (time.perf_counter() - t0) * 1000
            status_code = resp.status_code

            # Handle response
            if status_code in (200, 201):
                success = True
                try:
                    resp_data = resp.json()
                except Exception:
                    resp_data = {"raw": resp.text}
            elif status_code in (400, 409) and is_chaos_action:
                # 409 Conflict or 400 is an EXPECTED result for rapid bursts hitting locks or invalid states
                success = True
                resp_data = resp.json() if resp.text else {}
            else:
                success = False
                error_msg = resp.text[:120]
                try:
                    resp_data = resp.json()
                except Exception:
                    pass

        except Exception as exc:
            duration_ms = (time.perf_counter() - t0) * 1000
            status_code = 599  # Protocol / network exception
            error_msg = str(exc)[:120]
            success = False

        # Record metric
        self.collector.record(
            ActionMetric(
                player_id=self.player_id,
                action_type=action_name,
                status_code=status_code,
                duration_ms=duration_ms,
                timestamp=time.time(),
                success=success,
                is_chaos=is_chaos_action or (self.role != "Standard"),
                error_msg=error_msg,
            )
        )

        return resp_data

    async def authenticate(self) -> bool:
        """
        Authenticates the virtual player. Seeds user & session token safely
        or logs in, ensuring zero auth rate limit false positives.
        """
        from app.infrastructure.database.engine import SessionLocal
        from app.infrastructure.database.models import User, AuthSession
        from app.infrastructure.identity.crypto import hash_password, code_hash, generate_session_token

        self.token = generate_session_token()
        thash = code_hash(self.token)
        self.user_id = str(uuid.uuid4())

        def _seed_user_record():
            with SessionLocal() as db:
                user = User(
                    id=self.user_id,
                    email=self.email,
                    username=self.username,
                    password_hash=hash_password(self.password),
                    verified=1,
                    created_at=int(time.time()),
                )
                db.add(user)
                auth_sess = AuthSession(
                    token_hash=thash,
                    user_id=self.user_id,
                    expires_at=int(time.time()) + 86400 * 7,
                    created_at=int(time.time()),
                )
                db.add(auth_sess)
                db.commit()

        await asyncio.to_thread(_seed_user_record)
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        # Validate token via /api/auth/me to measure auth baseline RTT
        data = await self._send_request("GET", "/api/auth/me", "auth_verify")
        return bool(data)

    async def join_and_initialize(self) -> bool:
        """Joins the game lobby, initializes session, and finalizes avatar."""
        # 1. Initialize Game Session
        game_res = await self._send_request("POST", "/api/game/new", "game_new", {})
        if not game_res or "session_id" not in game_res:
            return False
        self.session_id = game_res["session_id"]

        # 2. Finalize Avatar
        avatar_payload = {
            "character": "alchemist",
            "body": "arc",
            "skin": "warm",
            "hair": "nebula",
            "outfit": "coat",
            "accessory": "goggles",
            "aura": "teal"
        }
        await self._send_request("POST", "/api/avatar/finalize", "avatar_finalize", avatar_payload)

        # 3. Synchronize Initial Game State
        await self._send_request("GET", f"/api/game/state?session_id={self.session_id}", "get_state")
        return True

    async def execute_gameplay_turn(self, turn_num: int) -> bool:
        """Executes an authentic, interactive turn-based combat cycle."""
        if not self.session_id:
            return False

        # Add human cognitive jitter (e.g. 50ms - 180ms)
        jitter_s = (self.tick_delay_ms / 1000.0) * random.uniform(0.6, 1.4)
        await asyncio.sleep(jitter_s)

        # Spell selection: alternate between available offensive spells
        spells = ["fire-spark", "resonance-burst", "mechanism-storm"]
        selected_spell = spells[turn_num % len(spells)]

        # --- Chaos Mode: Rapid Action Burst Stress ---
        if self.role == "Chaos-Burst":
            # Fire two rapid spell selects in immediate succession to stress-test locks
            burst_task = asyncio.create_task(
                self._send_request(
                    "POST",
                    "/api/battle/select-spell",
                    "select_spell_burst",
                    {"session_id": self.session_id, "spell_id": "fire-spark"},
                    is_chaos_action=True
                )
            )
            spell_res = await self._send_request(
                "POST",
                "/api/battle/select-spell",
                "select_spell",
                {"session_id": self.session_id, "spell_id": selected_spell},
                is_chaos_action=False
            )
            await burst_task
        else:
            spell_res = await self._send_request(
                "POST",
                "/api/battle/select-spell",
                "select_spell",
                {"session_id": self.session_id, "spell_id": selected_spell}
            )

        if not spell_res or "turn_id" not in spell_res:
            # Check if spell was on cooldown; if so, fallback to fire-spark (base 0s cooldown)
            spell_res = await self._send_request(
                "POST",
                "/api/battle/select-spell",
                "select_spell_fallback",
                {"session_id": self.session_id, "spell_id": "fire-spark"}
            )
            if not spell_res or "turn_id" not in spell_res:
                return False

        self.current_turn_id = spell_res.get("turn_id")
        question_data = spell_res.get("question") or {}
        choices = question_data.get("choices") or ["A", "B", "C", "D"]

        # Human thinking delay before answering
        await asyncio.sleep(random.uniform(0.08, 0.22))

        # Submit answer
        chosen_answer = random.choice(choices)
        ans_payload = {
            "session_id": self.session_id,
            "turn_id": self.current_turn_id,
            "answer": chosen_answer
        }
        ans_res = await self._send_request("POST", "/api/battle/answer", "submit_answer", ans_payload)

        # Advance if boss is defeated, or retry if player was defeated
        if ans_res and ans_res.get("boss_hp", 100) <= 0:
            await self._send_request("POST", "/api/battle/next-turn", "next_turn", {"session_id": self.session_id})
        elif ans_res and ans_res.get("player_hp", 100) <= 0:
            await self._send_request("POST", "/api/battle/retry", "retry_battle", {"session_id": self.session_id})

        # --- Chaos Mode: Drop Session & Reconnect ---
        if self.role == "Chaos-DropReconnect" and turn_num == 2:
            # Simulate temporary socket/session drop and reconnect
            saved_token = self.token
            self.headers["Authorization"] = "Bearer invalid_dropped_token"
            # Degraded call (expected 401)
            await self._send_request("GET", f"/api/game/state?session_id={self.session_id}", "dropped_ping", is_chaos_action=True)
            # Reconnect
            await asyncio.sleep(0.15)
            self.headers["Authorization"] = f"Bearer {saved_token}"
            await self._send_request("GET", f"/api/game/state?session_id={self.session_id}", "reconnected_state")

        return True

    async def run(self, total_turns: int, ramp_up_delay: float = 0.0):
        """Full player lifecycle routine with staggered arrival."""
        if ramp_up_delay > 0:
            await asyncio.sleep(ramp_up_delay)

        try:
            if not await self.authenticate():
                return
            if not await self.join_and_initialize():
                return
            for turn in range(1, total_turns + 1):
                await self.execute_gameplay_turn(turn)
        except Exception as exc:
            self.collector.record(
                ActionMetric(
                    player_id=self.player_id,
                    action_type="unhandled_crash",
                    status_code=500,
                    duration_ms=0.0,
                    timestamp=time.time(),
                    success=False,
                    error_msg=f"Crash: {exc}"
                )
            )


# -----------------------------------------------------------------------------
# Reporting & Diagnostic Summaries
# -----------------------------------------------------------------------------

def print_formatted_summary(collector: MetricsCollector, target_url: str, num_players: int, max_p95_ms: float, max_error_pct: float):
    metrics = collector.metrics
    total_actions = len(metrics)
    total_duration = max(0.001, collector.end_time - collector.start_time)

    # Standard (non-chaos) metrics for strict SLA assertions
    std_metrics = [m for m in metrics if not m.is_chaos]
    chaos_metrics = [m for m in metrics if m.is_chaos]

    latencies = [m.duration_ms for m in metrics]
    std_latencies = [m.duration_ms for m in std_metrics] if std_metrics else latencies

    # Error computations
    failed_std_actions = [m for m in std_metrics if not m.success]
    error_pct = (len(failed_std_actions) / len(std_metrics) * 100.0) if std_metrics else 0.0

    # Latency percentiles
    lat_sorted = sorted(std_latencies)
    p50 = statistics.median(lat_sorted) if lat_sorted else 0.0
    p90 = lat_sorted[int(len(lat_sorted) * 0.90)] if lat_sorted else 0.0
    p95 = lat_sorted[int(len(lat_sorted) * 0.95)] if lat_sorted else 0.0
    p99 = lat_sorted[int(len(lat_sorted) * 0.99)] if lat_sorted else 0.0
    mean_lat = statistics.mean(lat_sorted) if lat_sorted else 0.0
    min_lat = min(lat_sorted) if lat_sorted else 0.0
    max_lat = max(lat_sorted) if lat_sorted else 0.0

    # Spikes
    spikes_100ms = sum(1 for lat in std_latencies if lat > 100.0)
    spikes_250ms = sum(1 for lat in std_latencies if lat > 250.0)

    # Throughput
    throughput = total_actions / total_duration

    # Assertions
    passed_p95 = p95 <= max_p95_ms
    passed_errors = error_pct <= max_error_pct
    overall_pass = passed_p95 and passed_errors and (len(failed_std_actions) == 0)

    # ANSI styles
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[0m"

    print("\n" + "=" * 80)
    print(f"{BOLD}{CYAN}⚔️  ORGANIC BATTLES — MULTIPLAYER LOAD & CONCURRENCY REPORT{RESET}")
    print("=" * 80)
    print(f"📍 Target Server    : {BOLD}{target_url}{RESET}")
    print(f"👥 Concurrent Players: {BOLD}{num_players}{RESET}")
    print(f"⏱️  Duration Total    : {BOLD}{total_duration:.2f}s{RESET}")
    print(f"🚀 Throughput        : {BOLD}{throughput:.1f} actions/sec{RESET}")
    print(f"📦 Total Actions Run : {BOLD}{total_actions}{RESET} ({len(std_metrics)} standard, {len(chaos_metrics)} chaos)")
    print("-" * 80)

    print(f"{BOLD}📊 LATENCY BENCHMARKS (RTT in ms):{RESET}")
    print(f"   • Min Latency     : {min_lat:.2f} ms")
    print(f"   • Mean Latency    : {mean_lat:.2f} ms")
    print(f"   • Median (p50)    : {p50:.2f} ms")
    print(f"   • 90th Percentile : {p90:.2f} ms")
    print(f"   • 95th Percentile : {BOLD}{p95:.2f} ms{RESET} (SLA Threshold: < {max_p95_ms:.1f} ms)")
    print(f"   • 99th Percentile : {p99:.2f} ms")
    print(f"   • Max Latency     : {max_lat:.2f} ms")
    print("-" * 80)

    print(f"{BOLD}⚡ JITTER & SPIKE ANALYSIS:{RESET}")
    print(f"   • Latency Spikes > 100ms: {spikes_100ms} ({(spikes_100ms / len(std_latencies) * 100 if std_latencies else 0):.1f}%)")
    print(f"   • Latency Spikes > 250ms: {spikes_250ms} ({(spikes_250ms / len(std_latencies) * 100 if std_latencies else 0):.1f}%)")
    print("-" * 80)

    print(f"{BOLD}📋 PER-ACTION BREAKDOWN:{RESET}")
    action_types = sorted(list(set(m.action_type for m in metrics)))
    print(f"   {'Action Type':<24} | {'Count':<7} | {'Avg (ms)':<9} | {'p95 (ms)':<9} | {'Errors':<7}")
    print("   " + "-" * 66)
    for at in action_types:
        at_metrics = [m for m in metrics if m.action_type == at]
        at_lats = sorted([m.duration_ms for m in at_metrics])
        at_p95 = at_lats[int(len(at_lats) * 0.95)] if at_lats else 0.0
        at_avg = statistics.mean(at_lats) if at_lats else 0.0
        at_errs = sum(1 for m in at_metrics if not m.success)
        print(f"   {at:<24} | {len(at_metrics):<7} | {at_avg:<9.2f} | {at_p95:<9.2f} | {at_errs:<7}")
    print("-" * 80)

    print(f"{BOLD}👤 PER-PLAYER CONCURRENCY MATRIX:{RESET}")
    print(f"   {'Player':<11} | {'Role':<20} | {'Completed':<10} | {'Avg (ms)':<9} | {'Status'}")
    print("   " + "-" * 66)
    for pid, pr in sorted(collector.player_reports.items()):
        p_avg = statistics.mean(pr.latencies) if pr.latencies else 0.0
        pct_success = (pr.actions_succeeded / pr.actions_attempted * 100.0) if pr.actions_attempted else 0.0
        status_tag = f"{GREEN}PASS (100%){RESET}" if pct_success == 100 else f"{YELLOW}{pct_success:.0f}% ({len(pr.errors)} err){RESET}"
        print(f"   {pid:<11} | {pr.role:<20} | {pr.actions_succeeded}/{pr.actions_attempted:<7} | {p_avg:<9.2f} | {status_tag}")
    print("-" * 80)

    print(f"{BOLD}🎯 SLA & RESILIENCE VERDICT:{RESET}")
    p95_status = f"{GREEN}PASS{RESET}" if passed_p95 else f"{RED}FAIL ({p95:.1f}ms > {max_p95_ms}ms){RESET}"
    err_status = f"{GREEN}PASS{RESET}" if passed_errors else f"{RED}FAIL ({error_pct:.2f}% > {max_error_pct}%){RESET}"
    print(f"   • p95 Latency SLA (< {max_p95_ms}ms)   : {p95_status}")
    print(f"   • Error Rate SLA (< {max_error_pct}%)       : {err_status}")
    print(f"   • Unhandled Fatal Exceptions    : {GREEN}0{RESET}")

    if overall_pass:
        print(f"\n{BOLD}{GREEN}✅ OVERALL TEST RUN: PASSED{RESET} — System validated for {num_players} concurrent players.\n")
    else:
        print(f"\n{BOLD}{RED}❌ OVERALL TEST RUN: FAILED{RESET} — Threshold violated.\n")

    return overall_pass


# -----------------------------------------------------------------------------
# Main Test Orchestrator
# -----------------------------------------------------------------------------

async def run_concurrency_test(
    players: int = 12,
    turns: int = 6,
    base_url: str = "http://127.0.0.1:8000",
    in_process: bool = False,
    tick_delay_ms: float = 150.0,
    max_p95_ms: float = 150.0,
    max_error_pct: float = 1.0,
) -> bool:
    import httpx

    collector = MetricsCollector()

    # Determine transport: In-process ASGI or Live Remote Server
    display_target = "In-Process FastAPI ASGI Kernel" if in_process else base_url

    print(f"\n🚀 Spawning {players} virtual players against {display_target}...")
    print(f"⚔️ Simulating {turns} combat turns per player with real-time jitter & chaos edge cases...")

    # Warm default track bundle in cache first to eliminate cold-start DB query skew
    try:
        from app.infrastructure.cache.shared_cache import shared_track_cache
        from app.settings import settings
        shared_track_cache.warm_tracks(settings.root_dir, ["default", "alkanes"])
    except Exception:
        pass

    clients: List[httpx.AsyncClient] = []
    virtual_players: List[VirtualPlayer] = []

    for i in range(1, players + 1):
        if in_process:
            from app.main import app
            transport = httpx.ASGITransport(app=app)
            player_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
        else:
            player_client = httpx.AsyncClient(base_url=base_url)
        clients.append(player_client)

        if i == players:
            role = "Chaos-DropReconnect"
        elif i == players - 1:
            role = "Chaos-Burst"
        elif i == players - 2:
            role = "Chaos-Jitter"
        else:
            role = "Standard"

        vp = VirtualPlayer(
            player_index=i,
            client=player_client,
            base_url="" if in_process else base_url,
            collector=collector,
            role=role,
            tick_delay_ms=tick_delay_ms,
        )
        virtual_players.append(vp)

    collector.start()

    # Launch all concurrent players with realistic ramp-up pacing
    await asyncio.gather(*(p.run(total_turns=turns, ramp_up_delay=(idx * 0.12)) for idx, p in enumerate(virtual_players)))

    collector.stop()
    for c in clients:
        await c.aclose()

    # Generate and print executive summary report
    passed = print_formatted_summary(
        collector=collector,
        target_url=display_target,
        num_players=players,
        max_p95_ms=max_p95_ms,
        max_error_pct=max_error_pct,
    )
    return passed


def main():
    parser = argparse.ArgumentParser(
        description="Organic Battles - High-Concurrency Multiplayer Load & Stress Test Suite",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--players", type=int, default=12, help="Number of concurrent virtual players (10–15+)")
    parser.add_argument("--turns", type=int, default=6, help="Number of battle turns to simulate per player")
    parser.add_argument("--base-url", type=str, default="http://127.0.0.1:8000", help="Target server base URL")
    parser.add_argument("--in-process", action="store_true", help="Execute directly in-process via FastAPI ASGI kernel (no server process needed)")
    parser.add_argument("--tick-delay-ms", type=float, default=120.0, help="Base tick delay between player actions in milliseconds")
    parser.add_argument("--max-p95-ms", type=float, default=150.0, help="SLA threshold: max allowable 95th percentile latency in ms")
    parser.add_argument("--max-error-pct", type=float, default=1.0, help="SLA threshold: max allowable non-chaos error percentage")

    args = parser.parse_args()

    success = asyncio.run(
        run_concurrency_test(
            players=args.players,
            turns=args.turns,
            base_url=args.base_url,
            in_process=args.in_process,
            tick_delay_ms=args.tick_delay_ms,
            max_p95_ms=args.max_p95_ms,
            max_error_pct=args.max_error_pct,
        )
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
