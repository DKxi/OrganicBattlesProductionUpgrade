import time
import uuid
import logging
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from app.infrastructure.database.models import AdminUser, AdminSession, AdminAuditLog
from app.infrastructure.identity.crypto import hash_password, verify_password

logger = logging.getLogger("organicbattles.admin")


class AdminRepository:
    """Repository managing administrator accounts, sessions, and audit logs."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, admin_id: str) -> Optional[AdminUser]:
        return self.db.query(AdminUser).filter(AdminUser.id == admin_id).first()

    def get_by_username(self, username: str) -> Optional[AdminUser]:
        if not username:
            return None
        return self.db.query(AdminUser).filter(AdminUser.username == username.strip().lower()).first()

    def create_admin(
        self,
        username: str,
        password_hash: str,
        role: str = "admin",
        is_active: int = 1,
    ) -> AdminUser:
        clean_user = username.strip().lower()
        admin_id = f"admin_{uuid.uuid4().hex[:16]}"
        now = int(time.time())
        admin = AdminUser(
            id=admin_id,
            username=clean_user,
            password_hash=password_hash,
            role=role,
            is_active=is_active,
            created_at=now,
            updated_at=now,
        )
        self.db.add(admin)
        self.db.commit()
        self.db.refresh(admin)
        logger.info("[ADMIN_AUDIT] Created admin user '%s' (ID: %s, role: %s)", admin.username, admin.id, admin.role)
        return admin

    def verify_admin_credentials(self, username: str, password: str) -> Optional[AdminUser]:
        admin = self.get_by_username(username)
        if not admin:
            return None
        if not admin.is_active:
            logger.warning("[ADMIN_AUTH] Login attempt for disabled admin user '%s'", username)
            return None
        if verify_password(password, admin.password_hash):
            return admin
        return None

    def create_session(
        self,
        admin_user_id: str,
        token_hash: str,
        ttl_seconds: int = 86400,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AdminSession:
        now = int(time.time())
        expires_at = now + ttl_seconds
        sess = AdminSession(
            token_hash=token_hash,
            admin_user_id=admin_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
            created_at=now,
            last_activity_at=now,
        )
        self.db.add(sess)
        self.db.commit()
        self.db.refresh(sess)
        return sess

    def get_session(self, token_hash: str) -> Optional[AdminSession]:
        if not token_hash:
            return None
        sess = self.db.query(AdminSession).filter(AdminSession.token_hash == token_hash).first()
        if not sess:
            return None
        if sess.expires_at < int(time.time()):
            self.db.delete(sess)
            self.db.commit()
            return None
        return sess

    def update_session_activity(self, token_hash: str) -> None:
        try:
            self.db.query(AdminSession).filter(AdminSession.token_hash == token_hash).update(
                {"last_activity_at": int(time.time())}
            )
            self.db.commit()
        except Exception:
            self.db.rollback()

    def delete_session(self, token_hash: str) -> bool:
        sess = self.db.query(AdminSession).filter(AdminSession.token_hash == token_hash).first()
        if sess:
            self.db.delete(sess)
            self.db.commit()
            return True
        return False

    def delete_expired_sessions(self) -> int:
        now = int(time.time())
        deleted = self.db.query(AdminSession).filter(AdminSession.expires_at < now).delete()
        self.db.commit()
        return deleted

    def log_action(
        self,
        admin_user_id: str,
        admin_username: str,
        action: str,
        target_type: str,
        target_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AdminAuditLog:
        now = int(time.time())
        audit = AdminAuditLog(
            admin_user_id=admin_user_id,
            admin_username=admin_username,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details_json=details or {},
            ip_address=ip_address,
            created_at=now,
        )
        self.db.add(audit)
        try:
            self.db.commit()
            self.db.refresh(audit)
        except Exception:
            self.db.rollback()
            raise
        return audit

    def seed_default_admins(self) -> List[AdminUser]:
        """
        Seed initial default admin users required by specification:
        - user: admin, password: admin
        - user: admin1, password: admin2
        """
        defaults = [
            ("admin", "admin", "superadmin"),
            ("admin1", "admin2", "admin"),
        ]
        seeded = []
        for uname, pwd, role in defaults:
            existing = self.get_by_username(uname)
            if not existing:
                pwd_hash = hash_password(pwd)
                admin = self.create_admin(username=uname, password_hash=pwd_hash, role=role)
                seeded.append(admin)
                logger.info("[ADMIN_SEED] Seeded default admin user '%s' with role '%s'", uname, role)
            else:
                seeded.append(existing)
        return seeded
