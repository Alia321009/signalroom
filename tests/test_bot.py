def test_get_my_bot_settings_creates_defaults_on_first_call(client, member_headers):
    r = client.get("/bot-settings/me", headers=member_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False
    assert body["symbols"] == []
    assert body["magic"] > 0
    assert "api_key" not in body  # never returned from a plain GET


def test_bot_settings_are_stable_across_repeated_calls(client, member_headers):
    first = client.get("/bot-settings/me", headers=member_headers).json()
    second = client.get("/bot-settings/me", headers=member_headers).json()
    assert first["magic"] == second["magic"]


def test_two_members_get_distinct_magic_numbers(client, member_headers, session_factory):
    from app import auth as auth_module
    from app.models import User

    with session_factory() as session:
        other = User(email="other@x.com", password_hash=auth_module.hash_password("password123"), role="member")
        session.add(other)
        session.commit()

    mine = client.get("/bot-settings/me", headers=member_headers).json()

    r = client.post("/auth/login", json={"email": "other@x.com", "password": "password123"})
    r2 = client.post("/auth/verify-2fa", json={"temp_token": r.json()["temp_token"], "totp_code": ""})
    other_headers = {"Authorization": f"Bearer {r2.json()['access_token']}"}
    theirs = client.get("/bot-settings/me", headers=other_headers).json()

    assert mine["magic"] != theirs["magic"]


def test_update_bot_settings_enables_and_sets_risk(client, member_headers):
    r = client.put(
        "/bot-settings/me",
        json={"enabled": True, "risk_pct": 2.0, "symbols": ["xauusd", "eurusd"]},
        headers=member_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True
    assert body["risk_pct"] == 2.0
    assert body["symbols"] == ["XAUUSD", "EURUSD"]  # normalized


def test_update_bot_settings_rejects_risk_pct_above_five(client, member_headers):
    r = client.put("/bot-settings/me", json={"risk_pct": 10.0}, headers=member_headers)
    assert r.status_code == 422


def test_update_bot_settings_partial_update_leaves_other_fields_untouched(client, member_headers):
    client.put("/bot-settings/me", json={"enabled": True, "risk_pct": 2.0}, headers=member_headers)
    r = client.put("/bot-settings/me", json={"risk_pct": 3.0}, headers=member_headers)
    assert r.json()["enabled"] is True
    assert r.json()["risk_pct"] == 3.0


def test_rotate_api_key_returns_a_new_key(client, member_headers):
    r1 = client.post("/bot-settings/me/rotate-key", headers=member_headers)
    r2 = client.post("/bot-settings/me/rotate-key", headers=member_headers)
    assert r1.status_code == 200
    assert r1.json()["api_key"] != r2.json()["api_key"]
    assert len(r1.json()["api_key"]) == 64
