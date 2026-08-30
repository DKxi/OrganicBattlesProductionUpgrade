import sys
import random
import time
import uuid
import hashlib
import hmac
import os
import re
import secrets
import smtplib
import sqlite3
import json
import logging
try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 and earlier
    import tomli as tomllib
from email.message import EmailMessage
from pathlib import Path
from typing import Literal, Union, Optional

from fastapi import Cookie, FastAPI, Header, HTTPException, Response, Depends, BackgroundTasks, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from sqlalchemy.orm import Session as DBSession

from database import get_db, engine, Base
from models import User, VerificationCode, AuthSession, GameSession

ROOT = Path(__file__).parent
logger = logging.getLogger("organic_battles.assets")

# Load local secrets before reading any environment-backed configuration.
# Existing process environment variables take precedence over values in .env.
if (ROOT / ".env").is_file():
    load_dotenv(ROOT / ".env")
elif (ROOT / "env").is_file():
    load_dotenv(ROOT / "env")

SECRETS_PATH = ROOT / "secrets.toml"
try:
    with SECRETS_PATH.open("rb") as secrets_file:
        SECRETS = tomllib.load(secrets_file)
except FileNotFoundError:
    SECRETS = {}


def config_value(environment_name: str, *secret_path: str, default=None):
    """Read process environment first, then the matching secrets.toml value."""
    value = os.getenv(environment_name)
    if value is not None:
        return value
    if not secret_path:
        return default
    current = SECRETS
    for part in secret_path:
        if not isinstance(current, dict):
            return default
        current = current.get(part)
    return current if current is not None else default


CODE_TTL_SECONDS = int(os.getenv("VERIFICATION_CODE_TTL_SECONDS", "900"))
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,24}$")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def ensure_db_schema():
    """Automatically create database tables and ensure new columns are added."""
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        from sqlalchemy import text
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN content_source VARCHAR"))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE game_sessions ADD COLUMN content_source VARCHAR"))
            conn.commit()
        except Exception:
            pass


ensure_db_schema()


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000)
    return f"pbkdf2_sha256$310000${salt.hex()}${digest.hex()}"


def check_password(password: str, encoded: str) -> bool:
    try:
        _, rounds, salt, expected = encoded.split("$", 3)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def code_hash(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def send_verification_email(email: str, username: str, code: str):
    host = config_value("SMTP_HOST", "gmail", "smtp_host")
    if not host:
        # Local development mode: the code stays server-side and is never returned by an API.
        print(f"[Organic Battles] verification code for {email}: {code}")
        return
    try:
        message = EmailMessage()
        message["Subject"] = "Your Organic Battles confirmation code"
        sender = config_value("SMTP_FROM", "gmail", "sender", default=config_value("SMTP_USERNAME", "gmail", "sender", default="no-reply@example.com"))
        message["From"] = sender
        message["To"] = email
        message.set_content(f"Hi {username},\n\nYour Organic Battles confirmation code is: {code}\nIt expires in 15 minutes.\n\nIf you did not create this account, you can ignore this message.")
        port = int(config_value("SMTP_PORT", "gmail", "smtp_port", default="587"))
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.starttls()
            username = config_value("SMTP_USERNAME", "gmail", "sender")
            password = config_value("SMTP_PASSWORD", "gmail", "app_password")
            if username and password:
                # Gmail displays app passwords with spaces; SMTP expects the compact value.
                server.login(username, str(password).replace(" ", ""))
            server.send_message(message)
    except Exception as error:
        logger.error(f"[Organic Battles] Failed to send verification email to {email}: {type(error).__name__}: {error}")


def row_to_dict(user):
    if not user:
        return None
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "password_hash": user.password_hash,
        "verified": user.verified,
        "content_source": getattr(user, "content_source", None),
        "avatar_json": user.avatar_json,
        "progress_json": user.progress_json,
        "created_at": user.created_at,
    }


def auth_user(authorization: Optional[str], session_token: Optional[str], db: DBSession):
    raw = session_token
    if authorization and authorization.lower().startswith("bearer "):
        raw = authorization[7:].strip()
    if not raw:
        raise HTTPException(401, "Authentication required")
    user = db.query(User).join(AuthSession).filter(
        AuthSession.token_hash == code_hash(raw),
        AuthSession.expires_at > int(time.time())
    ).first()
    if not user:
        raise HTTPException(401, "Session expired or invalid")
    return row_to_dict(user)


def issue_auth_session(user_id: str, db: DBSession) -> str:
    token = secrets.token_urlsafe(40)
    now = int(time.time())
    session = AuthSession(
        token_hash=code_hash(token),
        user_id=user_id,
        expires_at=now + 60 * 60 * 24 * 30,
        created_at=now
    )
    db.add(session)
    db.commit()
    return token


class SignupRequest(BaseModel):
    email: str
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class VerifyRequest(BaseModel):
    code: str


class ModeSwitchRequest(BaseModel):
    mode: Optional[str] = None
    content_source: Optional[str] = None


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminUserConfigRequest(BaseModel):
    content_source: Optional[str] = None



def public_user(row):
    saved_avatar = None
    if row.get("avatar_json"):
        try:
            saved_avatar = json.loads(row["avatar_json"])
        except (TypeError, json.JSONDecodeError):
            saved_avatar = None
    content_src = row.get("content_source")
    return {
        "id": row["id"],
        "email": row["email"],
        "username": row["username"],
        "verified": bool(row["verified"]),
        "avatar": saved_avatar,
        "content_source": content_src,
        "effective_mode": resolve_content_source(content_src),
    }


def save_game_progress(game: "Session", db: DBSession):
    from session_repository import save_session
    save_session(db, game)


