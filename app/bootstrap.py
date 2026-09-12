"""First-run admin (the trader/founder) account creation. No public
signup for this role -- created from ADMIN_EMAIL/ADMIN_PASSWORD (.env) on
first startup, same pattern as the trading-bot project's api/bootstrap.py."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app import auth as auth_module
from app.config import Settings
from app.models import User
from app.logging_config import get_logger

log = get_logger(__name__)


def ensure_admin_user(session: Session, settings: Settings) -> None:
    if session.query(User).filter_by(role="admin").count() > 0:
        return

    if not settings.admin_email or not settings.admin_password:
        log.warning(
            "no_admin_user_and_no_bootstrap_credentials_configured",
            hint="set ADMIN_EMAIL and ADMIN_PASSWORD in .env to auto-create one on next startup",
        )
        return

    totp_secret = auth_module.generate_totp_secret()
    user = User(
        email=settings.admin_email,
        password_hash=auth_module.hash_password(settings.admin_password),
        totp_secret=totp_secret,
        role="admin",
    )
    session.add(user)
    session.commit()

    uri = auth_module.totp_provisioning_uri(totp_secret, settings.admin_email)
    log.warning(
        "admin_user_created_scan_this_totp_uri_now",
        email=settings.admin_email,
        totp_uri=uri,
        note="this URI is logged only this once — add it to an authenticator app now",
    )
