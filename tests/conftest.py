"""Shared fixtures: an in-memory SQLite session factory (StaticPool +
check_same_thread=False, so every session_factory() call shares the same
:memory: database -- essential since get_db calls it fresh per request),
a FastAPI TestClient wired to it, and full auth-flow helpers for both an
admin (TOTP-mandatory) and a plain member (TOTP-optional)."""
from __future__ import annotations

import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.rate_limit as rate_limit
from app import auth as auth_module
from app.main import create_app
from app.config import Settings
from app.models import Base, User

TEST_JWT_SECRET = "test-jwt-secret"
TEST_JWT_REFRESH_SECRET = "test-jwt-refresh-secret"


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    rate_limit.reset_all()
    yield
    rate_limit.reset_all()


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, jwt_secret=TEST_JWT_SECRET, jwt_refresh_secret=TEST_JWT_REFRESH_SECRET)


@pytest.fixture
def session_factory():
    db_engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(db_engine)
    return sessionmaker(bind=db_engine)


@pytest.fixture
def app(session_factory, settings):
    return create_app(session_factory, settings=settings)


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_user(session_factory) -> dict:
    email = "admin@signalroom.test"
    password = "admin-password-123"
    totp_secret = auth_module.generate_totp_secret()
    with session_factory() as session:
        user = User(email=email, password_hash=auth_module.hash_password(password), totp_secret=totp_secret, role="admin")
        session.add(user)
        session.commit()
    return {"email": email, "password": password, "totp_secret": totp_secret}


@pytest.fixture
def admin_headers(client, admin_user) -> dict:
    r = client.post("/auth/login", json={"email": admin_user["email"], "password": admin_user["password"]})
    assert r.status_code == 200, r.text
    temp_token = r.json()["temp_token"]
    code = pyotp.TOTP(admin_user["totp_secret"]).now()
    r2 = client.post("/auth/verify-2fa", json={"temp_token": temp_token, "totp_code": code})
    assert r2.status_code == 200, r2.text
    return {"Authorization": f"Bearer {r2.json()['access_token']}"}


@pytest.fixture
def member_user(client) -> dict:
    email = "member@signalroom.test"
    password = "member-password-123"
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    return {"email": email, "password": password, "temp_token": r.json()["temp_token"]}


@pytest.fixture
def member_headers(client, member_user) -> dict:
    r = client.post("/auth/login", json={"email": member_user["email"], "password": member_user["password"]})
    assert r.status_code == 200, r.text
    temp_token = r.json()["temp_token"]
    r2 = client.post("/auth/verify-2fa", json={"temp_token": temp_token, "totp_code": ""})
    assert r2.status_code == 200, r2.text
    return {"Authorization": f"Bearer {r2.json()['access_token']}"}