BUILTIN_SPELLS = {
    "fire-spark": ("Fire Spark", "basic", 20, 1.5, "A quick flame projectile."),
    "acid-shot": ("Acid Shot", "basic", 20, 1.5, "A corrosive green arc."),
    "carbon-punch": ("Carbon Punch", "basic", 20, 1.5, "A hexagonal carbon shockwave."),
    "resonance-burst": ("Resonance Burst", "medium", 30, 5, "Curved arrows converge into an orb."),
    "nucleophile-strike": ("Nucleophile Strike", "medium", 30, 5, "A lone-pair spiral seeks its target."),
    "chiral-slash": ("Chiral Slash", "medium", 30, 5, "Mirrored R/S blades cross the arena."),
    "mechanism-storm": ("Mechanism Storm", "strong", 45, 10, "A vortex of mechanisms and intermediates."),
    "stereochemical-rift": ("Stereochemical Rift", "strong", 45, 10, "A mirrored molecular portal tears open."),
    "spectral-obliteration": ("Spectral Obliteration", "strong", 45, 10, "IR and NMR energy become a beam."),
}

BUILTIN_CHAPTERS = [
    {"id": 1, "name": "Foundations of Organic Chemistry", "subtitle": "The Luminous Laboratory", "color": "#27d9cb", "bosses": [
        ("hybridization-goblin", "Hybridization Goblin", 120, 15, "Mini-Boss", "Orbitals spin around a goblin's tetrahedral staff."),
        ("functional-group-golem", "Functional Group Golem", 180, 15, "Mini-Boss", "Stone plates glow with reactive functional groups."),
        ("resonance-wraith", "Resonance Wraith", 250, 15, "Mini-Boss", "A spectral form shifts between resonance structures."),
        ("resonance-dragon", "Resonance Dragon", 450, 20, "MAJOR BOSS", "A massive dragon breathes glowing curved arrows."),
    ]},
    {"id": 2, "name": "Reaction Mechanisms", "subtitle": "The Kinetic Crucible", "color": "#9a7cff", "bosses": [
        ("sn1-knight", "SN1 Knight", 260, 30, "Mini-Boss", "A carbocation shield burns with unstable charge."),
        ("sn2-assassin", "SN2 Assassin", 320, 30, "Mini-Boss", "A backside attack flashes from the shadows."),
        ("e1-sorcerer", "E1 Sorcerer", 390, 30, "Mini-Boss", "Elimination glyphs orbit a reactive staff."),
        ("carbocation-shapeshifter", "Carbocation Shapeshifter", 470, 30, "Mini-Boss", "Its molecular skeleton rearranges in real time."),
        ("mechanism-titan", "Mechanism Titan", 600, 30, "MAJOR BOSS", "A giant of transition states and curved arrows."),
    ]},
    {"id": 3, "name": "Stereochemistry & Spectroscopy", "subtitle": "The Mirror Spectrum", "color": "#e34dff", "bosses": [
        ("chiral-chimera", "Chiral Chimera", 400, 45, "Mini-Boss", "Two mirrored heads argue across a stereocenter."),
        ("enantiomer-elf", "Enantiomer Elf", 480, 45, "Mini-Boss", "Left and right mirrored selves move as one."),
        ("ir-specter", "IR Specter", 550, 45, "Mini-Boss", "Spectral waves ripple through a translucent form."),
        ("nmr-oracle", "NMR Oracle", 650, 45, "Mini-Boss", "Magnetic rings reveal hidden chemical shifts."),
        ("stereochemistry-overlord", "Stereochemistry Overlord", 890, 45, "MAJOR BOSS", "An R/S split mask channels IR and NMR energy."),
    ]},
]

QUESTIONS = [
    ("What does sp3 hybridization describe?", ["Four equivalent hybrid orbitals", "A carbonyl resonance form", "A leaving group", "An IR absorption"], "Four equivalent hybrid orbitals"),
    ("A nucleophile is best described as…", ["An electron-pair donor", "An electron-pair acceptor", "A proton source", "A spectral peak"], "An electron-pair donor"),
    ("SN2 reactions are characterized by…", ["Backside attack and inversion", "A carbocation intermediate", "Two-step elimination", "Aromatic resonance only"], "Backside attack and inversion"),
    ("Enantiomers are molecules that are…", ["Non-superimposable mirror images", "Identical constitutional isomers", "Always achiral", "Different conformers only"], "Non-superimposable mirror images"),
    ("IR spectroscopy is especially useful for identifying…", ["Functional-group vibrations", "Molecular mass only", "Reaction yield", "Optical rotation alone"], "Functional-group vibrations"),
    ("In a resonance hybrid, the real molecule has…", ["Electron density spread across contributors", "Only one frozen structure", "No pi electrons", "Only single bonds"], "Electron density spread across contributors"),
]

EXPLANATIONS = {
    "What does sp3 hybridization describe?": "sp3 hybridization mixes one s orbital with three p orbitals to create four equivalent hybrid orbitals. Look for the answer describing four equivalent orbitals, not a resonance form or spectroscopy signal.",
    "A nucleophile is best described as…": "A nucleophile is electron-rich and donates a pair of electrons to form a bond. The key clue is donor: an electron-pair acceptor is an electrophile.",
    "A nucleophile is best described as...": "A nucleophile is electron-rich and donates a pair of electrons to form a bond. The key clue is donor: an electron-pair acceptor is an electrophile.",
    "SN2 reactions are characterized by…": "SN2 is a one-step backside attack. The incoming nucleophile attacks as the leaving group departs, causing inversion of configuration.",
    "SN2 reactions are characterized by...": "SN2 is a one-step backside attack. The incoming nucleophile attacks as the leaving group departs, causing inversion of configuration.",
    "Enantiomers are molecules that are…": "Enantiomers are non-superimposable mirror images. They have the same connectivity but differ in three-dimensional arrangement at their stereocenters.",
    "Enantiomers are molecules that are...": "Enantiomers are non-superimposable mirror images. They have the same connectivity but differ in three-dimensional arrangement at their stereocenters.",
    "IR spectroscopy is especially useful for identifying…": "IR spectroscopy measures bond vibrations, so it is especially useful for recognizing functional groups. It does not directly provide molecular mass or reaction yield.",
    "IR spectroscopy is especially useful for identifying...": "IR spectroscopy measures bond vibrations, so it is especially useful for recognizing functional groups. It does not directly provide molecular mass or reaction yield.",
    "In a resonance hybrid, the real molecule has…": "A resonance hybrid is the single real structure represented by multiple contributors. Electron density is delocalized across the contributing structures rather than frozen in only one of them.",
    "In a resonance hybrid, the real molecule has...": "A resonance hybrid is the single real structure represented by multiple contributors. Electron density is delocalized across the contributing structures rather than frozen in only one of them.",
}

