import datetime

from app.models import Subscription
from app.persistence import check_inactivity_revocation


def _sub(last_trade_activity_at=None) -> Subscription:
    return Subscription(user_id=1, tier="paid", status="active", last_trade_activity_at=last_trade_activity_at)


def test_no_activity_ever_is_not_flagged():
    # a member who never traded isn't "inactive" in the revocation sense --
    # that's a different (onboarding) state, not a lapsed one
    assert check_inactivity_revocation(_sub(None), inactivity_days=14) is False


def test_recent_activity_is_not_flagged():
    recent = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)
    assert check_inactivity_revocation(_sub(recent), inactivity_days=14) is False


def test_activity_exactly_at_the_threshold_is_flagged():
    at_threshold = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=14, minutes=1)
    assert check_inactivity_revocation(_sub(at_threshold), inactivity_days=14) is True


def test_activity_older_than_the_threshold_is_flagged():
    old = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)
    assert check_inactivity_revocation(_sub(old), inactivity_days=14) is True


def test_respects_a_custom_threshold():
    six_days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=6)
    assert check_inactivity_revocation(_sub(six_days_ago), inactivity_days=7) is False
    assert check_inactivity_revocation(_sub(six_days_ago), inactivity_days=5) is True
