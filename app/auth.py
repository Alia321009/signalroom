"""
Auth primitives: bcrypt password hashing, JWT access/refresh tokens, TOTP.
Same proven shape as the trading-bot project's api/auth.py.

TOTP is mandatory for the admin (the one account that can post calls and
manage every member's access) and optional for members -- forcing 2FA on
every paying subscriber is unusual friction for a consumer product that
growthclubpk.com itself doesn't appear to require either; the admin
account is the one worth protecting at that bar.
"""
from __future__ import annotations

import datetime
import secrets
from typing import Literal

import pyotp
from jose import JWTError, jwt
from passlib.context import CryptContext

TokenType = Literal["temp", "access", "refresh"]

ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 15
REFRESH_TOKEN_DAYS = 7
TEMP_TOKEN_MINUTES = 5

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password, password_hash)


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def totp_provisioning_uri(secret: str, email: str, issuer: str = "SignalRoom") -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def verify_totp(secret: str, code: str, valid_window: int = 1) -> bool:
    return pyotp.TOTP(secret).verify(code, valid_window=valid_window)


def _create_token(subject: str, token_type: TokenType, expires_delta: datetime.timedelta, secret: str) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {"sub": subject, "type": token_type, "iat": now, "exp": now + expires_delta}
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def create_temp_token(email: str, secret: str) -> str:
    return _create_token(email, "temp", datetime.timedelta(minutes=TEMP_TOKEN_MINUTES), secret)


def create_access_token(email: str, secret: str) -> str:
    return _create_token(email, "access", datetime.timedelta(minutes=ACCESS_TOKEN_MINUTES), secret)


def create_refresh_token(email: str, secret: str) -> str:
    return _create_token(email, "refresh", datetime.timedelta(days=REFRESH_TOKEN_DAYS), secret)


def decode_token(token: str, secret: str, expected_type: TokenType) -> str:
    """Returns the subject (email) if valid and of the expected type;
    raises JWTError/ValueError otherwise."""
    payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
    if payload.get("type") != expected_type:
        raise ValueError(f"expected token type {expected_type!r}, got {payload.get('type')!r}")
    return payload["sub"]


def generate_api_key() -> str:
    """A member's executor API key -- unrelated to JWT, long-lived, and
    revocable independently by rotating it (see app/routers/bot.py)."""
    return secrets.token_hex(32)