JSON_SPELL_IDS_BY_RANK = ("fire-spark", "resonance-burst", "mechanism-storm")


def json_available_spells(values):
    """Map the JSON spell damage row to one concrete spell per listed value."""
    return {spell_id: int(values[index]) for index, spell_id in enumerate(JSON_SPELL_IDS_BY_RANK) if index < len(values)}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


APP_DATA: dict = {}
JSON_DATA: dict = {}


def init_app_content():
    global APP_DATA
    boss_assets = {file.stem: file.name for file in (ROOT / "bosses").glob("*.png")}
    app_chapters = [
        {**chapter, "bosses": [(*boss, boss_assets.get(boss[0])) for boss in chapter["bosses"]]}
        for chapter in BUILTIN_CHAPTERS
    ]
    app_question_bank_by_chapter = {chapter_id: QUESTIONS for chapter_id in range(1, len(app_chapters) + 1)}
    app_question_boss_bank = {}
    for ch in app_chapters:
        for boss in ch["bosses"]:
            app_question_boss_bank[(ch["id"], boss[0])] = QUESTIONS

    APP_DATA = {
        "chapters": app_chapters,
        "questions": QUESTIONS,
        "question_bank_by_chapter": app_question_bank_by_chapter,
        "question_boss_bank": app_question_boss_bank,
        "boss_spell_values": {},
        "explanations": dict(EXPLANATIONS),
        "boss_images": {},
        "spell_values": {},
        "spells": dict(BUILTIN_SPELLS),
    }


def init_json_content():
    global JSON_DATA
    manifest_path = ROOT / "data" / "manifest.json"
    if not manifest_path.is_file():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    chapters = []
    question_bank = {}
    question_boss_bank = {}
    boss_spell_values = {}
    explanations = {}
    boss_images = {}
    spell_values = {}
    reported_missing_boss_images = set()
    spell_damage = {}
    for entry in manifest.get("chapters", []):
        chapter_file = ROOT / "data" / entry["file"]
        if not chapter_file.is_file():
            continue
        chapter_data = json.loads(chapter_file.read_text(encoding="utf-8"))
        chapter_id = int(chapter_data["chapter"])
        questions = []
        boss_groups = {}
        for item in chapter_data.get("questions", []):
            choices = [option["text"] for option in item.get("options", [])]
            prompt = item.get("question", "")
            correct = item.get("correct_answer", choices[0] if choices else "")
            questions.append((prompt, choices, correct))
            explanations[prompt] = item.get("explanation", "Review the chemistry concept and compare each answer carefully.")
            boss_image = (item.get("images") or [None])[0]
            if boss_image:
                boss_images[prompt] = boss_image
            spell_values[prompt] = [int(value) for value in item.get("spells", [])]
            for damage in item.get("spells", []):
                spell_damage[int(damage)] = int(damage)
            boss_name = item.get("boss") or chapter_data.get("assigned_boss") or entry.get("boss", "Organic Chemistry Boss")
            if not boss_image:
                missing_key = (boss_name, "<no filename>")
                if missing_key not in reported_missing_boss_images:
                    logger.warning("Missing boss image: %s (question %s has no image filename)", boss_name, item.get("id", prompt[:40]))
                    reported_missing_boss_images.add(missing_key)
            elif not (ROOT / "bosses" / boss_image).is_file():
                missing_key = (boss_name, boss_image)
                if missing_key not in reported_missing_boss_images:
                    logger.warning("Missing boss image: %s (question %s expects %s)", boss_name, item.get("id", prompt[:40]), ROOT / "bosses" / boss_image)
                    reported_missing_boss_images.add(missing_key)
            boss_groups.setdefault(boss_name, item)
            question_boss_bank.setdefault((chapter_id, _slug(boss_name)), []).append((prompt, choices, correct))
            boss_spell_values.setdefault((chapter_id, _slug(boss_name)), [int(value) for value in item.get("spells", [])])
        question_bank[chapter_id] = questions
        bosses = []
        for index, (boss_name, sample) in enumerate(boss_groups.items()):
            boss_id = _slug(boss_name)
            image = (sample.get("images") or [None])[0]
            health = max([int(value) for item in chapter_data.get("questions", []) if (item.get("boss") or chapter_data.get("assigned_boss") or entry.get("boss", "Organic Chemistry Boss")) == boss_name for value in item.get("health", [100])] or [100])
            bosses.append((boss_id, boss_name, health, 15, "MAJOR BOSS" if index == len(boss_groups) - 1 else "Mini-Boss", f"{chapter_data.get('chapter_title', '')} // {sample.get('topic', 'Organic chemistry')}", image))
        chapters.append({"id": chapter_id, "name": chapter_data.get("chapter_title", entry.get("title", f"Chapter {chapter_id}")), "subtitle": "The JSON Research Archive", "color": ["#27d9cb", "#9a7cff", "#e34dff", "#ff9f5a"][((chapter_id - 1) % 4)], "bosses": bosses})

    json_spells = dict(BUILTIN_SPELLS)
    if spell_damage:
        json_spells = {spell_id: (name, kind, spell_damage.get(damage, damage), cooldown, description) for spell_id, (name, kind, damage, cooldown, description) in json_spells.items()}

    JSON_DATA = {
        "chapters": chapters,
        "questions": [q for q_list in question_bank.values() for q in q_list],
        "question_bank_by_chapter": question_bank,
        "question_boss_bank": question_boss_bank,
        "boss_spell_values": boss_spell_values,
        "explanations": explanations,
        "boss_images": boss_images,
        "spell_values": spell_values,
        "spells": json_spells,
        "json_spell_damage": spell_damage
    }


