import hashlib
import hmac
import secrets
from typing import Tuple

PBKDF2_ITERATIONS = 310_000


def hash_password(password: str, salt: bytes = None) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 310k iterations."""
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored salt$digest."""
    try:
        salt_hex, expected_digest_hex = stored_hash.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        expected_digest = bytes.fromhex(expected_digest_hex)
        computed_digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
        return hmac.compare_digest(computed_digest, expected_digest)
    except Exception:
        return False


def code_hash(code: str) -> str:
    """Deterministic SHA-256 hash for codes and bearer tokens."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def generate_verification_code() -> str:
    """Generate 6-digit numeric verification code."""
    return f"{secrets.randbelow(1_000_000):06d}"


def generate_session_token() -> str:
    """Generate cryptographically secure session token."""
    return secrets.token_urlsafe(32)
