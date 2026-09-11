import time
from sqlalchemy import Column, String, Integer, BigInteger, Float, Text, ForeignKey, Index, UniqueConstraint, JSON
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


class Boss(Base):
    __tablename__ = "OB_bosses"

    id = Column(String, primary_key=True)
    slug = Column(String, nullable=False, index=True)
    track_id = Column(String, ForeignKey("OB_tracks.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter = Column(Integer, nullable=False)
    order_index = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    image_file = Column(String, nullable=False)
    health = Column(Integer, nullable=False, default=100)
    element = Column(String, nullable=True)
    strategy_json = Column(JSON_VARIANT, nullable=False, default=dict)
    created_at = Column(Integer, nullable=False, default=lambda: int(time.time()))

    track = relationship("Track", backref="bosses")
    question_assignments = relationship("BossQuestionAssignment", back_populates="boss", cascade="all, delete-orphan", order_by="BossQuestionAssignment.order_index")

    __table_args__ = (
        Index("ix_ob_bosses_track_ch_order", "track_id", "chapter", "order_index"),
        UniqueConstraint("track_id", "chapter", "order_index", name="uq_ob_bosses_track_ch_order"),
    )


class BossQuestionAssignment(Base):
    __tablename__ = "OB_boss_question_assignments"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    boss_id = Column(String, ForeignKey("OB_bosses.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("OB_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    track_id = Column(String, ForeignKey("OB_tracks.id", ondelete="CASCADE"), nullable=False, index=True)
    release_id = Column(String, ForeignKey("OB_content_releases.id", ondelete="SET NULL"), nullable=True, index=True)
    order_index = Column(Integer, nullable=False, default=0)
    weight = Column(Float, nullable=False, default=1.0)
    created_at = Column(Integer, nullable=False, default=lambda: int(time.time()))

    boss = relationship("Boss", back_populates="question_assignments")
    question = relationship("Question", backref="boss_assignments")
    track = relationship("Track")
    release = relationship("ContentRelease")

    __table_args__ = (
        Index("ix_ob_bqa_boss_order", "boss_id", "order_index"),
        Index("ix_ob_bqa_track_release", "track_id", "release_id"),
        UniqueConstraint("boss_id", "question_id", "release_id", name="uq_ob_bqa_boss_question_release"),
    )


class PlayerQuestionProgress(Base):
    __tablename__ = "OB_player_question_progress"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("OB_users.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("OB_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    track_id = Column(String, ForeignKey("OB_tracks.id", ondelete="CASCADE"), nullable=False, index=True)
    mastery_score = Column(Float, nullable=False, default=0.0)       # 0.0 to 1.0 progressive mastery
    ease_factor = Column(Float, nullable=False, default=2.5)         # SM-2 ease factor
    interval_days = Column(Float, nullable=False, default=0.0)       # Current review interval in days
    repetitions = Column(Integer, nullable=False, default=0)         # Successful recall streak
    total_attempts = Column(Integer, nullable=False, default=0)
    correct_attempts = Column(Integer, nullable=False, default=0)
    last_attempt_at = Column(Integer, nullable=True)
    next_review_at = Column(Integer, nullable=True, index=True)
    created_at = Column(Integer, nullable=False, default=lambda: int(time.time()))
    updated_at = Column(Integer, nullable=False, default=lambda: int(time.time()))

    user = relationship("User", backref="question_progress")
    question = relationship("Question", backref="player_progress")
    track = relationship("Track")

    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_ob_pqp_user_question"),
        Index("ix_ob_pqp_user_review", "user_id", "next_review_at"),
        Index("ix_ob_pqp_user_track_mastery", "user_id", "track_id", "mastery_score"),
    )


class AnswerAttempt(Base):
    __tablename__ = "OB_answer_attempts"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("OB_game_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(String, ForeignKey("OB_users.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("OB_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    track_id = Column(String, nullable=False, index=True)
    release_id = Column(String, nullable=True)
    boss_slug = Column(String, nullable=False, index=True)
    spell_id = Column(String, nullable=True)
    selected_option = Column(String, nullable=False)
    is_correct = Column(Integer, nullable=False)                     # 1 for correct, 0 for incorrect
    damage_dealt = Column(Integer, nullable=False, default=0)
    damage_taken = Column(Integer, nullable=False, default=0)
    time_taken_ms = Column(Integer, nullable=True)
    created_at = Column(Integer, nullable=False, default=lambda: int(time.time()), index=True)

    user = relationship("User", backref="answer_attempts")
    question = relationship("Question", backref="answer_attempts")
    session = relationship("GameSession", backref="answer_attempts")

    __table_args__ = (
        Index("ix_ob_attempts_user_time", "user_id", "created_at"),
        Index("ix_ob_attempts_question_correct", "question_id", "is_correct"),
        Index("ix_ob_attempts_track_time", "track_id", "created_at"),
        Index("ix_ob_attempts_boss_time", "boss_slug", "created_at"),
    )


