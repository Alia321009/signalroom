"""
Thin MT5 integration layer -- the only file in executor/ that touches the
MetaTrader5 package directly. Attaches to whatever terminal is ALREADY
running and logged in on this machine (MetaTrader5.initialize() with no
credentials does exactly that -- it does not log in on its own, and this
script never asks for or stores a broker password). Same "thin adapter,
no business logic" split as the trading-bot project's
engine/adapters/mt5_adapter.py; this file is intentionally not
unit-tested (no fake MT5 terminal to test against) -- see README's
testing section.
"""
from __future__ import annotations

from dataclasses import dataclass

import MetaTrader5 as mt5

from app.logging_config import get_logger

log = get_logger(__name__)

MAGIC_COMMENT_PREFIX = "signalroom-call-"


@dataclass
class SymbolInfo:
    tick_value: float
    tick_size: float
    volume_min: float
    volume_max: float
    volume_step: float
    point: float


def connect() -> bool:
    if not mt5.initialize():
        log.error("mt5_initialize_failed", error=mt5.last_error())
        return False
    return True


def disconnect() -> None:
    mt5.shutdown()


def get_balance() -> float:
    info = mt5.account_info()
    if info is None:
        raise RuntimeError(f"account_info() returned None: {mt5.last_error()}")
    return info.balance


def get_symbol_info(symbol: str) -> SymbolInfo:
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"symbol_info({symbol}) returned None: {mt5.last_error()}")
    if not info.visible:
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"symbol_select({symbol}, True) failed: {mt5.last_error()}")
        info = mt5.symbol_info(symbol)
    return SymbolInfo(
        tick_value=info.trade_tick_value, tick_size=info.trade_tick_size or info.point,
        volume_min=info.volume_min, volume_max=info.volume_max, volume_step=info.volume_step, point=info.point,
    )


def open_order(symbol: str, direction: str, volume: float, sl: float, tp: float, magic: int, call_id: int) -> str | None:
    """Places a market order. Returns the ticket as a string, or None on
    failure (logged, never raised -- one failed leg of a multi-target call
    should not crash the whole poll cycle; the caller decides whether to
    report it back as 'failed')."""
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        log.error("no_tick_data", symbol=symbol)
        return None

    order_type = mt5.ORDER_TYPE_BUY if direction == "buy" else mt5.ORDER_TYPE_SELL
    price = tick.ask if direction == "buy" else tick.bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "magic": magic,
        "comment": f"{MAGIC_COMMENT_PREFIX}{call_id}"[:31],  # MT5 comment field is capped at 31 chars
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        log.error("order_send_failed", symbol=symbol, retcode=getattr(result, "retcode", None), error=mt5.last_error())
        return None
    return str(result.order)


def close_ticket(ticket: str) -> bool:
    """Closes one position by ticket. True on success or if it's already
    gone (closed by broker-side SL/TP already, e.g.) -- only False on an
    actual close failure while the position still exists."""
    positions = mt5.positions_get(ticket=int(ticket))
    if not positions:
        return True  # already closed -- nothing to do, not a failure

    position = positions[0]
    tick = mt5.symbol_info_tick(position.symbol)
    if tick is None:
        return False

    close_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    price = tick.bid if close_type == mt5.ORDER_TYPE_SELL else tick.ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": position.symbol,
        "volume": position.volume,
        "type": close_type,
        "position": position.ticket,
        "price": price,
        "magic": position.magic,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        log.error("close_failed", ticket=ticket, retcode=getattr(result, "retcode", None), error=mt5.last_error())
        return False
    return True


def get_ticket_profit(ticket: str) -> float | None:
    """Profit for an OPEN position. Returns None if it's already closed
    (profit for a closed deal isn't available from positions_get -- a
    fuller implementation would use history_deals_get; left as a known
    gap, see README)."""
    positions = mt5.positions_get(ticket=int(ticket))
    if not positions:
        return None
    return positions[0].profit
