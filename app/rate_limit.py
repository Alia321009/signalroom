"""In-memory login rate limiting: 5 attempts per 15 minutes per IP. Same
simple approach as the trading-bot project's api/rate_limit.py -- fine for
a single-process deployment; a real multi-instance deployment would need
this backed by Redis instead."""
from __future__ import annotations

import time

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 15 * 60

_attempts: dict[str, list[float]] = {}


def check_and_record(client_ip: str) -> bool:
    """Returns True if this attempt is allowed (and records it); False if
    the IP is already over the limit for this window."""
    now = time.monotonic()
    history = [t for t in _attempts.get(client_ip, []) if now - t < WINDOW_SECONDS]
    if len(history) >= MAX_ATTEMPTS:
        _attempts[client_ip] = history
        return False
    history.append(now)
    _attempts[client_ip] = history
    return True


def reset_all() -> None:
    _attempts.clear()