init_app_content()
init_json_content()


def resolve_content_source(user_content_source: Optional[str] = None) -> str:
    """
    Resolve effective content source according to priority rules:
    1. Priority 1: Environment variable (GAME_CONTENT_SOURCE) / .env has highest priority.
    2. Priority 2: User database setting (content_source column on User).
    3. Priority 3: Default mode is 'app'.
    """
    env_source = os.getenv("GAME_CONTENT_SOURCE")
    if env_source and env_source.strip():
        val = env_source.strip().lower()
        if val in ("app", "json"):
            return val
    if user_content_source and user_content_source.strip():
        val = user_content_source.strip().lower()
        if val in ("app", "json"):
            return val
    return "app"


def get_content_bundle(mode: str) -> dict:
    """Return the content bundle for the resolved mode."""
    if mode == "json" and JSON_DATA.get("chapters"):
        return JSON_DATA
    return APP_DATA


# Global aliases for backward compatibility and test introspection
def sync_global_content_views():
    global CHAPTERS, QUESTIONS, QUESTION_BANK_BY_CHAPTER, QUESTION_BANK_BY_BOSS, BOSS_SPELL_VALUES, QUESTION_EXPLANATIONS, QUESTION_BOSS_IMAGES, QUESTION_SPELL_VALUES, SPELLS, GAME_CONTENT_SOURCE
    GAME_CONTENT_SOURCE = resolve_content_source()
    bundle = get_content_bundle(GAME_CONTENT_SOURCE)
    CHAPTERS = bundle["chapters"]
    QUESTIONS = bundle["questions"]
    QUESTION_BANK_BY_CHAPTER = bundle["question_bank_by_chapter"]
    QUESTION_BANK_BY_BOSS = bundle["question_boss_bank"]
    BOSS_SPELL_VALUES = bundle.get("boss_spell_values", {})
    QUESTION_EXPLANATIONS = bundle.get("explanations", {})
    QUESTION_BOSS_IMAGES = bundle.get("boss_images", {})
    QUESTION_SPELL_VALUES = bundle.get("spell_values", {})
    SPELLS = bundle["spells"]


sync_global_content_views()


PLAYER_AVATAR_ASSETS = {
    "organic-apprentice": ("Organic Apprentice", "organic-apprentice.png"),
    "reaction-mage": ("Reaction Mage", "reaction-mage.png"),
    "player-carbon-trailblazer": ("Player Carbon Trailblazer", "player-carbon-trailblazer.png"),
    "player-catalysis-adept": ("Player Catalysis Adept", "player-catalysis-adept.png"),
    "player-compound-artificer": ("Player Compound Artificer", "player-compound-artificer.png"),
    "player-molecular-analyst": ("Player Molecular Analyst", "player-molecular-analyst.png"),
    "player-research-alchemist": ("Player Research Alchemist", "player-research-alchemist.png"),
}


def validate_asset_files():
    """Write actionable startup warnings for missing player/boss artwork."""
    player_dirs = (ROOT / "avatars", ROOT / "static" / "assets" / "avatars")
    boss_dirs = (ROOT / "bosses", ROOT / "static" / "assets" / "bosses")
    for name, filename in PLAYER_AVATAR_ASSETS.values():
        for directory in player_dirs:
            if not (directory / filename).is_file():
                logger.warning("Missing player image: %s (%s)", name, directory / filename)
    for chapter in CHAPTERS:
        for boss in chapter["bosses"]:
            filename = boss[6] if len(boss) > 6 else None
            if not filename:
                logger.warning("Missing boss image: %s (chapter %s has no image filename)", boss[1], chapter["id"])
                continue
            for directory in boss_dirs:
                if not (directory / filename).is_file():
                    logger.warning("Missing boss image: %s (%s)", boss[1], directory / filename)


validate_asset_files()

PLAYER_AVATAR_IDS = {
    "organic-apprentice",
    "reaction-mage",
    "player-carbon-trailblazer",
    "player-catalysis-adept",
    "player-compound-artificer",
    "player-molecular-analyst",
    "player-research-alchemist",
}

class Avatar(BaseModel):
    character: str = "organic-apprentice"
    body: str = "arc"
    skin: str = "warm"
    hair: str = "nebula"
    outfit: str = "coat"
    accessory: str = "goggles"
    aura: str = "teal"
    config: dict = Field(default_factory=dict)

class SpellRequest(BaseModel):
    spell_id: str

class AnswerRequest(BaseModel):
    answer: str

