import os
from typing import Optional


def resolve_content_source(user_content_source: Optional[str] = None) -> str:
    """
    Priority Resolution Order:
    1. .env / process env (GAME_CONTENT_SOURCE)
    2. user_content_source from database ('app' or 'json')
    3. default "json" mode (Klein 5e chapters with all bosses and questions)
    """
    env_override = os.getenv("GAME_CONTENT_SOURCE")
    if env_override and env_override.strip():
        val = env_override.strip().lower()
        if val in ("app", "json"):
            return val

    if user_content_source and user_content_source.strip():
        val = user_content_source.strip().lower()
        if val in ("app", "json"):
            return val

    return "json"
