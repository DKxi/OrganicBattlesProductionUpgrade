import time
from typing import Dict, Optional, Any

# In-memory token stores with TTL validation
ADMIN_TOKENS: Dict[str, float] = {}
RATE_LIMIT_STORE: Dict[str, list] = {}


def set_admin_token(token_hash: str, ttl_seconds: int = 86400) -> None:
    ADMIN_TOKENS[token_hash] = time.time() + ttl_seconds


def get_admin_token_expiry(token_hash: str) -> Optional[float]:
    expires = ADMIN_TOKENS.get(token_hash)
    if not expires:
        return None
    if expires < time.time():
        ADMIN_TOKENS.pop(token_hash, None)
        return None
    return expires


def revoke_admin_token(token_hash: str) -> None:
    ADMIN_TOKENS.pop(token_hash, None)
