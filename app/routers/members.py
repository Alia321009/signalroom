"""Member self-service (profile, broker referral choice) and admin member
management (list, manual subscription updates -- see schemas.py's
SubscriptionUpdateRequest docstring for why this is manual, not
gateway-driven, for now)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import persistence
from app.config import Settings
from app.deps import get_db, get_settings_dep, require_admin, get_current_user
from app.models import User
from app.schemas import MemberResponse, SubscriptionResponse, SubscriptionUpdateRequest

router = APIRouter(tags=["members"])


def _to_member_response(user: User, session: Session) -> MemberResponse:
    sub = persistence.get_or_create_subscription(session, user.id)
    return MemberResponse(
        id=user.id, email=user.email, role=user.role, is_active=user.is_active, created_at=user.created_at,
        subscription=SubscriptionResponse(
            tier=sub.tier, status=sub.status, broker=sub.broker,
            paid_until=sub.paid_until, last_trade_activity_at=sub.last_trade_activity_at,
        ),
    )


@router.get("/members/me", response_model=MemberResponse)
def get_me(user: User = Depends(get_current_user), session: Session = Depends(get_db)) -> MemberResponse:
    return _to_member_response(user, session)


@router.post("/members/me/broker", response_model=SubscriptionResponse)
def set_broker(
    broker: str, user: User = Depends(get_current_user), session: Session = Depends(get_db)
) -> SubscriptionResponse:
    if broker not in ("exness", "xm"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "broker must be 'exness' or 'xm'")
    sub = persistence.get_or_create_subscription(session, user.id)
    sub.broker = broker
    if sub.tier == "none":
        sub.tier = "broker_referral"
    persistence.record_subscription_event(session, user.id, "broker_selected", f"{user.email} selected {broker}")
    session.flush()
    return SubscriptionResponse(
        tier=sub.tier, status=sub.status, broker=sub.broker,
        paid_until=sub.paid_until, last_trade_activity_at=sub.last_trade_activity_at,
    )


@router.get("/members", response_model=list[MemberResponse])
def list_members(admin: User = Depends(require_admin), session: Session = Depends(get_db)) -> list[MemberResponse]:
    members = session.query(User).filter_by(role="member").order_by(User.created_at.desc()).all()
    return [_to_member_response(m, session) for m in members]


@router.patch("/members/{member_id}/subscription", response_model=MemberResponse)
def update_subscription(
    member_id: int,
    body: SubscriptionUpdateRequest,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_db),
) -> MemberResponse:
    member = session.get(User, member_id)
    if member is None or member.role != "member":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such member")

    sub = persistence.get_or_create_subscription(session, member.id)
    old = {"tier": sub.tier, "status": sub.status, "broker": sub.broker, "paid_until": sub.paid_until}
    if body.tier is not None:
        sub.tier = body.tier
    if body.status is not None:
        sub.status = body.status
    if body.broker is not None:
        sub.broker = body.broker
    if body.paid_until is not None:
        sub.paid_until = body.paid_until
    session.flush()

    new = {"tier": sub.tier, "status": sub.status, "broker": sub.broker, "paid_until": sub.paid_until}
    persistence.record_subscription_event(
        session, member.id, "subscription_changed", f"{admin.email} updated {member.email}'s subscription",
        payload={"admin": admin.email, "old": {k: str(v) for k, v in old.items()}, "new": {k: str(v) for k, v in new.items()}},
    )

    return _to_member_response(member, session)
