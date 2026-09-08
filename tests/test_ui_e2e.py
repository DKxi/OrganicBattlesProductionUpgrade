"""
Pytest integration for End-to-End Playwright WebKit / Safari UI Test Suite.
"""

import pytest
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


@pytest.mark.e2e
def test_ui_suite_e2e():
    """Run full UI test suite in WebKit engine (Safari engine)."""
    script_path = ROOT_DIR / "scripts" / "run_ui_tests.py"
    res = subprocess.run(
        [str(ROOT_DIR / ".venv" / "bin" / "python"), str(script_path), "--browser", "webkit", "--skip-safari"],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)
    assert res.returncode == 0, f"UI test suite failed with return code {res.returncode}:\n{res.stdout}\n{res.stderr}"