class Session:
    def __init__(self, user_id: str, username: str, content_source: Optional[str] = None):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.username = username
        self.content_source = content_source
        self.avatar: Optional[Avatar] = None
        self.finalized = False
        self.chapter = 1
        self.boss_index = 0
        self.player_hp = 150
        self.player_max_hp = 150
        self.boss_hp = 0
        self.active_question = None
        self.active_spell = None
        self.turn_id = None
        self.last_turn = 0.0
        self.cooldowns: dict[str, float] = {}
        self.log = ["Welcome, alchemist. Choose a spell to begin."]
        self.completed: set[str] = set()
        self.rewards: list[str] = []
        self.question_cursors: dict[tuple[int, str], int] = {}

    @property
    def mode(self) -> str:
        return resolve_content_source(self.content_source)

    @property
    def content(self) -> dict:
        return get_content_bundle(self.mode)

    def current_boss(self):
        chapters = self.content["chapters"]
        ch_index = max(0, min(self.chapter - 1, len(chapters) - 1))
        bosses = chapters[ch_index]["bosses"]
        b_index = max(0, min(self.boss_index, len(bosses) - 1))
        return bosses[b_index]

    def prime_json_question(self):
        boss_key = (self.chapter, self.current_boss()[0])
        question_boss_bank = self.content.get("question_boss_bank", {})
        questions = question_boss_bank.get(boss_key, [])
        if not questions:
            return
        cursor = self.question_cursors.get(boss_key, 0)
        q = questions[cursor % len(questions)]
        self.question_cursors[boss_key] = cursor + 1
        choices = q[1][:]
        random.shuffle(choices)
        self.active_question = (q[0], choices, q[2])
        self.active_spell = None

    def state(self):
        bundle = self.content
        chapters = bundle["chapters"]
        ch_index = max(0, min(self.chapter - 1, len(chapters) - 1))
        ch_data = chapters[ch_index]
        boss = self.current_boss()
        if not self.boss_hp:
            self.boss_hp = boss[2]
        
        boss_images = bundle.get("boss_images", {})
        boss_image = boss_images.get(self.active_question[0]) if self.active_question else None
        boss_image = boss_image or (boss[6] if len(boss) > 6 else None)
        
        boss_spell_values = bundle.get("boss_spell_values", {}).get((self.chapter, boss[0]), [])
        question_spell_values = bundle.get("spell_values", {}).get(self.active_question[0], boss_spell_values) if self.active_question else boss_spell_values
        question_spell_damage = json_available_spells(question_spell_values) if (self.mode == "json" and question_spell_values) else {}
        
        question = None
        if self.active_question:
            question = {"prompt": self.active_question[0], "choices": self.active_question[1]}

        return {
            "session_id": self.id,
            "username": self.username,
            "mode": self.mode,
            "content_source": self.content_source,
            "avatar": self.avatar.model_dump() if self.avatar else None,
            "finalized": self.finalized,
            "chapter": self.chapter,
            "chapter_name": ch_data["name"],
            "chapter_subtitle": ch_data["subtitle"],
            "chapter_color": ch_data["color"],
            "boss": {
                "id": boss[0],
                "name": boss[1],
                "max_hp": boss[2],
                "hp": self.boss_hp,
                "damage": boss[3],
                "kind": boss[4],
                "lore": boss[5],
                "image": boss_image
            },
            "player": {"hp": self.player_hp, "max_hp": self.player_max_hp},
            "question": question,
            "spell_damage": question_spell_damage,
            "active_spell": self.active_spell,
            "cooldowns": {key: max(0, round(value - time.time(), 1)) for key, value in self.cooldowns.items()},
            "log": self.log[-5:],
            "completed": list(self.completed),
            "rewards": self.rewards
        }


limiter = Limiter(key_func=get_remote_address, enabled="pytest" not in sys.modules)
app = FastAPI(title="Organic Battles V2")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/health/live")
def health_live():
    return {"status": "alive"}


@app.get("/health/ready")
def health_ready(db: DBSession = Depends(get_db)):
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as error:
        logger.error(f"[Organic Battles] Database healthcheck failed: {error}")
        raise HTTPException(status_code=503, detail="Database connection failed")


@app.post("/api/auth/signup")
@limiter.limit("5/minute")
def signup(request: Request, signup_data: SignupRequest, background_tasks: BackgroundTasks, db: DBSession = Depends(get_db)):
    email = signup_data.email.strip().lower()
    username = signup_data.username.strip()
    if not EMAIL_RE.fullmatch(email):
        raise HTTPException(422, "Enter a valid email address")
    if not USERNAME_RE.fullmatch(username):
        raise HTTPException(422, "Username must be 3-24 characters using letters, numbers, or underscores")
    if len(signup_data.password) < 8:
        raise HTTPException(422, "Password must be at least 8 characters")
    
    existing_username = db.query(User).filter(User.username == username).first()
    if existing_username:
        raise HTTPException(409, "Username taken, choose a different one")
    existing_email = db.query(User).filter(User.email == email).first()
    if existing_email:
        raise HTTPException(409, "An account with that email already exists")

    user_id = str(uuid.uuid4())
    now = int(time.time())
    new_user = User(
        id=user_id,
        email=email,
        username=username,
        password_hash=hash_password(signup_data.password),
        content_source=None,
        created_at=now
    )
    db.add(new_user)
    
    code = f"{secrets.randbelow(1000000):06d}"
    ver_code = VerificationCode(
        user_id=user_id,
        code_hash=code_hash(code),
        expires_at=now + CODE_TTL_SECONDS,
        created_at=now
    )
    db.add(ver_code)
    db.commit()

    background_tasks.add_task(send_verification_email, email, username, code)
    return {"status": "verification_required", "email": email, "username": username}


@app.post("/api/auth/verify")
@limiter.limit("5/minute")
def verify(request: Request, verify_data: VerifyRequest, response: Response, db: DBSession = Depends(get_db)):
    code = verify_data.code.strip()
    if not re.fullmatch(r"\d{6}", code):
        raise HTTPException(400, "Enter the 6-digit confirmation code")
    now = int(time.time())
    
    row = db.query(VerificationCode, User).join(User).filter(
        VerificationCode.code_hash == code_hash(code),
        VerificationCode.used == 0
    ).order_by(VerificationCode.created_at.desc()).first()

    if not row:
        raise HTTPException(400, "Invalid confirmation code")
    
    ver_code, user = row
    if ver_code.expires_at < now:
        raise HTTPException(400, "Confirmation code expired. Request a new code.")
    
    ver_code.used = 1
    user.verified = 1
    db.commit()

    token = issue_auth_session(user.id, db)
    response.set_cookie("session_token", token, httponly=True, samesite="lax", secure=os.getenv("COOKIE_SECURE", "0") == "1", max_age=60 * 60 * 24 * 30)
    
    return {"token": token, "user": public_user(row_to_dict(user))}


@app.post("/api/auth/resend")
@limiter.limit("5/minute")
def resend(request: Request, email: str, background_tasks: BackgroundTasks, db: DBSession = Depends(get_db)):
    email = email.strip().lower()
    now = int(time.time())
    user = db.query(User).filter(User.email == email).first()
    if not user or user.verified:
        return {"status": "sent"}
    
    code = f"{secrets.randbelow(1000000):06d}"
    db.query(VerificationCode).filter(
        VerificationCode.user_id == user.id,
        VerificationCode.used == 0
    ).update({"used": 1})

    ver_code = VerificationCode(
        user_id=user.id,
        code_hash=code_hash(code),
        expires_at=now + CODE_TTL_SECONDS,
        created_at=now
    )
    db.add(ver_code)
    db.commit()

    background_tasks.add_task(send_verification_email, user.email, user.username, code)
    return {"status": "sent"}


