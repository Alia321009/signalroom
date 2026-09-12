"""
The local executor: runs on a member's own machine, next to their own
already-logged-in MT5 terminal. Polls SignalRoom for the admin's calls and
mirrors them onto the member's own account, sized by their own risk_pct.

Simplification, stated plainly rather than silently assumed: every call is
executed as a MARKET order the moment it's first seen (not a pending/limit
order sitting at the call's entry price waiting to be touched). Real
signal-copier products often do the latter; building full pending-order
lifecycle (place limit -> wait -> maybe cancel on expiry -> maybe modify)
is real additional scope this V1 doesn't cover -- see README's "known
limitations". A call's own `entry` field is still recorded and reported
back, so the gap between requested entry and actual fill price is visible
in the data even though the executor doesn't enforce it.

Run: python -m executor.run  (from the signalroom root, with
requirements/executor.txt installed and MT5 already logged in).
"""
from __future__ import annotations

import time

import httpx

from app.logging_config import configure_logging, get_logger
from executor import mt5_client
from executor.config import ExecutorSettings, get_executor_settings
from executor.sizing import compute_position_size, plan_order_legs
from executor.state import CallState, ExecutorState, load_state, save_state

log = get_logger(__name__)

OPENABLE_STATUSES = {"pending", "active"}
CLOSED_STATUSES = {"tp1_hit", "tp2_hit", "tp3_hit", "sl_hit", "expired", "cancelled"}


def fetch_settings(client: httpx.Client) -> dict:
    r = client.get("/executor/settings")
    r.raise_for_status()
    return r.json()


def fetch_calls(client: httpx.Client, since: str | None) -> list[dict]:
    params = {"since": since} if since else {}
    r = client.get("/executor/calls", params=params)
    r.raise_for_status()
    return r.json()


def report(client: httpx.Client, call_id: int, status: str, ticket: str | None = None,
           volume: float | None = None, profit: float | None = None, close_reason: str | None = None) -> None:
    try:
        client.post("/executor/calls/report", json={
            "call_id": call_id, "ticket": ticket, "volume": volume,
            "status": status, "profit": profit, "close_reason": close_reason,
        })
    except httpx.HTTPError:
        log.exception("report_failed", call_id=call_id, status=status)


def handle_new_call(client: httpx.Client, call: dict, bot_settings: dict) -> CallState:
    symbol = call["symbol"]
    try:
        symbol_info = mt5_client.get_symbol_info(symbol)
        balance = mt5_client.get_balance()
    except RuntimeError:
        log.exception("symbol_or_account_lookup_failed", symbol=symbol)
        report(client, call["id"], status="failed", close_reason="symbol_or_account_lookup_failed")
        return CallState(status=call["status"], tickets=[])

    total_volume = compute_position_size(
        balance=balance, risk_pct=bot_settings["risk_pct"], entry=call["entry"], sl=call["sl"],
        tick_value=symbol_info.tick_value, tick_size=symbol_info.tick_size,
        volume_min=symbol_info.volume_min, volume_max=symbol_info.volume_max, volume_step=symbol_info.volume_step,
    )
    if total_volume <= 0:
        log.warning("zero_volume_skipping", call_id=call["id"], symbol=symbol)
        report(client, call["id"], status="skipped", close_reason="zero_volume")
        return CallState(status=call["status"], tickets=[])

    legs = plan_order_legs(
        call["tp1"], call["tp2"], call["tp3"],
        total_volume, symbol_info.volume_min, symbol_info.volume_step,
    )

    tickets: list[str] = []
    for leg in legs:
        ticket = mt5_client.open_order(
            symbol=symbol, direction=call["direction"], volume=leg.volume, sl=call["sl"],
            tp=leg.take_profit, magic=bot_settings["magic"], call_id=call["id"],
        )
        if ticket is not None:
            tickets.append(ticket)
            report(client, call["id"], status="filled", ticket=ticket, volume=leg.volume)
        else:
            report(client, call["id"], status="failed", volume=leg.volume)

    return CallState(status=call["status"], tickets=tickets)


def handle_closed_call(client: httpx.Client, call: dict, existing: CallState) -> CallState:
    for ticket in existing.tickets:
        profit = mt5_client.get_ticket_profit(ticket)
        closed_ok = mt5_client.close_ticket(ticket)
        if closed_ok:
            report(client, call["id"], status="filled", ticket=ticket, profit=profit, close_reason=call["status"])
        else:
            log.error("failed_to_close_ticket", ticket=ticket, call_id=call["id"])
    return CallState(status=call["status"], tickets=[])


def run_once(client: httpx.Client, state: ExecutorState) -> ExecutorState:
    bot_settings = fetch_settings(client)
    if not bot_settings["enabled"]:
        return state

    calls = fetch_calls(client, state.cursor)
    for call in calls:
        existing = state.calls.get(call["id"])

        if call["status"] in OPENABLE_STATUSES and existing is None:
            state.calls[call["id"]] = handle_new_call(client, call, bot_settings)
        elif call["status"] in CLOSED_STATUSES and existing is not None and existing.tickets:
            state.calls[call["id"]] = handle_closed_call(client, call, existing)
        elif existing is not None:
            existing.status = call["status"]

        state.cursor = call["updated_at"]

    return state


def run_forever(settings: ExecutorSettings) -> None:
    if not mt5_client.connect():
        log.error("mt5_connect_failed_exiting")
        return

    state = load_state(settings.state_file)
    log.info("executor_starting", api_base_url=settings.api_base_url)

    try:
        while True:
            try:
                with httpx.Client(base_url=settings.api_base_url, headers={"X-Api-Key": settings.api_key}, timeout=15.0) as client:
                    state = run_once(client, state)
                    save_state(settings.state_file, state)
            except httpx.HTTPError:
                log.exception("poll_cycle_failed")
            time.sleep(settings.poll_interval_seconds)
    finally:
        mt5_client.disconnect()


def main() -> None:
    settings = get_executor_settings()
    # app.logging_config just needs .log_level/.environment -- app.config's
    # Settings already has that shape, reused here rather than duplicating
    # a second logging-config type for one field pair.
    from app.config import Settings as _LoggingSettingsShape

    configure_logging(_LoggingSettingsShape(_env_file=None))
    run_forever(settings)


if __name__ == "__main__":
    main()
