"""Request/response pydantic models for the HTTP-facing API surface."""
from __future__ import annotations

import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# --- auth ---


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TempTokenResponse(BaseModel):
    temp_token: str


class Verify2FARequest(BaseModel):
    temp_token: str
    totp_code: str


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- members / subscription ---


class SubscriptionResponse(BaseModel):
    tier: str
    status: str
    broker: str | None
    paid_until: datetime.datetime | None
    last_trade_activity_at: datetime.datetime | None


class MemberResponse(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    created_at: datetime.datetime
    subscription: SubscriptionResponse | None


class SubscriptionUpdateRequest(BaseModel):
    """Admin-only, manual for now -- no payment gateway wired in yet (see
    README's "Payments" section for why and what plugs in later)."""

    tier: Literal["none", "broker_referral", "paid", "trial"] | None = None
    status: Literal["pending", "active", "expired", "revoked"] | None = None
    broker: Literal["exness", "xm"] | None = None
    paid_until: datetime.datetime | None = None


# --- calls ---


class CallCreateRequest(BaseModel):
    symbol: str
    direction: Literal["buy", "sell"]
    entry: float
    sl: float
    tp1: float
    tp2: float | None = None
    tp3: float | None = None
    valid_until: datetime.datetime
    notes: str | None = None


class CallUpdateRequest(BaseModel):
    status: Literal["pending", "active", "tp1_hit", "tp2_hit", "tp3_hit", "sl_hit", "expired", "cancelled"] | None = None
    outcome_r: float | None = None
    notes: str | None = None


class CallResponse(BaseModel):
    id: int
    created_by: int
    symbol: str
    direction: str
    entry: float
    sl: float
    tp1: float
    tp2: float | None
    tp3: float | None
    valid_until: datetime.datetime
    status: str
    notes: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    closed_at: datetime.datetime | None
    outcome_r: float | None


class PublicCallResponse(BaseModel):
    """No member PII -- the "public track record" the site's own CTA
    promises. Closed calls only (see api routers/calls.py)."""

    id: int
    symbol: str
    direction: str
    status: str
    outcome_r: float | None
    closed_at: datetime.datetime | None


# --- bot settings (local executor) ---


class BotSettingsResponse(BaseModel):
    enabled: bool
    risk_pct: float
    max_daily_loss_pct: float
    symbols: list[str]
    magic: int


class BotSettingsUpdateRequest(BaseModel):
    enabled: bool | None = None
    risk_pct: float | None = Field(default=None, gt=0, le=5)
    max_daily_loss_pct: float | None = Field(default=None, gt=0, le=20)
    symbols: list[str] | None = None


class ApiKeyResponse(BaseModel):
    api_key: str


# --- executor-facing ---


class ExecutorCallResponse(BaseModel):
    id: int
    symbol: str
    direction: str
    entry: float
    sl: float
    tp1: float
    tp2: float | None
    tp3: float | None
    valid_until: datetime.datetime
    status: str
    updated_at: datetime.datetime


class ExecutionReportRequest(BaseModel):
    call_id: int
    ticket: str | None = None
    volume: float | None = None
    status: Literal["filled", "skipped", "failed"]
    profit: float | None = None
    close_reason: str | None = None


class WsMessage(BaseModel):
    type: Literal["call_new", "call_updated"]
    call: CallResponse