@app.post("/api/auth/login")
@limiter.limit("10/minute")
def login(request: Request, login_data: LoginRequest, response: Response, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.username == login_data.username.strip()).first()
    if not user or not check_password(login_data.password, user.password_hash):
        raise HTTPException(401, "Incorrect username or password")
    if not user.verified:
        raise HTTPException(403, "Please verify your email before entering the game")
    token = issue_auth_session(user.id, db)
    response.set_cookie("session_token", token, httponly=True, samesite="lax", secure=os.getenv("COOKIE_SECURE", "0") == "1", max_age=60 * 60 * 24 * 30)
    return {"token": token, "user": public_user(row_to_dict(user))}


@app.get("/api/auth/me")
def me(authorization: Optional[str] = Header(default=None), session_token: Optional[str] = Cookie(default=None), db: DBSession = Depends(get_db)):
    return {"user": public_user(auth_user(authorization, session_token, db))}


@app.post("/api/auth/logout")
def logout(response: Response, authorization: Optional[str] = Header(default=None), session_token: Optional[str] = Cookie(default=None), db: DBSession = Depends(get_db)):
    raw = session_token or (authorization[7:].strip() if authorization and authorization.lower().startswith("bearer ") else None)
    if raw:
        db.query(AuthSession).filter(AuthSession.token_hash == code_hash(raw)).delete()
        db.commit()
    response.delete_cookie("session_token")
    return {"status": "ok"}


@app.post("/api/user/mode")
@app.post("/api/user/content-source")
def set_user_mode(
    request_data: ModeSwitchRequest,
    authorization: Optional[str] = Header(default=None),
    session_token: Optional[str] = Cookie(default=None),
    db: DBSession = Depends(get_db)
):
    user_dict = auth_user(authorization, session_token, db)
    requested = request_data.mode or request_data.content_source
    if not requested:
        raise HTTPException(400, "Provide mode ('app' or 'json')")
    target_mode = requested.strip().lower()
    if target_mode not in ("app", "json"):
        raise HTTPException(400, "Content mode must be 'app' or 'json'")

    user = db.query(User).filter(User.id == user_dict["id"]).first()
    if not user:
        raise HTTPException(404, "User not found")

    user.content_source = target_mode

    # Synchronize game session if present
    game_session = db.query(GameSession).filter(GameSession.user_id == user.id).first()
    if game_session:
        game_session.content_source = target_mode
        game_session.active_question_json = None
        game_session.active_spell = None
        effective = resolve_content_source(target_mode)
        bundle = get_content_bundle(effective)
        chapters = bundle["chapters"]
        if game_session.chapter > len(chapters):
            game_session.chapter = 1
            game_session.boss_index = 0
            game_session.boss_hp = chapters[0]["bosses"][0][2]
        else:
            bosses = chapters[game_session.chapter - 1]["bosses"]
            if game_session.boss_index >= len(bosses):
                game_session.boss_index = 0
                game_session.boss_hp = bosses[0][2]
            else:
                game_session.boss_hp = bosses[game_session.boss_index][2]

    db.commit()
    db.refresh(user)

    effective_mode = resolve_content_source(user.content_source)
    from session_repository import get_or_create_session
    s = get_or_create_session(db, user.id, user.username)
    return {
        "status": "ok",
        "user_id": user.id,
        "content_source": user.content_source,
        "effective_mode": effective_mode,
        "env_override": bool(os.getenv("GAME_CONTENT_SOURCE")),
        "state": s.state()
    }


ADMIN_USERNAME = str(config_value("ADMIN_USERNAME", default="admin"))
ADMIN_PASSWORD = str(config_value("ADMIN_PASSWORD", default="admin"))
ADMIN_TOKENS: dict[str, float] = {}


def auth_admin(authorization: Optional[str] = Header(default=None), admin_token: Optional[str] = Cookie(default=None), session_token: Optional[str] = Cookie(default=None)):
    raw = None
    if authorization and authorization.lower().startswith("bearer "):
        raw = authorization[7:].strip()
    elif admin_token:
        raw = admin_token
    elif session_token:
        raw = session_token
    if not raw:
        raise HTTPException(401, "Admin authentication required")
    thash = code_hash(raw)
    now = time.time()
    expires = ADMIN_TOKENS.get(thash)
    if not expires or expires < now:
        raise HTTPException(401, "Admin session expired or invalid")
    return {"username": ADMIN_USERNAME, "is_admin": True}


@app.post("/api/admin/login")
@limiter.limit("10/minute")
def admin_login(request: Request, login_data: AdminLoginRequest, response: Response):
    if login_data.username != ADMIN_USERNAME or login_data.password != ADMIN_PASSWORD:
        raise HTTPException(401, "Incorrect admin username or password")
    token = secrets.token_urlsafe(40)
    thash = code_hash(token)
    ADMIN_TOKENS[thash] = time.time() + 60 * 60 * 24
    response.set_cookie("admin_token", token, httponly=True, samesite="lax", secure=os.getenv("COOKIE_SECURE", "0") == "1", max_age=60 * 60 * 24)
    return {"token": token, "username": ADMIN_USERNAME, "status": "ok"}


@app.get("/api/admin/status")
def admin_status(admin_info: dict = Depends(auth_admin), db: DBSession = Depends(get_db)):
    total_users = db.query(User).count()
    total_sessions = db.query(GameSession).count()
    return {
        "status": "ok",
        "admin_user": admin_info["username"],
        "env_content_source": os.getenv("GAME_CONTENT_SOURCE"),
        "default_mode": "app",
        "total_users": total_users,
        "total_sessions": total_sessions
    }


