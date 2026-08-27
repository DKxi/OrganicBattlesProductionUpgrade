from pathlib import Path

import pytest
from dotenv import dotenv_values

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

import app


ENV_FILE = Path(__file__).parents[1] / ".env"
SECRETS_FILE = Path(__file__).parents[1] / "secrets.toml"


def smtp_values():
    values = dotenv_values(ENV_FILE) if ENV_FILE.exists() else {}
    if values.get("SMTP_HOST"):
        return values
    if SECRETS_FILE.exists():
        with SECRETS_FILE.open("rb") as file:
            gmail = tomllib.load(file).get("gmail", {})
        return {"SMTP_HOST": gmail.get("smtp_host"), "SMTP_PORT": gmail.get("smtp_port"), "SMTP_USERNAME": gmail.get("sender"), "SMTP_PASSWORD": gmail.get("app_password"), "SMTP_FROM": gmail.get("sender")}
    return {}


def test_env_contains_smtp_settings():
    """Verify that a local .env has the values needed for SMTP delivery."""
    values = smtp_values()
    if not values:
        pytest.skip("Create .env or secrets.toml to test SMTP configuration")
    required = ("SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM")
    missing = [name for name in required if not values.get(name)]
    assert not missing, f"Missing SMTP settings in .env: {', '.join(missing)}"
    assert str(values["SMTP_PORT"]).isdigit(), "SMTP_PORT must be numeric"


def test_verification_email_uses_server_side_smtp(monkeypatch):
    """Exercise email delivery without connecting to or sending through SMTP."""
    values = smtp_values()
    if not values:
        pytest.skip("Create .env or secrets.toml to test SMTP configuration")
    if not values.get("SMTP_HOST") or not values.get("SMTP_PASSWORD"):
        pytest.skip("SMTP_HOST and SMTP_PASSWORD are required for this test")
    for name in ("SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM"):
        monkeypatch.setenv(name, str(values[name]))

    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            sent["connection"] = (host, port, timeout)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            sent["starttls"] = True

        def login(self, username, password):
            sent["login"] = (username, password)

        def send_message(self, message):
            sent["message"] = message

    monkeypatch.setattr(app.smtplib, "SMTP", FakeSMTP)
    app.send_verification_email("nkoneru2015@gmail.com", "TestPlayer", "123456")

    assert sent["connection"] == (str(values["SMTP_HOST"]), int(values["SMTP_PORT"]), 20)
    assert sent["starttls"] is True
    assert sent["login"][0] == str(values["SMTP_USERNAME"])
    assert sent["login"][1] == str(values["SMTP_PASSWORD"]).replace(" ", "")
    assert sent["message"]["To"] == "nkoneru2015@gmail.com"
    assert "123456" in sent["message"].get_content()
