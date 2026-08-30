import time
import secrets
from typing import Optional, List
from sqlalchemy.orm import Session as DBSession
from app.infrastructure.database.models import User, GameSession, AuthSession, VerificationCode


class UserRepository:
    def __init__(self, db: DBSession):
        self.db = db

    def get_by_id(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email.strip().lower()).first()

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username.strip()).first()

    def create_user(self, email: str, username: str, password_hash: str) -> User:
        user = User(
            id=secrets.token_hex(16),
            email=email.strip().lower(),
            username=username.strip(),
            password_hash=password_hash,
            verified=0,
            avatar_json=None,
            progress_json=None,
            content_source=None,
            created_at=int(time.time()),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_content_source(self, user_id: str, content_source: Optional[str]) -> Optional[User]:
        user = self.get_by_id(user_id)
        if not user:
            return None
        user.content_source = content_source
        self.db.commit()
        self.db.refresh(user)
        return user

    def list_all(self) -> List[User]:
        return self.db.query(User).order_by(User.created_at.desc()).all()


class SessionRepository:
    def __init__(self, db: DBSession):
        self.db = db

    def get_by_id(self, session_id: str) -> Optional[GameSession]:
        return self.db.query(GameSession).filter(GameSession.id == session_id).first()

    def get_by_user_id(self, user_id: str) -> Optional[GameSession]:
        return self.db.query(GameSession).filter(GameSession.user_id == user_id).first()

    def create_or_update(self, session_obj: GameSession) -> GameSession:
        self.db.merge(session_obj)
        self.db.commit()
        return session_obj

    def delete(self, session_id: str) -> bool:
        session_row = self.get_by_id(session_id)
        if not session_row:
            return False
        user = self.db.query(User).filter(User.id == session_row.user_id).first()
        if user:
            user.progress_json = None
        self.db.delete(session_row)
        self.db.commit()
        return True

    def list_all(self) -> List[GameSession]:
        return self.db.query(GameSession).order_by(GameSession.updated_at.desc()).all()


class AuthRepository:
    def __init__(self, db: DBSession):
        self.db = db

    def create_session(self, user_id: str, token_hash: str, ttl_days: int = 30) -> AuthSession:
        auth_session = AuthSession(
            token_hash=token_hash,
            user_id=user_id,
            expires_at=int(time.time()) + ttl_days * 86400,
            created_at=int(time.time()),
        )
        self.db.add(auth_session)
        self.db.commit()
        self.db.refresh(auth_session)
        return auth_session

    def get_session(self, token_hash: str) -> Optional[AuthSession]:
        return (
            self.db.query(AuthSession)
            .filter(AuthSession.token_hash == token_hash, AuthSession.expires_at > int(time.time()))
            .first()
        )

    def delete_session(self, token_hash: str) -> bool:
        auth_session = self.db.query(AuthSession).filter(AuthSession.token_hash == token_hash).first()
        if auth_session:
            self.db.delete(auth_session)
            self.db.commit()
            return True
        return False

    def create_verification_code(self, user_id: str, code_hash: str, ttl_seconds: int = 900) -> VerificationCode:
        # Invalidate old unused codes
        self.db.query(VerificationCode).filter(
            VerificationCode.user_id == user_id,
            VerificationCode.used == 0
        ).update({"used": 1})

        record = VerificationCode(
            user_id=user_id,
            code_hash=code_hash,
            expires_at=int(time.time()) + ttl_seconds,
            used=0,
            created_at=int(time.time()),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_valid_verification_code(self, code_hash: str) -> Optional[VerificationCode]:
        return (
            self.db.query(VerificationCode)
            .filter(
                VerificationCode.code_hash == code_hash,
                VerificationCode.used == 0,
                VerificationCode.expires_at > int(time.time())
            )
            .first()
        )

    def mark_code_used(self, code_id: int) -> None:
        self.db.query(VerificationCode).filter(VerificationCode.id == code_id).update({"used": 1})
        self.db.commit()
