"""Tests for executor/sizing.py -- pure functions, no MT5 needed."""
import pytest

from executor.sizing import (
    OrderLeg,
    compute_position_size,
    plan_order_legs,
    round_to_step,
    split_targets,
    split_volume,
)


def test_split_targets_includes_only_set_levels():
    assert split_targets(1.0, None, None) == [1.0]
    assert split_targets(1.0, 2.0, None) == [1.0, 2.0]
    assert split_targets(1.0, 2.0, 3.0) == [1.0, 2.0, 3.0]


def test_round_to_step_basic():
    assert round_to_step(0.037, 0.01) == 0.04
    assert round_to_step(0.033, 0.01) == 0.03


def test_round_to_step_with_zero_step_returns_value_unchanged():
    assert round_to_step(1.2345, 0) == 1.2345


def test_split_volume_single_leg_returns_whole_amount():
    assert split_volume(0.30, 1, volume_min=0.01, volume_step=0.01) == [0.30]


def test_split_volume_splits_evenly_across_legs():
    legs = split_volume(0.30, 3, volume_min=0.01, volume_step=0.01)
    assert legs == [0.10, 0.10, 0.10]
    assert round(sum(legs), 8) == pytest.approx(0.30)


def test_split_volume_puts_rounding_remainder_on_first_leg():
    legs = split_volume(0.10, 3, volume_min=0.01, volume_step=0.01)
    assert round(sum(legs), 8) == pytest.approx(0.10)
    assert legs[0] >= legs[1]


def test_split_volume_collapses_when_below_minimum_per_leg():
    # 0.02 total split 3 ways at min 0.01 -> only 2 legs actually fit
    legs = split_volume(0.02, 3, volume_min=0.01, volume_step=0.01)
    assert len(legs) == 2
    assert all(leg >= 0.01 for leg in legs)


def test_split_volume_recurses_when_rounding_remainder_pushes_first_leg_below_minimum():
    # volume_min (0.005) smaller than volume_step (0.01): the upfront
    # capacity check (total < num_legs * volume_min) passes since
    # 0.02 >= 3*0.005, but rounding each leg up to the 0.01 step still
    # over-allocates (3 * 0.01 = 0.03 > 0.02 available), and the negative
    # remainder correction on leg[0] drives it to 0.0 -- below volume_min,
    # forcing a recursive collapse to fewer legs.
    legs = split_volume(0.02, 3, volume_min=0.005, volume_step=0.01)
    assert all(leg >= 0.005 for leg in legs)
    assert round(sum(legs), 8) <= 0.02 + 1e-9


def test_split_volume_collapses_to_one_leg_when_total_below_two_minimums():
    legs = split_volume(0.01, 3, volume_min=0.01, volume_step=0.01)
    assert legs == [0.01]


def test_compute_position_size_scales_with_risk_pct():
    small = compute_position_size(
        balance=10_000, risk_pct=1.0, entry=1.1000, sl=1.0950,
        tick_value=1.0, tick_size=0.0001, volume_min=0.01, volume_max=100.0, volume_step=0.01,
    )
    large = compute_position_size(
        balance=10_000, risk_pct=2.0, entry=1.1000, sl=1.0950,
        tick_value=1.0, tick_size=0.0001, volume_min=0.01, volume_max=100.0, volume_step=0.01,
    )
    assert large == pytest.approx(small * 2, rel=0.05)


def test_compute_position_size_respects_volume_min():
    volume = compute_position_size(
        balance=100, risk_pct=0.1, entry=1.1000, sl=1.0999,  # tiny risk amount, tiny stop
        tick_value=1.0, tick_size=0.0001, volume_min=0.01, volume_max=100.0, volume_step=0.01,
    )
    assert volume >= 0.01


def test_compute_position_size_respects_volume_max():
    volume = compute_position_size(
        balance=10_000_000, risk_pct=5.0, entry=1.1000, sl=1.0999,
        tick_value=1.0, tick_size=0.0001, volume_min=0.01, volume_max=50.0, volume_step=0.01,
    )
    assert volume <= 50.0


def test_compute_position_size_zero_stop_distance_returns_zero():
    volume = compute_position_size(
        balance=10_000, risk_pct=1.0, entry=1.1000, sl=1.1000,
        tick_value=1.0, tick_size=0.0001, volume_min=0.01, volume_max=100.0, volume_step=0.01,
    )
    assert volume == 0.0


def test_compute_position_size_zero_tick_value_returns_zero():
    volume = compute_position_size(
        balance=10_000, risk_pct=1.0, entry=1.1000, sl=1.0950,
        tick_value=0.0, tick_size=0.0001, volume_min=0.01, volume_max=100.0, volume_step=0.01,
    )
    assert volume == 0.0


def test_plan_order_legs_one_target():
    legs = plan_order_legs(tp1=1.11, tp2=None, tp3=None, total_volume=0.30, volume_min=0.01, volume_step=0.01)
    assert legs == [OrderLeg(volume=0.30, take_profit=1.11)]


def test_plan_order_legs_three_targets():
    legs = plan_order_legs(tp1=1.11, tp2=1.12, tp3=1.13, total_volume=0.30, volume_min=0.01, volume_step=0.01)
    assert len(legs) == 3
    assert [leg.take_profit for leg in legs] == [1.11, 1.12, 1.13]
    assert round(sum(leg.volume for leg in legs), 8) == pytest.approx(0.30)


def test_plan_order_legs_collapses_legs_when_volume_too_small_to_split():
    legs = plan_order_legs(tp1=1.11, tp2=1.12, tp3=1.13, total_volume=0.01, volume_min=0.01, volume_step=0.01)
    assert len(legs) == 1
    assert legs[0].take_profit == 1.11  # TP1 kept when forced to collapse to one leg
