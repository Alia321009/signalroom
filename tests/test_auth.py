import pyotp

import app.rate_limit as rate_limit


def test_register_creates_member_and_returns_temp_token(client):
    r = client.post("/auth/register", json={"email": "new@x.com", "password": "password123"})
    assert r.status_code == 201
    assert "temp_token" in r.json()


def test_register_rejects_short_password(client):
    r = client.post("/auth/register", json={"email": "short@x.com", "password": "short"})
    assert r.status_code == 422


def test_register_rejects_duplicate_email(client, member_user):
    r = client.post("/auth/register", json={"email": member_user["email"], "password": "password123"})
    assert r.status_code == 409


def test_member_login_succeeds_with_empty_totp_code(client, member_user):
    r = client.post("/auth/login", json={"email": member_user["email"], "password": member_user["password"]})
    assert r.status_code == 200
    r2 = client.post("/auth/verify-2fa", json={"temp_token": r.json()["temp_token"], "totp_code": ""})
    assert r2.status_code == 200
    assert "access_token" in r2.json()


def test_login_rejects_wrong_password(client, member_user):
    r = client.post("/auth/login", json={"email": member_user["email"], "password": "wrong"})
    assert r.status_code == 401


def test_login_rejects_unknown_email(client):
    r = client.post("/auth/login", json={"email": "nobody@x.com", "password": "whatever123"})
    assert r.status_code == 401


def test_admin_login_requires_a_totp_code(client, admin_user):
    r = client.post("/auth/login", json={"email": admin_user["email"], "password": admin_user["password"]})
    temp_token = r.json()["temp_token"]
    r2 = client.post("/auth/verify-2fa", json={"temp_token": temp_token, "totp_code": ""})
    assert r2.status_code == 401


def test_admin_login_succeeds_with_a_valid_totp_code(client, admin_user):
    r = client.post("/auth/login", json={"email": admin_user["email"], "password": admin_user["password"]})
    temp_token = r.json()["temp_token"]
    code = pyotp.TOTP(admin_user["totp_secret"]).now()
    r2 = client.post("/auth/verify-2fa", json={"temp_token": temp_token, "totp_code": code})
    assert r2.status_code == 200
    assert "refresh_token" in r2.json()


def test_admin_login_rejects_wrong_totp_code(client, admin_user):
    r = client.post("/auth/login", json={"email": admin_user["email"], "password": admin_user["password"]})
    temp_token = r.json()["temp_token"]
    r2 = client.post("/auth/verify-2fa", json={"temp_token": temp_token, "totp_code": "000000"})
    assert r2.status_code == 401


def test_verify_2fa_rejects_invalid_temp_token(client):
    r = client.post("/auth/verify-2fa", json={"temp_token": "garbage", "totp_code": "123456"})
    assert r.status_code == 401


def test_refresh_issues_a_new_access_token(client, member_user, member_headers):
    r = client.post("/auth/login", json={"email": member_user["email"], "password": member_user["password"]})
    r2 = client.post("/auth/verify-2fa", json={"temp_token": r.json()["temp_token"], "totp_code": ""})
    refresh_token = r2.json()["refresh_token"]

    r3 = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert r3.status_code == 200
    assert "access_token" in r3.json()


def test_refresh_rejects_an_access_token_used_as_refresh(client, member_headers):
    access_token = member_headers["Authorization"].removeprefix("Bearer ")
    r = client.post("/auth/refresh", json={"refresh_token": access_token})
    assert r.status_code == 401


def test_login_rate_limited_after_five_attempts(client, member_user):
    for _ in range(5):
        client.post("/auth/login", json={"email": member_user["email"], "password": "wrong"})
    r = client.post("/auth/login", json={"email": member_user["email"], "password": "wrong"})
    assert r.status_code == 429


def test_protected_endpoint_rejects_missing_bearer_token(client):
    r = client.get("/members/me")
    assert r.status_code == 401


def test_protected_endpoint_rejects_malformed_bearer_token(client):
    r = client.get("/members/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


def test_deactivated_user_is_rejected_despite_a_valid_token(client, member_headers, member_user, session_factory):
    from app.models import User

    with session_factory() as session:
        user = session.query(User).filter_by(email=member_user["email"]).first()
        user.is_active = False
        session.commit()

    r = client.get("/members/me", headers=member_headers)
    assert r.status_code == 401
