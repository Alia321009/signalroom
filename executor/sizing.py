"""Pure, MT5-free sizing/planning logic for the local executor -- kept
separate from mt5_client.py (which does the actual order_send calls) so
this is fully unit-testable without a real terminal, same "pure core vs.
thin adapter" split as the trading-bot project's engine/risk/sizing.py
and engine/adapters/mt5_adapter.py."""
from __future__ import annotations

from dataclasses import dataclass


def split_targets(tp1: float, tp2: float | None, tp3: float | None) -> list[float]:
    """The TP levels actually set on this call, in order. A call always
    has tp1; tp2/tp3 are optional scale-out targets."""
    return [tp for tp in (tp1, tp2, tp3) if tp is not None]


def round_to_step(value: float, step: float) -> float:
    if step <= 0:
        return value
    return round(round(value / step) * step, 8)


def split_volume(total_volume: float, num_legs: int, volume_min: float, volume_step: float) -> list[float]:
    """Splits total_volume across num_legs equal-ish legs (one per TP
    target -- MT5 positions carry a single TP each, so hitting TP1/TP2/TP3
    means opening one sub-position per target and closing each at its own
    level). Every leg is rounded to volume_step and floored at volume_min;
    if that floor would make the legs sum to more than the requested
    total, legs collapse to fewer, larger ones instead of over-sizing."""
    if num_legs <= 1:
        return [round_to_step(total_volume, volume_step)]

    # Check capacity against the RAW total before rounding a per-leg size
    # -- rounding total_volume/num_legs can round UP to exactly
    # volume_min even when num_legs * volume_min actually exceeds the
    # total (e.g. 0.02 / 3 -> 0.00667 -> rounds to 0.01 at a 0.01 step,
    # but three 0.01 legs need 0.03, not the 0.02 available). Caught by a
    # test: that case produced a 0.0-sized first leg after the rounding
    # remainder was subtracted back out of it -- a zero-volume order a
    # real broker would simply reject.
    if total_volume < num_legs * volume_min:
        affordable_legs = max(1, int(total_volume // volume_min))
        return split_volume(total_volume, min(num_legs, affordable_legs), volume_min, volume_step)

    per_leg = round_to_step(total_volume / num_legs, volume_step)
    legs = [per_leg] * num_legs
    # Remainder (from rounding) goes to the first leg -- TP1 is the target
    # most likely to be hit, so that's the safest place for any leftover.
    remainder = round_to_step(total_volume - per_leg * num_legs, volume_step)
    if remainder != 0:
        legs[0] = round_to_step(legs[0] + remainder, volume_step)
        if legs[0] < volume_min:
            # The remainder correction pushed leg[0] back under the
            # minimum -- collapse to fewer legs rather than ship it.
            return split_volume(total_volume, num_legs - 1, volume_min, volume_step)
    return legs


def compute_position_size(
    balance: float,
    risk_pct: float,
    entry: float,
    sl: float,
    tick_value: float,
    tick_size: float,
    volume_min: float,
    volume_max: float,
    volume_step: float,
) -> float:
    """Risk-percent position sizing: risk this account's own risk_pct of
    its own balance on the distance from entry to stop. Same formula
    shape as the trading-bot project's engine/risk/sizing.py, reimplemented
    here rather than imported -- this is a deliberately independent
    project (see README), not one that reaches into a sibling repo's
    internals."""
    if tick_size <= 0 or tick_value <= 0:
        return 0.0

    risk_amount = balance * (risk_pct / 100.0)
    stop_distance = abs(entry - sl)
    if stop_distance <= 0:
        return 0.0

    ticks_at_risk = stop_distance / tick_size
    value_per_lot = ticks_at_risk * tick_value
    if value_per_lot <= 0:
        return 0.0

    raw_volume = risk_amount / value_per_lot
    volume = round_to_step(raw_volume, volume_step)
    return max(volume_min, min(volume_max, volume))


@dataclass(frozen=True)
class OrderLeg:
    volume: float
    take_profit: float


def plan_order_legs(
    tp1: float, tp2: float | None, tp3: float | None,
    total_volume: float, volume_min: float, volume_step: float,
) -> list[OrderLeg]:
    """The actual list of sub-orders to place for one call: one leg per
    TP target, each sized by split_volume."""
    targets = split_targets(tp1, tp2, tp3)
    volumes = split_volume(total_volume, len(targets), volume_min, volume_step)
    # split_volume can collapse to fewer legs than targets when volume_min
    # doesn't divide evenly -- pair volumes with the FIRST N targets (TP1
    # first, same "safest place for what a broker minimum can't split"
    # reasoning as the remainder placement above).
    return [OrderLeg(volume=v, take_profit=t) for v, t in zip(volumes, targets)]
