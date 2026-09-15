"""
Unit and Integration Tests for Gunicorn + Uvicorn Worker ("GUvicorn") Deployment.

Validates that:
1. gunicorn.conf.py parses correctly with compliant production defaults.
2. Environment variables (WEB_CONCURRENCY, PORT, HOST, TIMEOUT) properly override settings.
3. app.main:app satisfies ASGI application interface specifications for Gunicorn.
4. A multi-worker Gunicorn server can launch, serve traffic via Uvicorn workers, and terminate cleanly.
"""

import os
import sys
import time
import socket
import importlib.util
import subprocess
import urllib.request
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent


def _load_gunicorn_conf(env_overrides=None):
    """Dynamically load gunicorn.conf.py under controlled environment conditions."""
    conf_path = ROOT_DIR / "gunicorn.conf.py"
    assert conf_path.exists(), "gunicorn.conf.py does not exist at repository root"

    orig_env = os.environ.copy()
    if env_overrides:
        os.environ.update(env_overrides)

    try:
        spec = importlib.util.spec_from_file_location("gunicorn_conf", str(conf_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        os.environ.clear()
        os.environ.update(orig_env)


def _find_free_port() -> int:
    """Find an available local TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_gunicorn_conf_defaults():
    """Verify that gunicorn.conf.py provides production-grade defaults."""
    conf = _load_gunicorn_conf()

    assert conf.worker_class == "uvicorn.workers.UvicornWorker"
    assert conf.bind.endswith("8000")
    assert conf.timeout >= 60
    assert conf.graceful_timeout >= 15
    assert conf.keepalive >= 2
    assert conf.max_requests >= 500
    assert conf.max_requests_jitter >= 50
    assert conf.accesslog == "-"
    assert conf.errorlog == "-"
    assert callable(conf.post_fork)
    assert callable(conf.worker_exit)


def test_gunicorn_conf_environment_overrides():
    """Verify environment variables dynamically override Gunicorn settings."""
    overrides = {
        "HOST": "127.0.0.1",
        "PORT": "8888",
        "WEB_CONCURRENCY": "3",
        "GUNICORN_TIMEOUT": "90",
        "GUNICORN_MAX_REQUESTS": "2000",
        "GUNICORN_MAX_REQUESTS_JITTER": "150",
    }
    conf = _load_gunicorn_conf(overrides)

    assert conf.bind == "127.0.0.1:8888"
    assert conf.workers == 3
    assert conf.timeout == 90
    assert conf.max_requests == 2000
    assert conf.max_requests_jitter == 150


def test_asgi_app_target_compatibility():
    """Verify that app.main:app provides a valid ASGI interface compatible with UvicornWorker."""
    from app.main import app

    # An ASGI3 application is a callable accepting (scope, receive, send)
    assert callable(app)
    assert hasattr(app, "router")
    assert app.title == "Organic Battles V3"


@pytest.mark.e2e
def test_live_multi_worker_gunicorn_probe():
    """
    Spawns a real multi-worker Gunicorn server with 2 Uvicorn workers on an ephemeral port.
    Verifies HTTP responses for /health/live and / (index), then performs clean SIGTERM teardown.
    """
    port = _find_free_port()
    env = os.environ.copy()
    env["TESTING"] = "1"
    env["PORT"] = str(port)
    env["HOST"] = "127.0.0.1"
    env["WEB_CONCURRENCY"] = "2"

    gunicorn_bin = str(ROOT_DIR / ".venv" / "bin" / "gunicorn")
    cmd = [
        gunicorn_bin,
        "-c", "gunicorn.conf.py",
        "app.main:app",
    ]

    proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    base_url = f"http://127.0.0.1:{port}"
    server_ready = False
    start_time = time.time()

    # Wait up to 15s for multi-worker Gunicorn to bind and become healthy
    try:
        while time.time() - start_time < 15.0:
            try:
                with urllib.request.urlopen(f"{base_url}/health/live", timeout=1.0) as resp:
                    if resp.status == 200:
                        server_ready = True
                        break
            except Exception:
                time.sleep(0.3)

        assert server_ready, f"Gunicorn multi-worker server failed to start on {base_url}"

        # 1. Verify health probe response
        with urllib.request.urlopen(f"{base_url}/health/live", timeout=2.0) as resp:
            assert resp.status == 200
            data = resp.read().decode("utf-8")
            assert "alive" in data

        # 2. Verify root page renders
        with urllib.request.urlopen(f"{base_url}/", timeout=2.0) as resp:
            assert resp.status == 200
            html = resp.read().decode("utf-8")
            assert "ORGANIC" in html
            assert "BATTLES" in html

    finally:
        # Graceful shutdown
        proc.terminate()
        try:
            proc.wait(timeout=4.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2.0)
