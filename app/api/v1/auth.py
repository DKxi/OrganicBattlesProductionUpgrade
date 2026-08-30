import time
from typing import Optional
from fastapi import APIRouter, Request, Response, Depends, HTTPException, Header, Cookie
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session as DBSession

from app.settings import settings
from app.api.deps import get_db, get_current_user, limiter
from app.infrastructure.database.models import User
from app.infrastructure.database.repositories import UserRepository, AuthRepository
from app.infrastructure.identity.crypto import (
    hash_password,
    verify_password,
    code_hash,
    generate_verification_code,
    generate_session_token,
)
from app.infrastructure.messaging.smtp import send_verification_code_email
from app.domain.accounts.entities import to_public_user
from app.domain.content.resolver import resolve_content_source

router = APIRouter(tags=["Authentication"])


class SignupRequest(BaseModel):
    email: str = Field(..., min_length=5)
    username: str = Field(..., min_length=3, max_length=24)
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    email_or_username: Optional[str] = None
    password: str


class VerifyRequest(BaseModel):
    code: str




@router.post("/auth/signup")
@limiter.limit("5/minute")
def signup(request: Request, body: SignupRequest, db: DBSession = Depends(get_db)):
    email = body.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1] or len(email) < 5:
        raise HTTPException(422, "Please enter a valid email address.")
    if len(body.username) < 3 or len(body.username) > 24:
        raise HTTPException(422, "Username must be between 3 and 24 characters")
    if len(body.password) < 8:
        raise HTTPException(422, "Password must be at least 8 characters")

    user_repo = UserRepository(db)
    auth_repo = AuthRepository(db)

    if user_repo.get_by_email(email):
        raise HTTPException(409, "An account with that email already exists")
    if user_repo.get_by_username(body.username):
        raise HTTPException(409, "Username taken, choose a different one")

    pwd_hash = hash_password(body.password)
    user = user_repo.create_user(email, body.username, pwd_hash)

    code = generate_verification_code()
    chash = code_hash(code)
    auth_repo.create_verification_code(user.id, chash, settings.verification_code_ttl_seconds)

    import sys
    root_mod = sys.modules.get("app")
    sender_func = getattr(root_mod, "send_verification_email", send_verification_code_email) if root_mod else send_verification_code_email
    sender_func(user.email, user.username, code)

    return {
        "status": "pending_verification",
        "message": f"Confirmation code sent to {user.email}",
        "user_id": user.id,
    }


@router.post("/auth/verify")
@limiter.limit("10/minute")
def verify_code(request: Request, body: VerifyRequest, response: Response, db: DBSession = Depends(get_db)):
    auth_repo = AuthRepository(db)
    user_repo = UserRepository(db)

    code_str = body.code.strip()
    if not code_str.isdigit() or len(code_str) != 6:
        raise HTTPException(400, "Confirmation code must be a 6-digit number")

    chash = code_hash(code_str)
    record = auth_repo.get_valid_verification_code(chash)
    if not record:
        raise HTTPException(400, "Invalid confirmation code")

    auth_repo.mark_code_used(record.id)

    user = user_repo.get_by_id(record.user_id)
    if not user:

        raise HTTPException(404, "User not found")

    user.verified = 1
    db.commit()

    token = generate_session_token()
    thash = code_hash(token)
    auth_repo.create_session(user.id, thash, settings.auth_session_ttl_days)

    response.set_cookie(
        "session_token",
        token,
        httponly=True,
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
        max_age=settings.auth_session_ttl_days * 86400,
    )

    effective = resolve_content_source(user.content_source)
    return {
        "token": token,
        "user": to_public_user(user, effective),
        "status": "ok",
    }


@router.post("/auth/login")
@limiter.limit("10/minute")
def login(request: Request, body: LoginRequest, response: Response, db: DBSession = Depends(get_db)):
    user_repo = UserRepository(db)
    auth_repo = AuthRepository(db)

    identifier = (body.username or body.email or body.email_or_username or "").strip()
    if not identifier:
        raise HTTPException(422, "Please enter your username or email address")

    # Support login by username or email
    user = user_repo.get_by_username(identifier) or user_repo.get_by_email(identifier.lower())
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Incorrect username or password")
    if not user.verified:
        raise HTTPException(403, "Account not verified. Please verify your email first.")

    token = generate_session_token()
    thash = code_hash(token)
    auth_repo.create_session(user.id, thash, settings.auth_session_ttl_days)


    response.set_cookie(
        "session_token",
        token,
        httponly=True,
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
        max_age=settings.auth_session_ttl_days * 86400,
    )

    effective = resolve_content_source(user.content_source)
    return {
        "token": token,
        "user": to_public_user(user, effective),
        "status": "ok",
    }


@router.get("/auth/me")
def me(current_user: User = Depends(get_current_user)):
    effective = resolve_content_source(current_user.content_source)
    return {"user": to_public_user(current_user, effective)}


@router.post("/auth/resend")
@limiter.limit("3/minute")
def resend_code(request: Request, email: str, db: DBSession = Depends(get_db)):
    user_repo = UserRepository(db)
    auth_repo = AuthRepository(db)

    user = user_repo.get_by_email(email)
    if not user:
        raise HTTPException(404, "User not found")

    code = generate_verification_code()
    chash = code_hash(code)
    auth_repo.create_verification_code(user.id, chash, settings.verification_code_ttl_seconds)

    send_verification_code_email(user.email, user.username, code)

    return {"status": "ok", "message": f"Fresh confirmation code sent to {user.email}"}


@router.post("/auth/logout")
def logout(
    response: Response,
    authorization: Optional[str] = Header(default=None),
    session_token: Optional[str] = Cookie(default=None),
    db: DBSession = Depends(get_db),
):
    raw = None
    if authorization and authorization.lower().startswith("bearer "):
        raw = authorization[7:].strip()
    elif session_token:
        raw = session_token

    if raw:
        thash = code_hash(raw)
        auth_repo = AuthRepository(db)
        auth_repo.delete_session(thash)

    response.delete_cookie("session_token")
    return {"status": "ok"}
