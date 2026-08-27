from __future__ import annotations

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
from typing import Literal

from fastapi import Cookie, FastAPI, Header, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv

ROOT = Path(__file__).parent
logger = logging.getLogger("organic_battles.assets")
# Load local secrets before reading any environment-backed configuration.
# Existing process environment variables take precedence over values in .env.
load_dotenv(ROOT / ".env")

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
    current = SECRETS
    for part in secret_path:
        if not isinstance(current, dict):
            return default
        current = current.get(part)
    return current if current is not None else default


DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(ROOT / "organic_battles.sqlite3")))
CODE_TTL_SECONDS = int(os.getenv("VERIFICATION_CODE_TTL_SECONDS", "900"))
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,24}$")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def db():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    with db() as connection:
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL, verified INTEGER NOT NULL DEFAULT 0,
            avatar_json TEXT, progress_json TEXT, created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS verification_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            code_hash TEXT NOT NULL, expires_at INTEGER NOT NULL, used INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS auth_sessions (
            token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            expires_at INTEGER NOT NULL, created_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_codes_user ON verification_codes(user_id, created_at DESC);
        """)
        try:
            connection.execute("ALTER TABLE users ADD COLUMN progress_json TEXT")
        except sqlite3.OperationalError:
            pass


init_db()


def hash_password(password: str, salt: bytes | None = None) -> str:
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


def auth_user(authorization: str | None, session_token: str | None):
    raw = session_token
    if authorization and authorization.lower().startswith("bearer "):
        raw = authorization[7:].strip()
    if not raw:
        raise HTTPException(401, "Authentication required")
    with db() as connection:
        row = connection.execute("SELECT u.* FROM auth_sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?", (code_hash(raw), int(time.time()))).fetchone()
    if not row:
        raise HTTPException(401, "Session expired or invalid")
    return row


def issue_auth_session(user_id: str) -> str:
    token = secrets.token_urlsafe(40)
    now = int(time.time())
    with db() as connection:
        connection.execute("INSERT INTO auth_sessions(token_hash,user_id,expires_at,created_at) VALUES (?,?,?,?)", (code_hash(token), user_id, now + 60 * 60 * 24 * 30, now))
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


def public_user(row):
    saved_avatar = None
    if row["avatar_json"]:
        try:
            saved_avatar = json.loads(row["avatar_json"])
        except (TypeError, json.JSONDecodeError):
            saved_avatar = None
    return {"id": row["id"], "email": row["email"], "username": row["username"], "verified": bool(row["verified"]), "avatar": saved_avatar}


def save_game_progress(game: "Session"):
    progress = {
        "chapter": game.chapter, "boss_index": game.boss_index,
        "player_hp": game.player_hp, "player_max_hp": game.player_max_hp, "boss_hp": game.boss_hp,
        "active_question": list(game.active_question) if game.active_question else None,
        "active_spell": game.active_spell, "turn_id": game.turn_id,
        "cooldowns": game.cooldowns, "log": game.log[-20:], "completed": list(game.completed), "rewards": game.rewards,
        "question_cursors": {f"{chapter}:{boss}": cursor for (chapter, boss), cursor in game.question_cursors.items()},
    }
    with db() as connection:
        connection.execute("UPDATE users SET progress_json=? WHERE id=?", (json.dumps(progress), game.user_id))


def restore_game_progress(game: "Session", progress_json: str | None):
    if not progress_json:
        return
    try:
        progress = json.loads(progress_json)
        game.chapter = max(1, min(int(progress.get("chapter", game.chapter)), len(CHAPTERS)))
        game.boss_index = max(0, min(int(progress.get("boss_index", game.boss_index)), len(CHAPTERS[game.chapter - 1]["bosses"]) - 1))
        game.player_hp = int(progress.get("player_hp", game.player_hp)); game.player_max_hp = int(progress.get("player_max_hp", game.player_max_hp)); game.boss_hp = int(progress.get("boss_hp", game.boss_hp))
        active_question = progress.get("active_question")
        game.active_question = tuple(active_question) if active_question else None
        game.active_spell = progress.get("active_spell"); game.turn_id = progress.get("turn_id")
        game.cooldowns = {str(key): float(value) for key, value in progress.get("cooldowns", {}).items()}
        game.log = progress.get("log", game.log); game.completed = set(progress.get("completed", [])); game.rewards = progress.get("rewards", [])
        game.question_cursors = {}
        for key, cursor in progress.get("question_cursors", {}).items():
            chapter, boss = key.split(":", 1); game.question_cursors[(int(chapter), boss)] = int(cursor)
    except (TypeError, ValueError, KeyError, json.JSONDecodeError) as error:
        logger.warning("Could not restore saved game progress for user %s: %s", game.user_id, error)

SPELLS = {
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

CHAPTERS = [
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
    "A nucleophile is best described asâ€¦": "A nucleophile is electron-rich and donates a pair of electrons to form a bond. The key clue is donor: an electron-pair acceptor is an electrophile.",
    "SN2 reactions are characterized byâ€¦": "SN2 is a one-step backside attack. The incoming nucleophile attacks as the leaving group departs, causing inversion of configuration.",
    "Enantiomers are molecules that areâ€¦": "Enantiomers are non-superimposable mirror images. They have the same connectivity but differ in three-dimensional arrangement at their stereocenters.",
    "IR spectroscopy is especially useful for identifyingâ€¦": "IR spectroscopy measures bond vibrations, so it is especially useful for recognizing functional groups. It does not directly provide molecular mass or reaction yield.",
    "In a resonance hybrid, the real molecule hasâ€¦": "A resonance hybrid is the single real structure represented by multiple contributors. Electron density is delocalized across the contributing structures rather than frozen in only one of them.",
}

# Content source switch. Set GAME_CONTENT_SOURCE=json (or change the default
# below) to load the complete chapter/question bank from data/*.json.
GAME_CONTENT_SOURCE = os.getenv("GAME_CONTENT_SOURCE", "app").strip().lower()
QUESTION_BANK_BY_CHAPTER = {chapter_id: QUESTIONS for chapter_id in range(1, len(CHAPTERS) + 1)}
QUESTION_BANK_BY_BOSS = {}
BOSS_SPELL_VALUES = {}
QUESTION_EXPLANATIONS = dict(EXPLANATIONS)
QUESTION_BOSS_IMAGES = {}
QUESTION_SPELL_VALUES = {}
JSON_SPELL_DAMAGE: dict[int, int] = {}
JSON_SPELL_IDS_BY_RANK = ("fire-spark", "resonance-burst", "mechanism-storm")


def json_available_spells(values):
    """Map the JSON spell damage row to one concrete spell per listed value."""
    return {spell_id: int(values[index]) for index, spell_id in enumerate(JSON_SPELL_IDS_BY_RANK) if index < len(values)}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def load_json_content():
    """Load chapters, boss metadata/images, questions, explanations and spell power."""
    global CHAPTERS, QUESTION_BANK_BY_CHAPTER, QUESTION_BANK_BY_BOSS, BOSS_SPELL_VALUES, QUESTION_EXPLANATIONS, QUESTION_BOSS_IMAGES, QUESTION_SPELL_VALUES, SPELLS
    manifest = json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))
    chapters = []
    question_bank = {}
    question_boss_bank = {}
    boss_spell_values = {}
    explanations = {}
    boss_images = {}
    spell_values = {}
    reported_missing_boss_images = set()
    spell_damage = {}
    for entry in manifest["chapters"]:
        chapter_data = json.loads((ROOT / "data" / entry["file"]).read_text(encoding="utf-8"))
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
    if not chapters or any(not chapter["bosses"] for chapter in chapters):
        raise RuntimeError("JSON content source contains a chapter without bosses")
    CHAPTERS = chapters
    QUESTION_BANK_BY_CHAPTER = question_bank
    QUESTION_BANK_BY_BOSS = question_boss_bank
    BOSS_SPELL_VALUES = boss_spell_values
    QUESTION_EXPLANATIONS = explanations
    QUESTION_BOSS_IMAGES = boss_images
    QUESTION_SPELL_VALUES = spell_values
    JSON_SPELL_DAMAGE = spell_damage
    if JSON_SPELL_DAMAGE:
        SPELLS = {spell_id: (name, kind, JSON_SPELL_DAMAGE.get(damage, damage), cooldown, description) for spell_id, (name, kind, damage, cooldown, description) in SPELLS.items()}


if GAME_CONTENT_SOURCE == "json":
    load_json_content()
elif GAME_CONTENT_SOURCE != "app":
    raise RuntimeError("GAME_CONTENT_SOURCE must be 'app' or 'json'")
else:
    # Built-in chapter entries do not carry image filenames, so resolve them
    # only against the dedicated bosses/ asset directory.
    boss_assets = {file.stem: file.name for file in (ROOT / "bosses").glob("*.png")}
    CHAPTERS = [
        {**chapter, "bosses": [(*boss, boss_assets.get(boss[0])) for boss in chapter["bosses"]]}
        for chapter in CHAPTERS
    ]


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
    def __init__(self, user_id: str, username: str):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.username = username
        self.avatar: Avatar | None = None
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

    def prime_json_question(self):
        boss_key = (self.chapter, self.current_boss()[0])
        questions = QUESTION_BANK_BY_BOSS.get(boss_key, [])
        if not questions:
            return
        cursor = self.question_cursors.get(boss_key, 0)
        q = questions[cursor % len(questions)]
        self.question_cursors[boss_key] = cursor + 1
        choices = q[1][:]
        random.shuffle(choices)
        self.active_question = (q[0], choices, q[2])
        self.active_spell = None

    def current_boss(self):
        return CHAPTERS[self.chapter - 1]["bosses"][self.boss_index]

    def state(self):
        boss = self.current_boss()
        if not self.boss_hp: self.boss_hp = boss[2]
        boss_image = QUESTION_BOSS_IMAGES.get(self.active_question[0]) if self.active_question else None
        boss_image = boss_image or (boss[6] if len(boss) > 6 else None)
        boss_spell_values = BOSS_SPELL_VALUES.get((self.chapter, boss[0]), [])
        question_spell_values = QUESTION_SPELL_VALUES.get(self.active_question[0], boss_spell_values) if self.active_question else boss_spell_values
        question_spell_damage = json_available_spells(question_spell_values) if question_spell_values else {}
        question = None
        if self.active_question:
            question = {"prompt": self.active_question[0], "choices": self.active_question[1]}
        return {"session_id": self.id, "username": self.username, "avatar": self.avatar.model_dump() if self.avatar else None, "finalized": self.finalized,
                "chapter": self.chapter, "chapter_name": CHAPTERS[self.chapter-1]["name"], "chapter_subtitle": CHAPTERS[self.chapter-1]["subtitle"],
                "chapter_color": CHAPTERS[self.chapter-1]["color"], "boss": {"id": boss[0], "name": boss[1], "max_hp": boss[2], "hp": self.boss_hp, "damage": boss[3], "kind": boss[4], "lore": boss[5], "image": boss_image},
                "player": {"hp": self.player_hp, "max_hp": self.player_max_hp}, "question": question, "spell_damage": question_spell_damage, "active_spell": self.active_spell,
                "cooldowns": {key: max(0, round(value - time.time(), 1)) for key, value in self.cooldowns.items()}, "log": self.log[-5:],
                "completed": list(self.completed), "rewards": self.rewards}

sessions: dict[str, Session] = {}
app = FastAPI(title="Organic Battles V2")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.post("/api/auth/signup")
def signup(request: SignupRequest):
    email = request.email.strip().lower()
    username = request.username.strip()
    if not EMAIL_RE.fullmatch(email):
        raise HTTPException(422, "Enter a valid email address")
    if not USERNAME_RE.fullmatch(username):
        raise HTTPException(422, "Username must be 3-24 characters using letters, numbers, or underscores")
    if len(request.password) < 8:
        raise HTTPException(422, "Password must be at least 8 characters")
    user_id, now = str(uuid.uuid4()), int(time.time())
    try:
        with db() as connection:
            connection.execute("INSERT INTO users(id,email,username,password_hash,created_at) VALUES (?,?,?,?,?)", (user_id, email, username, hash_password(request.password), now))
    except sqlite3.IntegrityError as error:
        if "username" in str(error).lower():
            raise HTTPException(409, "Username taken, choose a different one")
        raise HTTPException(409, "An account with that email already exists")
    code = f"{secrets.randbelow(1000000):06d}"
    with db() as connection:
        connection.execute("INSERT INTO verification_codes(user_id,code_hash,expires_at,created_at) VALUES (?,?,?,?)", (user_id, code_hash(code), now + CODE_TTL_SECONDS, now))
    try:
        send_verification_email(email, username, code)
    except Exception as error:
        print(f"[Organic Battles] SMTP delivery failed: {type(error).__name__}: {error}")
        with db() as connection:
            connection.execute("DELETE FROM users WHERE id=?", (user_id,))
        raise HTTPException(503, "We could not send the confirmation email. Please try again.")
    return {"status": "verification_required", "email": email, "username": username}


@app.post("/api/auth/verify")
def verify(request: VerifyRequest, response: Response):
    code = request.code.strip()
    if not re.fullmatch(r"\d{6}", code):
        raise HTTPException(400, "Enter the 6-digit confirmation code")
    now = int(time.time())
    with db() as connection:
        row = connection.execute("SELECT c.*,u.* FROM verification_codes c JOIN users u ON u.id=c.user_id WHERE c.code_hash=? AND c.used=0 ORDER BY c.created_at DESC LIMIT 1", (code_hash(code),)).fetchone()
        if not row:
            raise HTTPException(400, "Invalid confirmation code")
        if row["expires_at"] < now:
            raise HTTPException(400, "Confirmation code expired. Request a new code.")
        connection.execute("UPDATE verification_codes SET used=1 WHERE id=?", (row["id"],))
        connection.execute("UPDATE users SET verified=1 WHERE id=?", (row["user_id"],))
    token = issue_auth_session(row["user_id"])
    response.set_cookie("session_token", token, httponly=True, samesite="lax", secure=os.getenv("COOKIE_SECURE", "0") == "1", max_age=60 * 60 * 24 * 30)
    with db() as connection:
        user = connection.execute("SELECT * FROM users WHERE id=?", (row["user_id"],)).fetchone()
    return {"token": token, "user": public_user(user)}


@app.post("/api/auth/resend")
def resend(email: str):
    email = email.strip().lower()
    now = int(time.time())
    with db() as connection:
        user = connection.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not user or user["verified"]:
        return {"status": "sent"}
    code = f"{secrets.randbelow(1000000):06d}"
    with db() as connection:
        connection.execute("UPDATE verification_codes SET used=1 WHERE user_id=? AND used=0", (user["id"],))
        connection.execute("INSERT INTO verification_codes(user_id,code_hash,expires_at,created_at) VALUES (?,?,?,?)", (user["id"], code_hash(code), now + CODE_TTL_SECONDS, now))
    try:
        send_verification_email(user["email"], user["username"], code)
    except Exception as error:
        print(f"[Organic Battles] SMTP resend failed: {type(error).__name__}: {error}")
        raise HTTPException(503, "We could not send the confirmation email. Please try again.")
    return {"status": "sent"}


@app.post("/api/auth/login")
def login(request: LoginRequest, response: Response):
    with db() as connection:
        user = connection.execute("SELECT * FROM users WHERE username=?", (request.username.strip(),)).fetchone()
    if not user or not check_password(request.password, user["password_hash"]):
        raise HTTPException(401, "Incorrect username or password")
    if not user["verified"]:
        raise HTTPException(403, "Please verify your email before entering the game")
    token = issue_auth_session(user["id"])
    response.set_cookie("session_token", token, httponly=True, samesite="lax", secure=os.getenv("COOKIE_SECURE", "0") == "1", max_age=60 * 60 * 24 * 30)
    return {"token": token, "user": public_user(user)}


@app.get("/api/auth/me")
def me(authorization: str | None = Header(default=None), session_token: str | None = Cookie(default=None)):
    return {"user": public_user(auth_user(authorization, session_token))}


@app.post("/api/auth/logout")
def logout(response: Response, authorization: str | None = Header(default=None), session_token: str | None = Cookie(default=None)):
    raw = session_token or (authorization[7:].strip() if authorization and authorization.lower().startswith("bearer ") else None)
    if raw:
        with db() as connection:
            connection.execute("DELETE FROM auth_sessions WHERE token_hash=?", (code_hash(raw),))
    response.delete_cookie("session_token")
    return {"status": "ok"}

def get_session(session_id: str | None) -> Session:
    if not session_id or session_id not in sessions: raise HTTPException(404, "Session not found")
    return sessions[session_id]

@app.get("/")
def index(): return FileResponse(ROOT / "templates" / "index.html")

@app.get("/favicon.ico")
def favicon(): return FileResponse(ROOT / "static" / "favicon.svg", media_type="image/svg+xml")

@app.post("/api/game/new")
def new_game(authorization: str | None = Header(default=None), session_token: str | None = Cookie(default=None)):
    user = auth_user(authorization, session_token)
    s = Session(user["id"], user["username"])
    if user["avatar_json"]:
        s.avatar = Avatar.model_validate(json.loads(user["avatar_json"]))
        s.finalized = True
    restore_game_progress(s, user["progress_json"])
    sessions[s.id] = s; return s.state()

@app.get("/api/game/state")
def game_state(session_id: str, authorization: str | None = Header(default=None), session_token: str | None = Cookie(default=None)):
    user = auth_user(authorization, session_token); game = get_session(session_id)
    if game.user_id != user["id"]: raise HTTPException(403, "This game session belongs to another account")
    return game.state()

@app.post("/api/avatar/finalize")
def finalize_avatar(session_id: str, avatar: Avatar, authorization: str | None = Header(default=None), session_token: str | None = Cookie(default=None)):
    s = get_session(session_id)
    user = auth_user(authorization, session_token)
    if s.user_id != user["id"]: raise HTTPException(403, "This game session belongs to another account")
    if avatar.character not in PLAYER_AVATAR_IDS: raise HTTPException(400, "Choose an available player avatar")
    was_finalized = s.finalized
    s.avatar, s.finalized = avatar, True
    with db() as connection:
        connection.execute("UPDATE users SET avatar_json=? WHERE id=?", (avatar.model_dump_json(), user["id"]))
    s.log.append("Avatar updated. Your ORGO journey continues." if was_finalized else "Avatar accepted. Your ORGO journey begins."); save_game_progress(s); return s.state()

@app.post("/api/battle/select-spell")
def select_spell(session_id: str, request: SpellRequest, authorization: str | None = Header(default=None), session_token: str | None = Cookie(default=None)):
    s = get_session(session_id)
    if s.user_id != auth_user(authorization, session_token)["id"]: raise HTTPException(403, "This game session belongs to another account")
    if request.spell_id not in SPELLS: raise HTTPException(400, "Unknown spell")
    if not s.finalized: raise HTTPException(400, "Finalize your avatar first")
    if s.active_question: raise HTTPException(409, "Answer the active question")
    spell = SPELLS[request.spell_id]
    if GAME_CONTENT_SOURCE == "json":
        boss_values = BOSS_SPELL_VALUES.get((s.chapter, s.current_boss()[0]), [])
        if boss_values and request.spell_id not in json_available_spells(boss_values):
            raise HTTPException(409, "This spell is not available for the current boss")
    if s.cooldowns.get(request.spell_id, 0) > time.time(): raise HTTPException(409, "Spell is cooling down")
    if GAME_CONTENT_SOURCE == "json": s.prime_json_question()
    s.active_spell, s.turn_id = request.spell_id, str(uuid.uuid4())
    if GAME_CONTENT_SOURCE != "json":
        available_questions = QUESTION_BANK_BY_BOSS.get((s.chapter, s.current_boss()[0]), QUESTION_BANK_BY_CHAPTER.get(s.chapter, QUESTIONS))
        q = random.choice(available_questions); choices = q[1][:]; random.shuffle(choices); s.active_question = (q[0], choices, q[2])
    save_game_progress(s)
    return {"turn_id": s.turn_id, **s.state()}

@app.post("/api/battle/answer")
def answer(session_id: str, request: AnswerRequest, authorization: str | None = Header(default=None), session_token: str | None = Cookie(default=None)):
    s = get_session(session_id)
    if s.user_id != auth_user(authorization, session_token)["id"]: raise HTTPException(403, "This game session belongs to another account")
    if not s.active_question or not s.active_spell: raise HTTPException(409, "No active question")
    q, choices, correct = s.active_question; spell_id = s.active_spell; spell = SPELLS[spell_id]
    is_correct = request.answer == correct
    spell_power = spell[2]
    if GAME_CONTENT_SOURCE == "json" and QUESTION_SPELL_VALUES.get(q):
        spell_power = QUESTION_SPELL_VALUES[q][JSON_SPELL_IDS_BY_RANK.index(spell_id)]
    damage = spell_power if is_correct else 0
    s.boss_hp = max(0, s.boss_hp - damage); s.cooldowns[spell_id] = time.time() + spell[3]
    self_damage = 0
    if is_correct:
        boss_hit = random.random() < 0.5; boss_damage = s.current_boss()[3] if boss_hit else 0
        s.player_hp = max(0, s.player_hp - boss_damage)
        s.log.append("Correct! " + spell[0] + " deals " + str(damage) + " damage.")
    else:
        boss_hit = False; boss_damage = 0; self_damage = spell_power
        s.player_hp = max(0, s.player_hp - self_damage)
        s.log.append("Fizzle. The incorrect " + spell[0] + " backfires for " + str(self_damage) + " damage. The correct answer was: " + correct)
    result = {"correct": is_correct, "question_prompt": q, "correct_answer": correct, "explanation": QUESTION_EXPLANATIONS.get(q, EXPLANATIONS.get(q, "Review the definition and compare each answer with the key chemistry idea in the question.")), "damage": damage, "self_damage": self_damage, "boss_hit": boss_hit, "boss_damage": boss_damage, "spell_id": spell_id}
    defeated = s.boss_hp <= 0; defeat = s.player_hp <= 0
    s.active_question = s.active_spell = s.turn_id = None
    if defeated:
        boss_id = s.current_boss()[0]; s.completed.add(boss_id); reward = {1:"Resonance Slayer",2:"Mechanism Master",3:"Spectral Champion"}.get(s.chapter, f"Chapter {s.chapter} Champion") if s.boss_index == len(CHAPTERS[s.chapter-1]["bosses"])-1 else "Arcane Chemistry Shard"; s.rewards.append(reward); s.log.append(f"{s.current_boss()[1]} defeated! Reward unlocked: {reward}.")
    if defeat:
        # Defeat is a checkpoint at the current boss. Preserve chapter,
        # boss_index, completed bosses, and rewards; only reset this fight.
        s.boss_hp = s.current_boss()[2]
        s.player_hp = s.player_max_hp
        s.completed.discard(s.current_boss()[0])
        s.active_question = s.active_spell = s.turn_id = None
        s.log.append("Your aura fades. Retry this boss when ready.")
    save_game_progress(s)
    result.update({"defeated": defeated, "defeat": defeat, **s.state()}); return result

@app.post("/api/battle/retry")
def retry(session_id: str, authorization: str | None = Header(default=None), session_token: str | None = Cookie(default=None)):
    s = get_session(session_id)
    if s.user_id != auth_user(authorization, session_token)["id"]: raise HTTPException(403, "This game session belongs to another account")
    s.player_hp = 150; s.boss_hp = s.current_boss()[2]; s.active_question = s.active_spell = None
    s.log.append("Battle reset. Your completed progression remains safe."); save_game_progress(s); return s.state()

@app.post("/api/battle/next-turn")
def next_turn(session_id: str, authorization: str | None = Header(default=None), session_token: str | None = Cookie(default=None)):
    s = get_session(session_id)
    if s.user_id != auth_user(authorization, session_token)["id"]: raise HTTPException(403, "This game session belongs to another account")
    if s.current_boss()[0] not in s.completed: raise HTTPException(409, "Defeat the current boss first")
    if s.boss_index < len(CHAPTERS[s.chapter-1]["bosses"])-1: s.boss_index += 1
    elif s.chapter < len(CHAPTERS): s.chapter += 1; s.boss_index = 0
    else: return {"victory": True, **s.state()}
    s.boss_hp = s.current_boss()[2]; s.player_hp = 150
    s.log.append("New arena discovered: " + s.current_boss()[1]); save_game_progress(s); return s.state()

@app.get("/api/progression")
def progression(session_id: str, authorization: str | None = Header(default=None), session_token: str | None = Cookie(default=None)):
    user = auth_user(authorization, session_token); game = get_session(session_id)
    if game.user_id != user["id"]: raise HTTPException(403, "This game session belongs to another account")
    return game.state()
