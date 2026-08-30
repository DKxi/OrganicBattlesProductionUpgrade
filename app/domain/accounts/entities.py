from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class UserAccount:
    id: str
    email: str
    username: str
    password_hash: str
    verified: bool
    avatar_json: Optional[str]
    progress_json: Optional[str]
    content_source: Optional[str]
    created_at: int


def to_public_user(user: UserAccount, effective_mode: str) -> Dict[str, Any]:
    import json
    saved_avatar = None
    if user.avatar_json:
        try:
            saved_avatar = json.loads(user.avatar_json)
        except Exception:
            saved_avatar = None

    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "verified": bool(user.verified),
        "avatar": saved_avatar,
        "content_source": user.content_source,
        "effective_mode": effective_mode,
    }
