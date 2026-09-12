import datetime


def _valid_until(hours=4):
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=hours)).isoformat()


def _call_payload(**overrides):
    payload = {
        "symbol": "xauusd",
        "direction": "buy",
        "entry": 4220.0,
        "sl": 4210.0,
        "tp1": 4230.0,
        "tp2": 4240.0,
        "tp3": None,
        "valid_until": _valid_until(),
        "notes": "London session breakout",
    }
    payload.update(overrides)
    return payload


def test_admin_can_create_a_call(client, admin_headers):
    r = client.post("/calls", json=_call_payload(), headers=admin_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["symbol"] == "XAUUSD"  # normalized to uppercase
    assert body["status"] == "pending"
    assert body["tp3"] is None


def test_member_cannot_create_a_call(client, member_headers):
    r = client.post("/calls", json=_call_payload(), headers=member_headers)
    assert r.status_code == 403


def test_member_can_list_calls(client, admin_headers, member_headers):
    client.post("/calls", json=_call_payload(), headers=admin_headers)
    r = client.get("/calls", headers=member_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_unauthenticated_request_cannot_list_calls(client):
    r = client.get("/calls")
    assert r.status_code == 401


def test_get_single_call(client, admin_headers, member_headers):
    created = client.post("/calls", json=_call_payload(), headers=admin_headers).json()
    r = client.get(f"/calls/{created['id']}", headers=member_headers)
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_get_call_404_for_unknown_id(client, member_headers):
    r = client.get("/calls/99999", headers=member_headers)
    assert r.status_code == 404


def test_admin_can_update_call_status_to_a_closed_state(client, admin_headers):
    created = client.post("/calls", json=_call_payload(), headers=admin_headers).json()
    r = client.patch(f"/calls/{created['id']}", json={"status": "tp1_hit", "outcome_r": 2.0}, headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "tp1_hit"
    assert body["outcome_r"] == 2.0
    assert body["closed_at"] is not None


def test_updating_to_a_non_closed_status_does_not_set_closed_at(client, admin_headers):
    created = client.post("/calls", json=_call_payload(), headers=admin_headers).json()
    r = client.patch(f"/calls/{created['id']}", json={"status": "active"}, headers=admin_headers)
    assert r.json()["closed_at"] is None


def test_member_cannot_update_a_call(client, admin_headers, member_headers):
    created = client.post("/calls", json=_call_payload(), headers=admin_headers).json()
    r = client.patch(f"/calls/{created['id']}", json={"status": "cancelled"}, headers=member_headers)
    assert r.status_code == 403


def test_update_call_404_for_unknown_id(client, admin_headers):
    r = client.patch("/calls/99999", json={"status": "cancelled"}, headers=admin_headers)
    assert r.status_code == 404


def test_public_track_record_requires_no_auth(client, admin_headers):
    created = client.post("/calls", json=_call_payload(), headers=admin_headers).json()
    client.patch(f"/calls/{created['id']}", json={"status": "tp1_hit", "outcome_r": 1.5}, headers=admin_headers)

    r = client.get("/calls/public")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["outcome_r"] == 1.5


def test_public_track_record_excludes_still_open_calls(client, admin_headers):
    client.post("/calls", json=_call_payload(), headers=admin_headers)  # left pending
    r = client.get("/calls/public")
    assert r.json() == []
