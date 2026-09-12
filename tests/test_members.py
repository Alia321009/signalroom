def test_get_me_returns_profile_and_subscription(client, member_headers, member_user):
    r = client.get("/members/me", headers=member_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == member_user["email"]
    assert body["role"] == "member"
    assert body["subscription"]["tier"] == "none"
    assert body["subscription"]["status"] == "pending"


def test_set_broker_updates_subscription_tier_and_broker(client, member_headers):
    r = client.post("/members/me/broker", params={"broker": "exness"}, headers=member_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["broker"] == "exness"
    assert body["tier"] == "broker_referral"


def test_set_broker_rejects_unknown_broker(client, member_headers):
    r = client.post("/members/me/broker", params={"broker": "not-a-broker"}, headers=member_headers)
    assert r.status_code == 422


def test_set_broker_does_not_downgrade_an_already_paid_tier(client, member_headers, admin_headers, member_user, session_factory):
    from app.models import User

    with session_factory() as session:
        member = session.query(User).filter_by(email=member_user["email"]).first()
        member_id = member.id

    client.patch(f"/members/{member_id}/subscription", json={"tier": "paid"}, headers=admin_headers)
    r = client.post("/members/me/broker", params={"broker": "xm"}, headers=member_headers)
    assert r.json()["tier"] == "paid"  # broker choice recorded, but doesn't clobber an existing paid tier


def test_member_cannot_list_members(client, member_headers):
    r = client.get("/members", headers=member_headers)
    assert r.status_code == 403


def test_admin_can_list_members(client, admin_headers, member_user):
    r = client.get("/members", headers=admin_headers)
    assert r.status_code == 200
    emails = [m["email"] for m in r.json()]
    assert member_user["email"] in emails


def test_member_cannot_update_a_subscription(client, member_headers, member_user, session_factory):
    from app.models import User

    with session_factory() as session:
        member_id = session.query(User).filter_by(email=member_user["email"]).first().id

    r = client.patch(f"/members/{member_id}/subscription", json={"tier": "paid"}, headers=member_headers)
    assert r.status_code == 403


def test_admin_can_activate_a_members_subscription(client, admin_headers, member_user, session_factory):
    from app.models import User

    with session_factory() as session:
        member_id = session.query(User).filter_by(email=member_user["email"]).first().id

    r = client.patch(
        f"/members/{member_id}/subscription",
        json={"tier": "paid", "status": "active"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["subscription"]["tier"] == "paid"
    assert r.json()["subscription"]["status"] == "active"


def test_update_subscription_404_for_unknown_member(client, admin_headers):
    r = client.patch("/members/99999/subscription", json={"tier": "paid"}, headers=admin_headers)
    assert r.status_code == 404


def test_admin_can_set_broker_and_paid_until(client, admin_headers, member_user, session_factory):
    import datetime

    from app.models import User

    with session_factory() as session:
        member_id = session.query(User).filter_by(email=member_user["email"]).first().id

    paid_until = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)).isoformat()
    r = client.patch(
        f"/members/{member_id}/subscription",
        json={"broker": "xm", "paid_until": paid_until},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["subscription"]["broker"] == "xm"
    assert r.json()["subscription"]["paid_until"] is not None


def test_update_subscription_404_for_the_admin_itself(client, admin_headers, session_factory):
    from app.models import User

    with session_factory() as session:
        admin_id = session.query(User).filter_by(role="admin").first().id

    r = client.patch(f"/members/{admin_id}/subscription", json={"tier": "paid"}, headers=admin_headers)
    assert r.status_code == 404  # not a "member" row -- refuse rather than silently mutate the admin
