"""
SQLAlchemy models. Domain is deliberately different from the trading-bot
project's schema: that one is a single account being traded by one engine;
this one is many paying members subscribing to one trader's discretionary
calls, each optionally auto-executing them on their OWN MT5 account via
the local executor (executor/).
"""
from __future__ import annotations

import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    # "admin" = the trader posting calls and managing members (exactly one
    # in practice, bootstrapped like the trading-bot project's own admin).
    # "member" = a paying/referred subscriber.
    role: Mapped[str] = mapped_column(String(20), default="member")
    totp_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    subscription: Mapped["Subscription | None"] = relationship(back_populates="user", uselist=False)
    bot_settings: Mapped["BotSettings | None"] = relationship(back_populates="user", uselist=False)


class Subscription(Base):
    """One row per member -- their current access state. History of how it
    got there lives in SubscriptionEvent, same audit-trail split as the
    trading-bot project's EngineEvent."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    # "none" (signed up, not yet approved) | "broker_referral" (free tier,
    # funded by the broker's IB commission) | "paid" (flat monthly fee) |
    # "trial"
    tier: Mapped[str] = mapped_column(String(20), default="none")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | active | expired | revoked
    broker: Mapped[str | None] = mapped_column(String(20), nullable=True)  # "exness" | "xm" | None
    paid_until: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_trade_activity_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user: Mapped[User] = relationship(back_populates="subscription")


class SubscriptionEvent(Base):
    __tablename__ = "subscription_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(String(500))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Call(Base):
    """One discretionary trade call, posted by the admin -- the core
    product (spec: "Entry, Stop loss, Take profit 1-3, Validity window,
    Status & outcome", verbatim from growthclubpk.com's own feature list)."""

    __tablename__ = "calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    symbol: Mapped[str] = mapped_column(String(20))
    direction: Mapped[str] = mapped_column(String(4))  # "buy" | "sell"
    entry: Mapped[float] = mapped_column(Float)
    sl: Mapped[float] = mapped_column(Float)
    tp1: Mapped[float] = mapped_column(Float)
    tp2: Mapped[float | None] = mapped_column(Float, nullable=True)
    tp3: Mapped[float | None] = mapped_column(Float, nullable=True)
    valid_until: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    # pending (posted, entry not yet reached) | active (filled) |
    # tp1_hit | tp2_hit | tp3_hit | sl_hit | expired | cancelled
    status: Mapped[str] = mapped_column(String(20), default="pending")
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    closed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # R-multiple result once closed -- what "the full public track record"
    # (the site's own CTA) is actually built from.
    outcome_r: Mapped[float | None] = mapped_column(Float, nullable=True)


class CallExecution(Base):
    """One member's own fill/skip record against one Call -- populated by
    the local executor's report-back call, or left null if they traded it
    manually / not at all."""

    __tablename__ = "call_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    call_id: Mapped[int] = mapped_column(ForeignKey("calls.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    ticket: Mapped[str | None] = mapped_column(String(40), nullable=True)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    executed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | filled | skipped | failed
    profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    close_reason: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class BotSettings(Base):
    """A member's own auto-execution config for the local executor
    (executor/run.py) -- never a broker password. The executor runs on
    the member's own machine against their own already-logged-in MT5
    terminal; the server only needs to know what to tell it to do and how
    to authenticate its polling requests."""

    __tablename__ = "bot_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_pct: Mapped[float] = mapped_column(Float, default=1.0)
    max_daily_loss_pct: Mapped[float] = mapped_column(Float, default=3.0)
    symbols: Mapped[list[str]] = mapped_column(JSON, default=list)  # empty list = all symbols
    magic: Mapped[int] = mapped_column(Integer, unique=True)
    # A long-lived bearer token distinct from the web JWT -- the executor
    # runs unattended on the member's machine and can't do an interactive
    # login/2FA/refresh dance. Lesson learned directly from the trading-bot
    # project's Phase 8 (an unattended monitor can't hold a fresh human
    # TOTP code either) -- same fix, a dedicated machine credential scoped
    # to exactly what it needs.
    api_key: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user: Mapped[User] = relationship(back_populates="bot_settings")
