import pyotp

from app import auth as auth_module
from app import bootstrap
from app.config import Settings
from app.models import User


def test_ensure_admin_user_creates_one_when_none_exists(session_factory):
    settings = Settings(_env_file=None, admin_email="admin@test.com", admin_password="strong-password-123")
    with session_factory() as session:
        bootstrap.ensure_admin_user(session, settings)
        session.commit()

    with session_factory() as session:
        user = session.query(User).filter_by(email="admin@test.com").first()
        assert user is not None
        assert user.role == "admin"
        assert user.totp_secret is not None
        assert auth_module.verify_password("strong-password-123", user.password_hash)


def test_ensure_admin_user_is_idempotent(session_factory):
    settings = Settings(_env_file=None, admin_email="admin@test.com", admin_password="strong-password-123")
    with session_factory() as session:
        bootstrap.ensure_admin_user(session, settings)
        session.commit()
    with session_factory() as session:
        bootstrap.ensure_admin_user(session, settings)
        session.commit()

    with session_factory() as session:
        assert session.query(User).filter_by(role="admin").count() == 1


def test_ensure_admin_user_noop_when_an_admin_already_exists(session_factory):
    with session_factory() as session:
        session.add(User(email="existing@test.com", password_hash="x", totp_secret="Y", role="admin"))
        session.commit()

    settings = Settings(_env_file=None, admin_email="new-admin@test.com", admin_password="strong-password-123")
    with session_factory() as session:
        bootstrap.ensure_admin_user(session, settings)
        session.commit()

    with session_factory() as session:
        assert session.query(User).filter_by(role="admin").count() == 1
        assert session.query(User).filter_by(role="admin").first().email == "existing@test.com"


def test_ensure_admin_user_does_not_block_member_signups(session_factory):
    """A member registering (role=member) must not satisfy the "an admin
    exists" check -- confirms the query is scoped to role=admin, not any
    user at all."""
    with session_factory() as session:
        session.add(User(email="member@test.com", password_hash="x", role="member"))
        session.commit()

    settings = Settings(_env_file=None, admin_email="admin@test.com", admin_password="strong-password-123")
    with session_factory() as session:
        bootstrap.ensure_admin_user(session, settings)
        session.commit()

    with session_factory() as session:
        assert session.query(User).filter_by(role="admin").count() == 1


def test_ensure_admin_user_noop_when_no_credentials_configured(session_factory):
    settings = Settings(_env_file=None)
    with session_factory() as session:
        bootstrap.ensure_admin_user(session, settings)
        session.commit()

    with session_factory() as session:
        assert session.query(User).count() == 0


def test_bootstrapped_admin_totp_secret_actually_works(session_factory):
    settings = Settings(_env_file=None, admin_email="admin@test.com", admin_password="strong-password-123")
    with session_factory() as session:
        bootstrap.ensure_admin_user(session, settings)
        session.commit()

    with session_factory() as session:
        user = session.query(User).filter_by(email="admin@test.com").first()
        code = pyotp.TOTP(user.totp_secret).now()
        assert auth_module.verify_totp(user.totp_secret, code)
