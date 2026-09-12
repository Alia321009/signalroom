"""Tests for executor/run.py's orchestration (run_once and friends) --
mirrors the trading-bot project's own split of a pure-ish decision core
(run_tick there, run_once here) from the stateful wrapper that actually
connects to anything (EngineLoop there, run_forever here). httpx is
exercised against a MockTransport (real request/response shapes, no
network); MT5 itself is monkeypatched -- there's no fake terminal to test
against, same reasoning as mt5_client.py's own module docstring."""
from __future__ import annotations

import json

import httpx
import pytest

import executor.run as run_module
from executor.mt5_client import SymbolInfo
from executor.sizing import OrderLeg
from executor.state import CallState, ExecutorState


SYMBOL_INFO = SymbolInfo(tick_value=1.0, tick_size=0.0001, volume_min=0.01, volume_max=100.0, volume_step=0.01, point=0.0001)


def _call(id=1, status="pending", symbol="EURUSD", tp2=None, tp3=None, updated_at="2026-01-01T00:00:01Z"):
    return {
        "id": id, "symbol": symbol, "direction": "buy", "entry": 1.1000, "sl": 1.0950,
        "tp1": 1.1050, "tp2": tp2, "tp3": tp3, "valid_until": "2026-01-01T04:00:00Z",
        "status": status, "updated_at": updated_at,
    }


def _client_for(handler) -> httpx.Client:
    return httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler))


def test_run_once_does_nothing_when_bot_disabled(monkeypatch):
    calls_seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls_seen.append(request.url.path)
        if request.url.path == "/executor/settings":
            return httpx.Response(200, json={"enabled": False, "risk_pct": 1.0, "max_daily_loss_pct": 3.0, "symbols": [], "magic": 1})
        raise AssertionError(f"should not have called {request.url.path}")

    state = run_module.run_once(_client_for(handler), ExecutorState())
    assert state.calls == {}
    assert "/executor/calls" not in calls_seen


def test_run_once_opens_a_position_for_a_new_call(monkeypatch):
    reports = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/executor/settings":
            return httpx.Response(200, json={"enabled": True, "risk_pct": 1.0, "max_daily_loss_pct": 3.0, "symbols": [], "magic": 777})
        if request.url.path == "/executor/calls":
            return httpx.Response(200, json=[_call()])
        if request.url.path == "/executor/calls/report":
            reports.append(json.loads(request.content))
            return httpx.Response(204)
        raise AssertionError(request.url.path)

    monkeypatch.setattr(run_module.mt5_client, "get_symbol_info", lambda symbol: SYMBOL_INFO)
    monkeypatch.setattr(run_module.mt5_client, "get_balance", lambda: 10_000.0)
    monkeypatch.setattr(run_module.mt5_client, "open_order", lambda **kwargs: "555")

    state = run_module.run_once(_client_for(handler), ExecutorState())

    assert state.calls[1].tickets == ["555"]
    assert state.cursor == "2026-01-01T00:00:01Z"
    assert len(reports) == 1
    assert reports[0]["status"] == "filled"
    assert reports[0]["ticket"] == "555"


def test_run_once_splits_into_multiple_legs_for_multiple_targets(monkeypatch):
    tickets_opened = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/executor/settings":
            return httpx.Response(200, json={"enabled": True, "risk_pct": 1.0, "max_daily_loss_pct": 3.0, "symbols": [], "magic": 1})
        if request.url.path == "/executor/calls":
            return httpx.Response(200, json=[_call(tp2=1.1100, tp3=1.1150)])
        if request.url.path == "/executor/calls/report":
            return httpx.Response(204)
        raise AssertionError(request.url.path)

    def fake_open_order(**kwargs):
        tickets_opened.append(kwargs.get("tp"))
        return f"ticket-{len(tickets_opened)}"

    monkeypatch.setattr(run_module.mt5_client, "get_symbol_info", lambda symbol: SYMBOL_INFO)
    monkeypatch.setattr(run_module.mt5_client, "get_balance", lambda: 100_000.0)
    monkeypatch.setattr(run_module.mt5_client, "open_order", fake_open_order)

    state = run_module.run_once(_client_for(handler), ExecutorState())

    assert len(state.calls[1].tickets) == 3  # one leg per TP target


