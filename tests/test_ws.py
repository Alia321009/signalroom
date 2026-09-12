import datetime

from fastapi.testclient import TestClient


def _valid_until(hours=4):
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=hours)).isoformat()


def test_ws_rejects_connection_with_no_token(app):
    with TestClient(app) as client:
        try:
            with client.websocket_connect("/ws"):
                assert False, "should have been rejected"
        except Exception:
            pass  # starlette raises on the 4401 close during handshake


def test_ws_pushes_a_newly_created_call(app, admin_headers, member_headers):
    with TestClient(app) as client:
        access_token = member_headers["Authorization"].removeprefix("Bearer ")
        with client.websocket_connect(f"/ws?token={access_token}") as ws:
            client.post(
                "/calls",
                json={
                    "symbol": "XAUUSD", "direction": "buy", "entry": 4220.0, "sl": 4210.0,
                    "tp1": 4230.0, "valid_until": _valid_until(), "notes": None,
                },
                headers=admin_headers,
            )
            msg = ws.receive_json()
            assert msg["type"] == "call_new"
            assert msg["call"]["symbol"] == "XAUUSD"


def test_ws_pushes_a_status_update_as_call_updated(app, admin_headers, member_headers):
    with TestClient(app) as client:
        created = client.post(
            "/calls",
            json={
                "symbol": "XAUUSD", "direction": "buy", "entry": 4220.0, "sl": 4210.0,
                "tp1": 4230.0, "valid_until": _valid_until(), "notes": None,
            },
            headers=admin_headers,
        ).json()

        access_token = member_headers["Authorization"].removeprefix("Bearer ")
        with client.websocket_connect(f"/ws?token={access_token}") as ws:
            # the connection's initial catch-up poll looks back ~1s (so a
            # call created in the same instant as connecting isn't missed),
            # so the pre-existing call arrives as call_new first -- drain it
            # before triggering the actual update this test targets.
            catch_up = ws.receive_json()
            assert catch_up["type"] == "call_new"

            client.patch(f"/calls/{created['id']}", json={"status": "active"}, headers=admin_headers)
            msg = ws.receive_json()
            assert msg["type"] == "call_updated"
            assert msg["call"]["status"] == "active"
