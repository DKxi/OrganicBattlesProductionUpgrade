import time
from sqlalchemy import Column, String, Integer, BigInteger, Text, ForeignKey, Index, UniqueConstraint, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship

JSON_VARIANT = JSON().with_variant(JSONB, "postgresql")
Base = declarative_base()


class User(Base):
    __tablename__ = "OB_users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    verified = Column(Integer, nullable=False, default=0)
    content_source = Column(String, nullable=True, default=None)
    avatar_json = Column(String, nullable=True)
    progress_json = Column(String, nullable=True)
    created_at = Column(Integer, nullable=False, default=lambda: int(time.time()))

    verification_codes = relationship("VerificationCode", back_populates="user", cascade="all, delete-orphan")
    auth_sessions = relationship("AuthSession", back_populates="user", cascade="all, delete-orphan")
    game_sessions = relationship("GameSession", back_populates="user", cascade="all, delete-orphan")


class VerificationCode(Base):
    __tablename__ = "OB_verification_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("OB_users.id", ondelete="CASCADE"), nullable=False)
    code_hash = Column(String, nullable=False)
    expires_at = Column(Integer, nullable=False)
    used = Column(Integer, nullable=False, default=0)
    created_at = Column(Integer, nullable=False, default=lambda: int(time.time()))

    user = relationship("User", back_populates="verification_codes")


class AuthSession(Base):
    __tablename__ = "OB_auth_sessions"

    token_hash = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("OB_users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(Integer, nullable=False)
    created_at = Column(Integer, nullable=False, default=lambda: int(time.time()))

    user = relationship("User", back_populates="auth_sessions")


class GameSession(Base):
    __tablename__ = "OB_game_sessions"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("OB_users.id", ondelete="CASCADE"), nullable=False, unique=True)
    content_source = Column(String, nullable=True, default=None)
    chapter = Column(Integer, nullable=False, default=1)
    boss_index = Column(Integer, nullable=False, default=0)
    player_hp = Column(Integer, nullable=False, default=150)
    player_max_hp = Column(Integer, nullable=False, default=150)
    boss_hp = Column(Integer, nullable=False, default=0)
    active_question_json = Column(String, nullable=True)
    active_spell = Column(String, nullable=True)
    turn_id = Column(String, nullable=True)
    cooldowns_json = Column(String, nullable=False, default="{}")
    log_json = Column(String, nullable=False, default="[]")
    completed_json = Column(String, nullable=False, default="[]")
    rewards_json = Column(String, nullable=False, default="[]")
    question_cursors_json = Column(String, nullable=False, default="{}")
    version = Column(Integer, nullable=False, default=1)
    updated_at = Column(Integer, nullable=False, default=lambda: int(time.time()))

    user = relationship("User", back_populates="game_sessions")


class Curriculum(Base):
    __tablename__ = "OB_curricula"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=True)
    total_questions = Column(Integer, nullable=False, default=0)
    chapters = Column(Integer, nullable=False, default=0)
    bosses = Column(Integer, nullable=False, default=0)
    display_order = Column(Integer, nullable=False, default=0)

    tracks = relationship("Track", back_populates="curriculum", cascade="all, delete-orphan")


class Track(Base):
    __tablename__ = "OB_tracks"

    id = Column(String, primary_key=True)
    curriculum_id = Column(String, ForeignKey("OB_curricula.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    detail = Column(String, nullable=True)
    data_folder = Column(String, nullable=False)
    boss_folder = Column(String, nullable=True)
    questions = Column(Integer, nullable=False, default=0)
    chapters = Column(Integer, nullable=False, default=0)
    accent = Column(String, nullable=False, default="amber")
    display_order = Column(Integer, nullable=False, default=0)

    curriculum = relationship("Curriculum", back_populates="tracks")
    questions_rel = relationship("Question", back_populates="track", cascade="all, delete-orphan", order_by="Question.order_index")
    releases = relationship("ContentRelease", back_populates="track", cascade="all, delete-orphan", order_by="ContentRelease.version.desc()")


class ContentRelease(Base):
    __tablename__ = "OB_content_releases"

    id = Column(String, primary_key=True)
    track_id = Column(String, ForeignKey("OB_tracks.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    status = Column(String, nullable=False, default="draft")  # draft, published, archived
    checksum = Column(String, nullable=True)
    created_at = Column(Integer, nullable=False, default=lambda: int(time.time()))
    published_at = Column(Integer, nullable=True)

    track = relationship("Track", back_populates="releases")
    questions = relationship("Question", back_populates="release")

    __table_args__ = (
        Index("ix_ob_content_releases_track_ver", "track_id", "version"),
        Index("ix_ob_content_releases_track_status", "track_id", "status"),
    )


class Question(Base):
    __tablename__ = "OB_questions"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    track_id = Column(String, ForeignKey("OB_tracks.id", ondelete="CASCADE"), nullable=False, index=True)
    release_id = Column(String, ForeignKey("OB_content_releases.id", ondelete="SET NULL"), nullable=True, index=True)
    raw_id = Column(String, nullable=False)
    chapter = Column(Integer, nullable=False)
    chapter_title = Column(String, nullable=False)
    boss_name = Column(String, nullable=False)
    boss_slug = Column(String, nullable=False)
    order_index = Column(Integer, nullable=False)  # Strict sequential order matching JSON array
    topic = Column(String, nullable=True)
    difficulty = Column(String, nullable=True)
    question_type = Column(String, nullable=False, default="Multiple Choice")
    prompt = Column(Text, nullable=False)
    options_json = Column(JSON_VARIANT, nullable=False)    # JSON/JSONB serialized list of options [{label, text}]
    correct_option = Column(String, nullable=False)
    correct_answer = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    spells_json = Column(JSON_VARIANT, nullable=False, default=lambda: [20, 30, 45])
    health_json = Column(JSON_VARIANT, nullable=False, default=lambda: [100])
    images_json = Column(JSON_VARIANT, nullable=False, default=list)
    created_at = Column(Integer, nullable=False, default=lambda: int(time.time()))
    updated_at = Column(Integer, nullable=False, default=lambda: int(time.time()))

    track = relationship("Track", back_populates="questions_rel")
    release = relationship("ContentRelease", back_populates="questions")

    __table_args__ = (
        Index("ix_ob_questions_track_ch_order", "track_id", "chapter", "order_index"),
        Index("ix_ob_questions_track_ch_boss_order", "track_id", "chapter", "boss_slug", "order_index"),
        Index("ix_ob_questions_track_release_ch_order", "track_id", "release_id", "chapter", "order_index"),
        Index(
            "ix_ob_questions_prompt_trgm",
            "prompt",
            postgresql_using="gin",
            postgresql_ops={"prompt": "gin_trgm_ops"},
        ),
        Index(
            "ix_ob_questions_topic_trgm",
            "topic",
            postgresql_using="gin",
            postgresql_ops={"topic": "gin_trgm_ops"},
        ),
        UniqueConstraint("track_id", "release_id", "chapter", "order_index", name="uq_ob_questions_order"),
    )


