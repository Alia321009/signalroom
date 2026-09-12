"""WebSocket push: new/updated calls, pushed to every logged-in member's
dashboard in real time. Same shape as the trading-bot project's api/ws.py
-- authenticates on connect via ?token=, polls the DB for calls with
updated_at newer than the last one it already pushed. No per-member
filtering here (unlike the executor's own poll endpoint): every member
sees every call the instant it's posted or changes status, which is
exactly the product's own pitch ("live setups")."""
from __future__ import annotations

import asyncio
import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError

from app import auth as auth_module
from app.config import get_settings
from app.models import Call, User

router = APIRouter()

DEFAULT_POLL_INTERVAL_SECONDS = 1.0


async def _authenticate(websocket: WebSocket, session_factory) -> User | None:
    settings = get_settings()
    token = websocket.query_params.get("token")
    if not token:
        return None
    try:
        email = auth_module.decode_token(token, settings.jwt_secret, expected_type="access")
    except (JWTError, ValueError):
        return None
    with session_factory() as session:
        return session.query(User).filter_by(email=email).first()


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    session_factory = websocket.app.state.session_factory
    poll_interval = getattr(websocket.app.state, "ws_poll_interval", DEFAULT_POLL_INTERVAL_SECONDS)

    user = await _authenticate(websocket, session_factory)
    if user is None:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    last_seen = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=1)
    # created_at and updated_at are each stamped by a separate _utcnow()
    # call at flush time (SQLAlchemy Python-side column defaults), so they
    # differ by microseconds even on a brand-new row -- comparing them for
    # equality to detect "new" would almost never actually match. Track
    # which ids this connection has already pushed instead.
    seen_ids: set[int] = set()

    try:
        while True:
            with session_factory() as session:
                new_or_updated = (
                    session.query(Call).filter(Call.updated_at > last_seen).order_by(Call.updated_at.asc()).all()
                )
                for call in new_or_updated:
                    msg_type = "call_new" if call.id not in seen_ids else "call_updated"
                    seen_ids.add(call.id)
                    await websocket.send_json({
                        "type": msg_type,
                        "call": {
                            "id": call.id, "symbol": call.symbol, "direction": call.direction,
                            "entry": call.entry, "sl": call.sl, "tp1": call.tp1, "tp2": call.tp2, "tp3": call.tp3,
                            "valid_until": call.valid_until.isoformat(), "status": call.status,
                            "notes": call.notes, "outcome_r": call.outcome_r,
                        },
                    })
                    last_seen = call.updated_at

            await asyncio.sleep(poll_interval)
    except WebSocketDisconnect:
        return
