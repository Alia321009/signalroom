import datetime


def _valid_until(hours=4):
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=hours)).isoformat()


def _call_payload(symbol="XAUUSD", **overrides):
    payload = {
        "symbol": symbol, "direction": "buy", "entry": 4220.0, "sl": 4210.0,
        "tp1": 4230.0, "tp2": None, "tp3": None, "valid_until": _valid_until(), "notes": None,
    }
    payload.update(overrides)
    return payload


def _get_api_key(client, member_headers) -> str:
    return client.post("/bot-settings/me/rotate-key", headers=member_headers).json()["api_key"]


def test_poll_returns_empty_when_bot_disabled(client, admin_headers, member_headers):
    client.post("/calls", json=_call_payload(), headers=admin_headers)
    api_key = _get_api_key(client, member_headers)

    r = client.get("/executor/calls", headers={"X-Api-Key": api_key})
    assert r.status_code == 200
    assert r.json() == []


def test_poll_returns_calls_once_bot_enabled(client, admin_headers, member_headers):
    client.put("/bot-settings/me", json={"enabled": True}, headers=member_headers)
    api_key = _get_api_key(client, member_headers)
    client.post("/calls", json=_call_payload(), headers=admin_headers)

    r = client.get("/executor/calls", headers={"X-Api-Key": api_key})
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["symbol"] == "XAUUSD"


def test_poll_filters_to_the_symbol_whitelist(client, admin_headers, member_headers):
    client.put("/bot-settings/me", json={"enabled": True, "symbols": ["EURUSD"]}, headers=member_headers)
    api_key = _get_api_key(client, member_headers)
    client.post("/calls", json=_call_payload(symbol="XAUUSD"), headers=admin_headers)
    client.post("/calls", json=_call_payload(symbol="EURUSD"), headers=admin_headers)

    r = client.get("/executor/calls", headers={"X-Api-Key": api_key})
    symbols = [c["symbol"] for c in r.json()]
    assert symbols == ["EURUSD"]


def test_poll_with_empty_whitelist_returns_all_symbols(client, admin_headers, member_headers):
    client.put("/bot-settings/me", json={"enabled": True, "symbols": []}, headers=member_headers)
    api_key = _get_api_key(client, member_headers)
    client.post("/calls", json=_call_payload(symbol="XAUUSD"), headers=admin_headers)
    client.post("/calls", json=_call_payload(symbol="EURUSD"), headers=admin_headers)

    r = client.get("/executor/calls", headers={"X-Api-Key": api_key})
    assert len(r.json()) == 2


def test_poll_since_only_returns_calls_updated_after_the_cursor(client, admin_headers, member_headers):
    client.put("/bot-settings/me", json={"enabled": True}, headers=member_headers)
    api_key = _get_api_key(client, member_headers)

    first = client.post("/calls", json=_call_payload(), headers=admin_headers).json()
    # Use the first call's own updated_at as the cursor rather than a
    # wall-clock capture in between -- a timestamp taken independently in
    # the test only has a thin, load-dependent margin over the two calls
    # either side of it (this flaked under full-suite load with as little
    # as sub-millisecond separation). The first call's real stored
    # timestamp is guaranteed strictly earlier than the second call's.
    cursor = first["updated_at"]
    client.post("/calls", json=_call_payload(symbol="EURUSD"), headers=admin_headers)

    r = client.get("/executor/calls", params={"since": cursor}, headers={"X-Api-Key": api_key})
    assert len(r.json()) == 1
    assert r.json()[0]["symbol"] == "EURUSD"


def test_get_settings_via_api_key_returns_the_members_own_bot_settings(client, member_headers):
    client.put("/bot-settings/me", json={"enabled": True, "risk_pct": 2.5, "symbols": ["XAUUSD"]}, headers=member_headers)
    api_key = _get_api_key(client, member_headers)

    r = client.get("/executor/settings", headers={"X-Api-Key": api_key})
    assert r.status_code == 200
    assert r.json()["enabled"] is True
    assert r.json()["risk_pct"] == 2.5
    assert r.json()["symbols"] == ["XAUUSD"]


def test_get_settings_rejects_missing_api_key(client):
    r = client.get("/executor/settings")
    assert r.status_code == 401


def test_poll_rejects_missing_api_key(client):
    r = client.get("/executor/calls")
    assert r.status_code == 401


def test_poll_rejects_invalid_api_key(client):
    r = client.get("/executor/calls", headers={"X-Api-Key": "not-a-real-key"})
    assert r.status_code == 401


def test_report_filled_execution_records_it_and_touches_last_activity(client, admin_headers, member_headers, session_factory):
    from app.models import User

    api_key = _get_api_key(client, member_headers)
    created = client.post("/calls", json=_call_payload(), headers=admin_headers).json()

    r = client.post(
        "/executor/calls/report",
        json={"call_id": created["id"], "ticket": "12345", "volume": 0.1, "status": "filled"},
        headers={"X-Api-Key": api_key},
    )
    assert r.status_code == 204

    with session_factory() as session:
        member = session.query(User).filter_by(email="member@signalroom.test").first()
        assert member.subscription.last_trade_activity_at is not None


def test_report_skipped_execution_does_not_touch_last_activity(client, admin_headers, member_headers, session_factory):
    from app.models import User

    api_key = _get_api_key(client, member_headers)
    created = client.post("/calls", json=_call_payload(), headers=admin_headers).json()

    client.post(
        "/executor/calls/report",
        json={"call_id": created["id"], "status": "skipped"},
        headers={"X-Api-Key": api_key},
    )

    with session_factory() as session:
        member = session.query(User).filter_by(email="member@signalroom.test").first()
        assert member.subscription.last_trade_activity_at is None