@app.get("/api/admin/users")
def admin_get_users(admin_info: dict = Depends(auth_admin), db: DBSession = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    sessions = {s.user_id: s for s in db.query(GameSession).all()}
    result = []
    for u in users:
        sess = sessions.get(u.id)
        effective = resolve_content_source(u.content_source)
        result.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "verified": bool(u.verified),
            "content_source": u.content_source,
            "effective_mode": effective,
            "chapter": sess.chapter if sess else 1,
            "boss_index": sess.boss_index if sess else 0,
            "player_hp": sess.player_hp if sess else 150,
            "created_at": u.created_at
        })
    return {"users": result, "total": len(result)}


@app.post("/api/admin/users/{user_id}/config")
def admin_update_user_config(
    user_id: str,
    config_data: AdminUserConfigRequest,
    admin_info: dict = Depends(auth_admin),
    db: DBSession = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    if config_data.content_source is not None:
        target = config_data.content_source.strip().lower() if config_data.content_source else None
        if target and target not in ("app", "json"):
            raise HTTPException(400, "content_source must be 'app', 'json', or null")
        user.content_source = target
        
        # Synchronize game session if present
        game_session = db.query(GameSession).filter(GameSession.user_id == user.id).first()
        if game_session:
            game_session.content_source = target
            game_session.active_question_json = None
            game_session.active_spell = None
            effective = resolve_content_source(target)
            bundle = get_content_bundle(effective)
            chapters = bundle["chapters"]
            if game_session.chapter > len(chapters):
                game_session.chapter = 1
                game_session.boss_index = 0
                game_session.boss_hp = chapters[0]["bosses"][0][2]
            else:
                bosses = chapters[game_session.chapter - 1]["bosses"]
                if game_session.boss_index >= len(bosses):
                    game_session.boss_index = 0
                    game_session.boss_hp = bosses[0][2]
                else:
                    game_session.boss_hp = bosses[game_session.boss_index][2]

    db.commit()
    db.refresh(user)
    
    effective = resolve_content_source(user.content_source)
    return {
        "status": "ok",
        "user_id": user.id,
        "username": user.username,
        "content_source": user.content_source,
        "effective_mode": effective,
        "env_override": bool(os.getenv("GAME_CONTENT_SOURCE")),
    }


@app.post("/api/admin/logout")
def admin_logout(response: Response, authorization: Optional[str] = Header(default=None), admin_token: Optional[str] = Cookie(default=None)):
    raw = admin_token or (authorization[7:].strip() if authorization and authorization.lower().startswith("bearer ") else None)
    if raw:
        thash = code_hash(raw)
        ADMIN_TOKENS.pop(thash, None)
    response.delete_cookie("admin_token")
    return {"status": "ok"}



def get_session(session_id: Optional[str], db: DBSession) -> Session:
    from session_repository import get_session_by_id
    if not session_id:
        raise HTTPException(404, "Session not found")
    return get_session_by_id(db, session_id)


@app.get("/")
def index():
    return FileResponse(ROOT / "templates" / "index.html")


@app.get("/favicon.ico")
def favicon():
    return FileResponse(ROOT / "static" / "favicon.svg", media_type="image/svg+xml")


@app.post("/api/game/new")
def new_game(authorization: Optional[str] = Header(default=None), session_token: Optional[str] = Cookie(default=None), db: DBSession = Depends(get_db)):
    from session_repository import get_or_create_session
    user = auth_user(authorization, session_token, db)
    s = get_or_create_session(db, user["id"], user["username"])
    return s.state()


@app.get("/api/game/state")
def game_state(session_id: str, authorization: Optional[str] = Header(default=None), session_token: Optional[str] = Cookie(default=None), db: DBSession = Depends(get_db)):
    user = auth_user(authorization, session_token, db)
    game = get_session(session_id, db)
    if game.user_id != user["id"]:
        raise HTTPException(403, "This game session belongs to another account")
    return game.state()


@app.post("/api/avatar/finalize")
def finalize_avatar(session_id: str, avatar: Avatar, authorization: Optional[str] = Header(default=None), session_token: Optional[str] = Cookie(default=None), db: DBSession = Depends(get_db)):
    user = auth_user(authorization, session_token, db)
    s = get_session(session_id, db)
    if s.user_id != user["id"]:
        raise HTTPException(403, "This game session belongs to another account")
    if avatar.character not in PLAYER_AVATAR_IDS:
        raise HTTPException(400, "Choose an available player avatar")
    if s.finalized:
        raise HTTPException(409, "Avatar already finalized")
    s.avatar, s.finalized = avatar, True
    
    db_user = db.query(User).filter(User.id == user["id"]).first()
    if db_user:
        db_user.avatar_json = avatar.model_dump_json()
    
    s.log.append("Avatar accepted. Your ORGO journey begins.")
    save_game_progress(s, db)
    return s.state()


@app.post("/api/battle/select-spell")
def select_spell(session_id: str, request: SpellRequest, authorization: Optional[str] = Header(default=None), session_token: Optional[str] = Cookie(default=None), db: DBSession = Depends(get_db)):
    user = auth_user(authorization, session_token, db)
    s = get_session(session_id, db)
    if s.user_id != user["id"]:
        raise HTTPException(403, "This game session belongs to another account")
    
    mode = s.mode
    bundle = s.content
    spells = bundle["spells"]
    if request.spell_id not in spells:
        raise HTTPException(400, "Unknown spell")
    if not s.finalized:
        raise HTTPException(400, "Finalize your avatar first")
    if s.active_question:
        raise HTTPException(409, "Answer the active question")
    
    spell = spells[request.spell_id]
    if mode == "json":
        boss_values = bundle.get("boss_spell_values", {}).get((s.chapter, s.current_boss()[0]), [])
        if boss_values and request.spell_id not in json_available_spells(boss_values):
            raise HTTPException(409, "This spell is not available for the current boss")
    if s.cooldowns.get(request.spell_id, 0) > time.time():
        raise HTTPException(409, "Spell is cooling down")
    
    if mode == "json":
        s.prime_json_question()
    s.active_spell, s.turn_id = request.spell_id, str(uuid.uuid4())
    if mode != "json":
        question_boss_bank = bundle.get("question_boss_bank", {})
        question_chapter_bank = bundle.get("question_bank_by_chapter", {})
        available_questions = question_boss_bank.get((s.chapter, s.current_boss()[0]), question_chapter_bank.get(s.chapter, bundle["questions"]))
        q = random.choice(available_questions)
        choices = q[1][:]
        random.shuffle(choices)
        s.active_question = (q[0], choices, q[2])
    save_game_progress(s, db)
    return {"turn_id": s.turn_id, **s.state()}


@app.post("/api/battle/answer")
def answer(session_id: str, request: AnswerRequest, authorization: Optional[str] = Header(default=None), session_token: Optional[str] = Cookie(default=None), db: DBSession = Depends(get_db)):
    user = auth_user(authorization, session_token, db)
    s = get_session(session_id, db)
    if s.user_id != user["id"]:
        raise HTTPException(403, "This game session belongs to another account")
    if not s.active_question or not s.active_spell:
        raise HTTPException(409, "No active question")
    
    mode = s.mode
    bundle = s.content
    spells = bundle["spells"]
    q, choices, correct = s.active_question
    spell_id = s.active_spell
    spell = spells[spell_id]
    is_correct = request.answer == correct
    spell_power = spell[2]
    if mode == "json" and bundle.get("spell_values", {}).get(q):
        spell_power = bundle["spell_values"][q][JSON_SPELL_IDS_BY_RANK.index(spell_id)]
    damage = spell_power if is_correct else 0
    s.boss_hp = max(0, s.boss_hp - damage)
    s.cooldowns[spell_id] = time.time() + spell[3]
    self_damage = 0
    if is_correct:
        boss_hit = random.random() < 0.5
        boss_damage = s.current_boss()[3] if boss_hit else 0
        s.player_hp = max(0, s.player_hp - boss_damage)
        s.log.append("Correct! " + spell[0] + " deals " + str(damage) + " damage.")
    else:
        boss_hit = False
        boss_damage = 0
        self_damage = spell_power
        s.player_hp = max(0, s.player_hp - self_damage)
        s.log.append("Fizzle. The incorrect " + spell[0] + " backfires for " + str(self_damage) + " damage. The correct answer was: " + correct)
    
    explanations = bundle.get("explanations", {})
    explanation_text = explanations.get(q, "Review the definition and compare each answer with the key chemistry idea in the question.")
    result = {
        "correct": is_correct,
        "question_prompt": q,
        "correct_answer": correct,
        "explanation": explanation_text,
        "damage": damage,
        "self_damage": self_damage,
        "boss_hit": boss_hit,
        "boss_damage": boss_damage,
        "spell_id": spell_id
    }
    defeated = s.boss_hp <= 0
    defeat = s.player_hp <= 0
    s.active_question = s.active_spell = s.turn_id = None
    chapters = bundle["chapters"]
    if defeated:
        boss_id = s.current_boss()[0]
        s.completed.add(boss_id)
        reward = {1: "Resonance Slayer", 2: "Mechanism Master", 3: "Spectral Champion"}.get(s.chapter, f"Chapter {s.chapter} Champion") if s.boss_index == len(chapters[s.chapter - 1]["bosses"]) - 1 else "Arcane Chemistry Shard"
        s.rewards.append(reward)
        s.log.append(f"{s.current_boss()[1]} defeated! Reward unlocked: {reward}.")
    if defeat:
        s.boss_hp = s.current_boss()[2]
        s.player_hp = s.player_max_hp
        s.completed.discard(s.current_boss()[0])
        s.active_question = s.active_spell = s.turn_id = None
        s.log.append("Your aura fades. Retry this boss when ready.")
    save_game_progress(s, db)
    result.update({"defeated": defeated, "defeat": defeat, **s.state()})
    return result


@app.post("/api/battle/retry")
def retry(session_id: str, authorization: Optional[str] = Header(default=None), session_token: Optional[str] = Cookie(default=None), db: DBSession = Depends(get_db)):
    user = auth_user(authorization, session_token, db)
    s = get_session(session_id, db)
    if s.user_id != user["id"]:
        raise HTTPException(403, "This game session belongs to another account")
    s.player_hp = 150
    s.boss_hp = s.current_boss()[2]
    s.active_question = s.active_spell = None
    s.log.append("Battle reset. Your completed progression remains safe.")
    save_game_progress(s, db)
    return s.state()


@app.post("/api/battle/next-turn")
def next_turn(session_id: str, authorization: Optional[str] = Header(default=None), session_token: Optional[str] = Cookie(default=None), db: DBSession = Depends(get_db)):
    user = auth_user(authorization, session_token, db)
    s = get_session(session_id, db)
    if s.user_id != user["id"]:
        raise HTTPException(403, "This game session belongs to another account")
    chapters = s.content["chapters"]
    if s.current_boss()[0] not in s.completed:
        raise HTTPException(409, "Defeat the current boss first")
    if s.boss_index < len(chapters[s.chapter - 1]["bosses"]) - 1:
        s.boss_index += 1
    elif s.chapter < len(chapters):
        s.chapter += 1
        s.boss_index = 0
    else:
        return {"victory": True, **s.state()}
    s.boss_hp = s.current_boss()[2]
    s.player_hp = 150
    s.log.append("New arena discovered: " + s.current_boss()[1])
    save_game_progress(s, db)
    return s.state()


@app.get("/api/progression")
def progression(session_id: str, authorization: Optional[str] = Header(default=None), session_token: Optional[str] = Cookie(default=None), db: DBSession = Depends(get_db)):
    user = auth_user(authorization, session_token, db)
    game = get_session(session_id, db)
    if game.user_id != user["id"]:
        raise HTTPException(403, "This game session belongs to another account")
    return game.state()
