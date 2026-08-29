import time
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    verified = Column(Integer, nullable=False, default=0)
    avatar_json = Column(String, nullable=True)
    progress_json = Column(String, nullable=True)
    created_at = Column(Integer, nullable=False, default=lambda: int(time.time()))

    verification_codes = relationship("VerificationCode", back_populates="user", cascade="all, delete-orphan")
    auth_sessions = relationship("AuthSession", back_populates="user", cascade="all, delete-orphan")
    game_sessions = relationship("GameSession", back_populates="user", cascade="all, delete-orphan")

class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code_hash = Column(String, nullable=False)
    expires_at = Column(Integer, nullable=False)
    used = Column(Integer, nullable=False, default=0)
    created_at = Column(Integer, nullable=False, default=lambda: int(time.time()))

    user = relationship("User", back_populates="verification_codes")

# Index for fast lookup of verification codes by user
Index("idx_codes_user_new", VerificationCode.user_id, VerificationCode.created_at.desc())

class AuthSession(Base):
    __tablename__ = "auth_sessions"

    token_hash = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(Integer, nullable=False)
    created_at = Column(Integer, nullable=False, default=lambda: int(time.time()))

    user = relationship("User", back_populates="auth_sessions")

class GameSession(Base):
    __tablename__ = "game_sessions"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
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
    version = Column(Integer, nullable=False, default=1)  # For optimistic locking
    updated_at = Column(Integer, nullable=False, default=lambda: int(time.time()))

    user = relationship("User", back_populates="game_sessions")
