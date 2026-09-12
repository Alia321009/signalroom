"""DB helper functions -- the only layer that touches the ORM directly,
same split as the trading-bot project's engine/persistence.py."""
from __future__ import annotations

import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import auth as auth_module
from app.models import BotSettings, Call, CallExecution, Subscription, SubscriptionEvent, User
from app.schemas import BotSettingsUpdateRequest, CallCreateRequest, CallUpdateRequest, ExecutionReportRequest


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def get_or_create_subscription(session: Session, user_id: int) -> Subscription:
    sub = session.query(Subscription).filter_by(user_id=user_id).first()
    if sub is not None:
        return sub
    sub = Subscription(user_id=user_id, tier="none", status="pending")
    session.add(sub)
    session.flush()
    return sub


def record_subscription_event(
    session: Session, user_id: int, event_type: str, message: str, payload: dict | None = None
) -> None:
    session.add(SubscriptionEvent(user_id=user_id, event_type=event_type, message=message, payload=payload or {}))


def create_call(session: Session, created_by: int, data: CallCreateRequest) -> Call:
    call = Call(
        created_by=created_by, symbol=data.symbol.upper(), direction=data.direction,
        entry=data.entry, sl=data.sl, tp1=data.tp1, tp2=data.tp2, tp3=data.tp3,
        valid_until=data.valid_until, notes=data.notes, status="pending",
    )
    session.add(call)
    session.flush()
    return call


CLOSED_STATUSES = {"tp1_hit", "tp2_hit", "tp3_hit", "sl_hit", "expired", "cancelled"}


def update_call(session: Session, call: Call, data: CallUpdateRequest) -> Call:
    if data.status is not None:
        call.status = data.status
        if data.status in CLOSED_STATUSES and call.closed_at is None:
            call.closed_at = _utcnow()
    if data.outcome_r is not None:
        call.outcome_r = data.outcome_r
    if data.notes is not None:
        call.notes = data.notes
    session.flush()
    return call


def list_calls(session: Session, limit: int = 100) -> list[Call]:
    return list(session.query(Call).order_by(Call.created_at.desc()).limit(limit))


def list_public_closed_calls(session: Session, limit: int = 100) -> list[Call]:
    return list(
        session.query(Call)
        .filter(Call.status.in_(CLOSED_STATUSES))
        .order_by(Call.closed_at.desc())
        .limit(limit)
    )


def get_or_create_bot_settings(session: Session, user_id: int) -> BotSettings:
    settings_row = session.query(BotSettings).filter_by(user_id=user_id).first()
    if settings_row is not None:
        return settings_row
    next_magic = (session.query(func.max(BotSettings.magic)).scalar() or 90000000) + 1
    settings_row = BotSettings(
        user_id=user_id, enabled=False, magic=next_magic, api_key=auth_module.generate_api_key(),
    )
    session.add(settings_row)
    session.flush()
    return settings_row


def update_bot_settings(session: Session, settings_row: BotSettings, data: BotSettingsUpdateRequest) -> BotSettings:
    if data.enabled is not None:
        settings_row.enabled = data.enabled
    if data.risk_pct is not None:
        settings_row.risk_pct = data.risk_pct
    if data.max_daily_loss_pct is not None:
        settings_row.max_daily_loss_pct = data.max_daily_loss_pct
    if data.symbols is not None:
        settings_row.symbols = [s.upper() for s in data.symbols]
    session.flush()
    return settings_row


def rotate_api_key(session: Session, settings_row: BotSettings) -> str:
    new_key = auth_module.generate_api_key()
    settings_row.api_key = new_key
    session.flush()
    return new_key


def record_execution_report(
    session: Session, user_id: int, report: ExecutionReportRequest
) -> CallExecution:
    execution = CallExecution(
        call_id=report.call_id, user_id=user_id, ticket=report.ticket, volume=report.volume,
        status=report.status, profit=report.profit, close_reason=report.close_reason,
        executed_at=_utcnow() if report.status == "filled" else None,
    )
    session.add(execution)

    if report.status == "filled":
        sub = get_or_create_subscription(session, user_id)
        sub.last_trade_activity_at = _utcnow()

    session.flush()
    return execution


def get_user_by_api_key(session: Session, api_key: str) -> User | None:
    settings_row = session.query(BotSettings).filter_by(api_key=api_key).first()
    if settings_row is None:
        return None
    return session.get(User, settings_row.user_id)


def check_inactivity_revocation(subscription: Subscription, inactivity_days: int) -> bool:
    """True if this member's last trade activity is stale enough to flag
    for revocation (spec: growthclubpk.com's own stated policy, "no
    trading for 2 weeks may revoke access"). Read-only check -- callers
    decide whether/how to act on it (see app/routers/members.py's
    admin-facing flag, not an automatic silent revoke)."""
    if subscription.last_trade_activity_at is None:
        return False
    age = _utcnow() - subscription.last_trade_activity_at
    return age.days >= inactivity_days