def test_run_once_skips_a_call_with_degenerate_zero_stop_distance(monkeypatch):
    """compute_position_size deliberately floors to volume_min for a
    merely-small balance (a broker's minimum lot is already small;
    refusing entirely would leave small accounts unable to trade at
    all -- see test_executor_sizing.py). The genuine zero-volume case is
    degenerate call data instead: entry == sl gives a zero stop distance,
    which no position size can meaningfully represent."""
    reports = []

    degenerate_call = _call()
    degenerate_call["sl"] = degenerate_call["entry"]  # zero stop distance

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/executor/settings":
            return httpx.Response(200, json={"enabled": True, "risk_pct": 1.0, "max_daily_loss_pct": 3.0, "symbols": [], "magic": 1})
        if request.url.path == "/executor/calls":
            return httpx.Response(200, json=[degenerate_call])
        if request.url.path == "/executor/calls/report":
            reports.append(json.loads(request.content))
            return httpx.Response(204)
        raise AssertionError(request.url.path)

    monkeypatch.setattr(run_module.mt5_client, "get_symbol_info", lambda symbol: SYMBOL_INFO)
    monkeypatch.setattr(run_module.mt5_client, "get_balance", lambda: 10_000.0)
    opened = []
    monkeypatch.setattr(run_module.mt5_client, "open_order", lambda **kwargs: opened.append(1))

    run_module.run_once(_client_for(handler), ExecutorState())

    assert opened == []
    assert reports[0]["status"] == "skipped"


def test_run_once_reports_failed_when_order_send_fails(monkeypatch):
    reports = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/executor/settings":
            return httpx.Response(200, json={"enabled": True, "risk_pct": 1.0, "max_daily_loss_pct": 3.0, "symbols": [], "magic": 1})
        if request.url.path == "/executor/calls":
            return httpx.Response(200, json=[_call()])
        if request.url.path == "/executor/calls/report":
            reports.append(json.loads(request.content))
            return httpx.Response(204)
        raise AssertionError(request.url.path)

    monkeypatch.setattr(run_module.mt5_client, "get_symbol_info", lambda symbol: SYMBOL_INFO)
    monkeypatch.setattr(run_module.mt5_client, "get_balance", lambda: 10_000.0)
    monkeypatch.setattr(run_module.mt5_client, "open_order", lambda **kwargs: None)

    state = run_module.run_once(_client_for(handler), ExecutorState())

    assert state.calls[1].tickets == []
    assert reports[0]["status"] == "failed"


def test_run_once_closes_tickets_for_a_call_that_transitions_to_closed(monkeypatch):
    reports = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/executor/settings":
            return httpx.Response(200, json={"enabled": True, "risk_pct": 1.0, "max_daily_loss_pct": 3.0, "symbols": [], "magic": 1})
        if request.url.path == "/executor/calls":
            return httpx.Response(200, json=[_call(status="tp1_hit")])
        if request.url.path == "/executor/calls/report":
            reports.append(json.loads(request.content))
            return httpx.Response(204)
        raise AssertionError(request.url.path)

    monkeypatch.setattr(run_module.mt5_client, "close_ticket", lambda ticket: True)
    monkeypatch.setattr(run_module.mt5_client, "get_ticket_profit", lambda ticket: 42.5)

    state = ExecutorState(calls={1: CallState(status="pending", tickets=["999"])})
    state = run_module.run_once(_client_for(handler), state)

    assert state.calls[1].tickets == []
    assert reports[0]["status"] == "filled"
    assert reports[0]["profit"] == 42.5
    assert reports[0]["close_reason"] == "tp1_hit"


def test_run_once_ignores_a_closed_call_it_never_opened(monkeypatch):
    """A call that closed before this member's bot was ever enabled --
    nothing to close, and must not crash."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/executor/settings":
            return httpx.Response(200, json={"enabled": True, "risk_pct": 1.0, "max_daily_loss_pct": 3.0, "symbols": [], "magic": 1})
        if request.url.path == "/executor/calls":
            return httpx.Response(200, json=[_call(status="expired")])
        raise AssertionError(request.url.path)

    state = run_module.run_once(_client_for(handler), ExecutorState())
    assert 1 not in state.calls or state.calls[1].tickets == []


def test_run_once_updates_tracked_status_without_action_on_a_benign_transition(monkeypatch):
    """pending -> active with no MT5 action needed (already filled) --
    just keep the local record's status current."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/executor/settings":
            return httpx.Response(200, json={"enabled": True, "risk_pct": 1.0, "max_daily_loss_pct": 3.0, "symbols": [], "magic": 1})
        if request.url.path == "/executor/calls":
            return httpx.Response(200, json=[_call(status="active")])
        raise AssertionError(request.url.path)

    state = ExecutorState(calls={1: CallState(status="pending", tickets=["1"])})
    state = run_module.run_once(_client_for(handler), state)

    assert state.calls[1].status == "active"
    assert state.calls[1].tickets == ["1"]  # untouched
