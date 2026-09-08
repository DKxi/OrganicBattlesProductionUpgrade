"""
Legacy adapter for models.py.
Re-exports declarative models from app.infrastructure.database.models.
"""
from app.infrastructure.database.models import (
    Base,
    User,
    AuthSession,
    VerificationCode,
    GameSession,
    Curriculum,
    Track,
    Question,
)

__all__ = [
    "Base",
    "User",
    "AuthSession",
    "VerificationCode",
    "GameSession",
    "Curriculum",
    "Track",
    "Question",
]

