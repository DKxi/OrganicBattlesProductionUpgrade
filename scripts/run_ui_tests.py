#!/usr/bin/env python3
"""
Orchestrator script to start test server, run the comprehensive Playwright WebKit
(Safari engine) UI test suite, output latency scorecard, and launch macOS Safari.
"""

import os
import sys
import time
import subprocess
import argparse
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))


def is_server_running(url: str = "http://127.0.0.1:8000") -> bool:
    try:
        with urllib.request.urlopen(f"{url}/docs", timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def wait_for_server(url: str = "http://127.0.0.1:8000", timeout: float = 12.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        if is_server_running(url):
            return True
        time.sleep(0.3)
    return False


def main():
    parser = argparse.ArgumentParser(description="Run UI Test Suite in WebKit / Safari.")
    parser.add_argument("--browser", type=str, default="webkit", choices=["webkit", "chromium"], help="Browser engine")
    parser.add_argument("--headed", action="store_true", help="Launch visible browser during test")
    parser.add_argument("--open-safari", action="store_true", help="Launch macOS Safari desktop app")
    parser.add_argument("--skip-safari", action="store_true", help="Deprecated alias; desktop Safari is off by default")
    args = parser.parse_args()

    server_proc = None
    server_url = "http://127.0.0.1:8000"

    if not is_server_running(server_url):
        print(f"📡 Starting Organic Battles server on {server_url} (TESTING=1)...")
        env = os.environ.copy()
        env["TESTING"] = "1"
        server_proc = subprocess.Popen(
            [str(ROOT_DIR / ".venv" / "bin" / "uvicorn"), "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=str(ROOT_DIR),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if not wait_for_server(server_url):
            print("❌ Failed to start test server!")
            if server_proc:
                server_proc.kill()
            sys.exit(1)
        print("✅ Server is online and responding.")
    else:
        print(f"✅ Existing server detected on {server_url}.")

    # Open native macOS Safari if requested
    if args.open_safari and sys.platform == "darwin":
        print("🌐 Opening macOS Safari at http://127.0.0.1:8000...")
        subprocess.run(["open", "-a", "Safari", server_url], check=False)

    try:
        # Run Playwright UI Test Suite
        test_script = ROOT_DIR / "tests" / "ui_test_suite.py"
        cmd = [
            str(ROOT_DIR / ".venv" / "bin" / "python"),
            str(test_script),
            "--url", server_url,
            "--browser", args.browser,
        ]
        if args.headed:
            cmd.append("--headed")

        res = subprocess.run(cmd, cwd=str(ROOT_DIR))
        exit_code = res.returncode

    finally:
        if server_proc:
            print("🛑 Shutting down background test server...")
            server_proc.terminate()
            try:
                server_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                server_proc.kill()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
