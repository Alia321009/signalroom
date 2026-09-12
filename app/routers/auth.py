"""
Auth endpoints. POST /auth/register (members only -- the admin has no
signup, see app/bootstrap.py). POST /auth/login always returns a temp
token; whether the next step actually requires a TOTP code depends on the
account (mandatory for admin, optional for members -- see verify-2fa).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError
from sqlalchemy.orm import Session

from app import auth as auth_module
from app import persistence
from app import rate_limit
from app.deps import get_db, get_settings_dep
from app.config import Settings
from app.models import User
from app.schemas import (
    AccessTokenResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TempTokenResponse,
    TokenPairResponse,
    Verify2FARequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TempTokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterRequest, session: Session = Depends(get_db), settings: Settings = Depends(get_settings_dep)
) -> TempTokenResponse:
    existing = session.query(User).filter_by(email=body.email).first()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    if len(body.password) < 8:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Password must be at least 8 characters")

    user = User(email=body.email, password_hash=auth_module.hash_password(body.password), role="member")
    session.add(user)
    session.flush()
    persistence.get_or_create_subscription(session, user.id)
    persistence.record_subscription_event(session, user.id, "registered", f"{user.email} registered")
    session.commit()

    return TempTokenResponse(temp_token=auth_module.create_temp_token(user.email, settings.jwt_secret))


@router.post("/login", response_model=TempTokenResponse)
def login(
    body: LoginRequest,
    request: Request,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> TempTokenResponse:
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limit.check_and_record(client_ip):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many login attempts; try again later")

    user = session.query(User).filter_by(email=body.email).first()
    if user is None or not auth_module.verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")

    return TempTokenResponse(temp_token=auth_module.create_temp_token(user.email, settings.jwt_secret))


@router.post("/verify-2fa", response_model=TokenPairResponse)
def verify_2fa(
    body: Verify2FARequest,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> TokenPairResponse:
    try:
        email = auth_module.decode_token(body.temp_token, settings.jwt_secret, expected_type="temp")
    except (JWTError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired temp token")

    user = session.query(User).filter_by(email=email).first()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired temp token")

    # TOTP is mandatory for admin, optional for a member who hasn't
    # enrolled one -- an empty totp_code is accepted only in that case.
    if user.totp_secret:
        if not body.totp_code or not auth_module.verify_totp(
            user.totp_secret, body.totp_code, settings.totp_valid_window
        ):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid TOTP code")
    elif user.role == "admin":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Admin account has no TOTP enrolled — contact support")

    return TokenPairResponse(
        access_token=auth_module.create_access_token(user.email, settings.jwt_secret),
        refresh_token=auth_module.create_refresh_token(user.email, settings.jwt_refresh_secret),
    )


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(
    body: RefreshRequest,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> AccessTokenResponse:
    try:
        email = auth_module.decode_token(body.refresh_token, settings.jwt_refresh_secret, expected_type="refresh")
    except (JWTError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")

    user = session.query(User).filter_by(email=email).first()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    return AccessTokenResponse(access_token=auth_module.create_access_token(user.email, settings.jwt_secret))
