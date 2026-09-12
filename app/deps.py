"""Shared FastAPI dependencies: DB session, JWT auth, admin gate, and the
executor's own API-key auth (separate from the member-facing JWT)."""
from __future__ import annotations

from typing import Generator

from fastapi import Depends, Header, HTTPException, Request, status
from jose import JWTError
from sqlalchemy.orm import Session

from app import auth as auth_module
from app import persistence
from app.config import Settings, get_settings
from app.models import User


def get_settings_dep() -> Settings:
    return get_settings()


def get_db(request: Request) -> Generator[Session, None, None]:
    session_factory = request.app.state.session_factory
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_current_user(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings_dep),
    session: Session = Depends(get_db),
) -> User:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")

    token = authorization.removeprefix("Bearer ")
    try:
        email = auth_module.decode_token(token, settings.jwt_secret, expected_type="access")
    except (JWTError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    user = session.query(User).filter_by(email=email).first()
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    return user


def get_executor_user(
    x_api_key: str | None = Header(default=None),
    session: Session = Depends(get_db),
) -> User:
    """Auth for the local executor's polling/reporting calls -- a
    long-lived per-member key (app/models.py's BotSettings.api_key), not
    the web JWT. An unattended script on someone's own machine can't do an
    interactive login/2FA/refresh cycle; this is the same lesson the
    trading-bot project's Phase 8 uptime monitor already learned."""
    if not x_api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "X-Api-Key header required")
    user = persistence.get_user_by_api_key(session, x_api_key)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")
    return user
