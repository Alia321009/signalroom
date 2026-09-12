"""
Endpoints the LOCAL executor (executor/run.py, running on a member's own
machine next to their own logged-in MT5 terminal) polls and reports to.
Authenticated via X-Api-Key (app/deps.py's get_executor_user), not the web
JWT -- see BotSettings.api_key's docstring for why.
"""
from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import persistence
from app.deps import get_db, get_executor_user
from app.models import Call, User
from app.schemas import BotSettingsResponse, ExecutionReportRequest, ExecutorCallResponse

router = APIRouter(prefix="/executor", tags=["executor"])


@router.get("/settings", response_model=BotSettingsResponse)
def get_my_settings(user: User = Depends(get_executor_user), session: Session = Depends(get_db)) -> BotSettingsResponse:
    """The executor's own risk/symbol config, fetched via its API key --
    it has no JWT and can't hit /bot-settings/me (that route requires the
    web login flow)."""
    settings_row = persistence.get_or_create_bot_settings(session, user.id)
    return BotSettingsResponse(
        enabled=settings_row.enabled, risk_pct=settings_row.risk_pct,
        max_daily_loss_pct=settings_row.max_daily_loss_pct, symbols=settings_row.symbols, magic=settings_row.magic,
    )


@router.get("/calls", response_model=list[ExecutorCallResponse])
def poll_calls(
    since: datetime.datetime | None = None,
    user: User = Depends(get_executor_user),
    session: Session = Depends(get_db),
) -> list[ExecutorCallResponse]:
    """New calls AND status changes to existing ones since `since`
    (updated_at, not created_at -- the executor needs to hear about a call
    moving to sl_hit/tp_hit just as much as a brand-new one) -- an empty
    list whenever the bot is disabled, so a member who never turned it on
    doesn't need special-cased client behavior."""
    settings_row = persistence.get_or_create_bot_settings(session, user.id)
    if not settings_row.enabled:
        return []

    query = session.query(Call)
    if since is not None:
        query = query.filter(Call.updated_at > since)
    if settings_row.symbols:
        query = query.filter(Call.symbol.in_(settings_row.symbols))

    calls = query.order_by(Call.updated_at.asc()).all()
    return [
        ExecutorCallResponse(
            id=c.id, symbol=c.symbol, direction=c.direction, entry=c.entry, sl=c.sl,
            tp1=c.tp1, tp2=c.tp2, tp3=c.tp3, valid_until=c.valid_until, status=c.status,
            updated_at=c.updated_at,
        )
        for c in calls
    ]


@router.post("/calls/report", status_code=204, response_model=None)
def report_execution(
    body: ExecutionReportRequest, user: User = Depends(get_executor_user), session: Session = Depends(get_db)
) -> None:
    persistence.record_execution_report(session, user.id, body)
