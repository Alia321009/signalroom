"""The core product: admin posts discretionary trade calls, members read
them. GET /calls/public is deliberately unauthenticated -- it's the site's
own "See the full public track record" CTA, and only ever returns CLOSED
calls (persistence.list_public_closed_calls), never anything still open
(no reason to leak an active, unfilled entry to a non-member)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import persistence
from app.deps import get_current_user, get_db, require_admin
from app.models import Call, User
from app.schemas import CallCreateRequest, CallResponse, CallUpdateRequest, PublicCallResponse

router = APIRouter(tags=["calls"])


def _to_response(call: Call) -> CallResponse:
    return CallResponse(
        id=call.id, created_by=call.created_by, symbol=call.symbol, direction=call.direction,
        entry=call.entry, sl=call.sl, tp1=call.tp1, tp2=call.tp2, tp3=call.tp3,
        valid_until=call.valid_until, status=call.status, notes=call.notes,
        created_at=call.created_at, updated_at=call.updated_at, closed_at=call.closed_at, outcome_r=call.outcome_r,
    )


@router.get("/calls/public", response_model=list[PublicCallResponse])
def public_track_record(session: Session = Depends(get_db)) -> list[PublicCallResponse]:
    calls = persistence.list_public_closed_calls(session)
    return [
        PublicCallResponse(id=c.id, symbol=c.symbol, direction=c.direction, status=c.status,
                            outcome_r=c.outcome_r, closed_at=c.closed_at)
        for c in calls
    ]


@router.get("/calls", response_model=list[CallResponse])
def list_calls(
    limit: int = 100, user: User = Depends(get_current_user), session: Session = Depends(get_db)
) -> list[CallResponse]:
    return [_to_response(c) for c in persistence.list_calls(session, limit=limit)]


@router.get("/calls/{call_id}", response_model=CallResponse)
def get_call(call_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_db)) -> CallResponse:
    call = session.get(Call, call_id)
    if call is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such call")
    return _to_response(call)


@router.post("/calls", response_model=CallResponse, status_code=status.HTTP_201_CREATED)
def create_call(
    body: CallCreateRequest, admin: User = Depends(require_admin), session: Session = Depends(get_db)
) -> CallResponse:
    call = persistence.create_call(session, admin.id, body)
    return _to_response(call)


@router.patch("/calls/{call_id}", response_model=CallResponse)
def update_call(
    call_id: int, body: CallUpdateRequest, admin: User = Depends(require_admin), session: Session = Depends(get_db)
) -> CallResponse:
    call = session.get(Call, call_id)
    if call is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such call")
    call = persistence.update_call(session, call, body)
    return _to_response(call)
