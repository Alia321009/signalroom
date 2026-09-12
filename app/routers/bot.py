"""A member's own auto-execution config for the local executor. The
api_key is returned ONLY from the rotate endpoint, right after
generation -- never from the plain GET, same "shown once" discipline as
the trading-bot project's admin TOTP enrollment URI."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import persistence
from app.deps import get_current_user, get_db
from app.models import User
from app.schemas import ApiKeyResponse, BotSettingsResponse, BotSettingsUpdateRequest

router = APIRouter(prefix="/bot-settings", tags=["bot"])


def _to_response(settings_row) -> BotSettingsResponse:
    return BotSettingsResponse(
        enabled=settings_row.enabled, risk_pct=settings_row.risk_pct,
        max_daily_loss_pct=settings_row.max_daily_loss_pct, symbols=settings_row.symbols, magic=settings_row.magic,
    )


@router.get("/me", response_model=BotSettingsResponse)
def get_my_bot_settings(user: User = Depends(get_current_user), session: Session = Depends(get_db)) -> BotSettingsResponse:
    return _to_response(persistence.get_or_create_bot_settings(session, user.id))


@router.put("/me", response_model=BotSettingsResponse)
def update_my_bot_settings(
    body: BotSettingsUpdateRequest, user: User = Depends(get_current_user), session: Session = Depends(get_db)
) -> BotSettingsResponse:
    settings_row = persistence.get_or_create_bot_settings(session, user.id)
    settings_row = persistence.update_bot_settings(session, settings_row, body)
    return _to_response(settings_row)


@router.post("/me/rotate-key", response_model=ApiKeyResponse)
def rotate_my_api_key(user: User = Depends(get_current_user), session: Session = Depends(get_db)) -> ApiKeyResponse:
    settings_row = persistence.get_or_create_bot_settings(session, user.id)
    new_key = persistence.rotate_api_key(session, settings_row)
    return ApiKeyResponse(api_key=new_key)
