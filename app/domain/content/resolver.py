from typing import Optional


def resolve_content_source(user_content_source: Optional[str] = None) -> str:
    """
    Questions are based on track selection.
    GAME_CONTENT_SOURCE is completely ignored.

    Priority:
    1. user_content_source from database / session (e.g. 'track:default', 'track:adv-outcomes', or track ID)
    2. Fallback to default track: "track:default"
    """
    if user_content_source and user_content_source.strip():
        val = user_content_source.strip().lower()
        if val.startswith("track:"):
            return val
        if val in ("default", "json"):
            return "track:default"
        if val.startswith("adv-") or val.startswith("found-"):
            return f"track:{val}"
        if val == "app":
            return "app"
        return f"track:{val}"

    return "track:default"

