from dataclasses import dataclass
from typing import Optional


@dataclass
class AuthToken:
    token: str
    token_hash: str
    user_id: str
    expires_at: int


@dataclass
class VerificationCodeEntity:
    id: str
    user_id: str
    code_hash: str
    expires_at: int
    used: bool
