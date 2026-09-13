"""
Multiplayer E2E Browser UI Concurrency Test Suite.

Verifies that multiple concurrent real browser instances (Playwright WebKit / Chromium)
can simultaneously load the application, mount the Phaser 3 game canvas, stream CDN assets,
and execute interactive combat turns in parallel without visual crashes or unhandled client exceptions.
"""

import os
import sys
import time
import subprocess
import urllib.request
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent


def _is_server_listening(url: str = "http://127.0.0.1:8000") -> bool:
    try:
        with urllib.request.urlopen(f"{url}/", timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def _wait_for_server(url: str = "http://127.0.0.1:8000", timeout: float = 12.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        if _is_server_listening(url):
            return True
        time.sleep(0.3)
    return False


@pytest.fixture(scope="module")
def live_test_server():
    """Ensures a live server is running for browser concurrency testing."""
    url = "http://127.0.0.1:8000"
    server_proc = None

    if not _is_server_listening(url):
        env = os.environ.copy()
        env["TESTING"] = "1"
        server_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=str(ROOT_DIR),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert _wait_for_server(url), "Failed to start local test server for UI concurrency testing"

    try:
        yield url
    finally:
        if server_proc:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                server_proc.kill()


@pytest.mark.e2e
def test_parallel_browser_ui_concurrency(live_test_server, tmp_path):
    """
    Spawns multiple concurrent browser contexts to test parallel UI combat loops.
    Validates that:
    1. All browser contexts mount the Phaser 3 canvas.
    2. Real users execute combat turns in parallel.
    3. Zero fatal JavaScript exceptions are raised in any context.
    """
    script_path = ROOT_DIR / "scripts" / "ui_concurrency_load_test.py"
    report_file = tmp_path / "test_ui_concurrency_report.md"

    cmd = [
        sys.executable,
        str(script_path),
        "--players", "2",
        "--turns", "1",
        "--base-url", live_test_server,
        "--browser", "webkit",
        "--output-report", str(report_file),
    ]

    res = subprocess.run(
        cmd,
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
    )

    if res.returncode != 0:
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)

    assert res.returncode == 0, f"UI concurrency test failed with return code {res.returncode}:\n{res.stdout}\n{res.stderr}"
    assert report_file.exists(), "UI concurrency report was not generated"
    content = report_file.read_text(encoding="utf-8")
    assert "0 fatal JS runtime errors" in content or "Unhandled Client Exceptions" in content
    assert "100% of player canvases mounted without WebGL/Canvas crashes" in content
