"""
Organic Battles - Modular Backend Package
Re-exports the application instance and domain symbols.
"""
import smtplib
from app.main import app, create_app
from app.settings import settings
from app.api.deps import APP_DATA, JSON_DATA, get_content_bundle, limiter
from app.domain.content.resolver import resolve_content_source
from app.domain.content.loader import APP_CHAPTERS, APP_QUESTIONS, APP_EXPLANATIONS
from app.domain.combat.spells import SPELL_CATALOG, SPELL_LIST
from app.infrastructure.identity.crypto import code_hash, hash_password, verify_password
from app.infrastructure.messaging.smtp import send_verification_code_email as send_verification_email
from app.infrastructure.database.models import User, GameSession, AuthSession, VerificationCode
from app.infrastructure.database.engine import get_db, ensure_db_schema, engine, SessionLocal
from app.domain.progression.entities import Avatar, Session

# Legacy global content references for test fixtures
CHAPTERS = APP_DATA.chapters
QUESTIONS = APP_DATA.questions
EXPLANATIONS = APP_DATA.explanations
QUESTION_BANK_BY_CHAPTER = APP_DATA.question_bank_by_chapter
QUESTION_BANK_BY_BOSS = APP_DATA.question_bank_by_boss
SPELL_DAMAGE_BY_QUESTION = APP_DATA.spell_damage_by_question
SPELL_DAMAGE_BY_BOSS = APP_DATA.spell_damage_by_boss
BOSS_IMAGES = APP_DATA.boss_images
SPELLS = SPELL_LIST


def sync_global_content_views() -> None:
    """Synchronize global references to match current active global mode."""
    global CHAPTERS, QUESTIONS, EXPLANATIONS, QUESTION_BANK_BY_CHAPTER, QUESTION_BANK_BY_BOSS, SPELL_DAMAGE_BY_QUESTION, SPELL_DAMAGE_BY_BOSS, BOSS_IMAGES
    active_bundle = get_content_bundle(resolve_content_source())
    CHAPTERS = active_bundle.chapters
    QUESTIONS = active_bundle.questions
    EXPLANATIONS = active_bundle.explanations
    QUESTION_BANK_BY_CHAPTER = active_bundle.question_bank_by_chapter
    QUESTION_BANK_BY_BOSS = active_bundle.question_bank_by_boss
    SPELL_DAMAGE_BY_QUESTION = active_bundle.spell_damage_by_question
    SPELL_DAMAGE_BY_BOSS = active_bundle.spell_damage_by_boss
    BOSS_IMAGES = active_bundle.boss_images


sync_global_content_views()



__all__ = [
    "app",
    "create_app",
    "settings",
    "smtplib",
    "send_verification_email",
    "APP_DATA",
    "JSON_DATA",
    "CHAPTERS",
    "QUESTIONS",
    "EXPLANATIONS",
    "QUESTION_BANK_BY_CHAPTER",
    "QUESTION_BANK_BY_BOSS",
    "SPELLS",
    "SPELL_CATALOG",
    "sync_global_content_views",
    "resolve_content_source",
    "get_db",
    "code_hash",
    "hash_password",
    "verify_password",
    "User",
    "GameSession",
    "AuthSession",
    "VerificationCode",
]
