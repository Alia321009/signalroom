"""FastAPI app assembly. create_app() is a pure factory -- constructing it
never touches a real database; that only happens when the app actually
starts (lifespan). Same discipline as the trading-bot project's api/main.py,
so tests can build one against an in-memory SQLite session factory."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import bootstrap
from app.config import Settings, get_settings
from app.routers import auth, bot, calls, executor, members
from app.ws import router as ws_router

WEB_DIST_DIR = Path(__file__).resolve().parent.parent / "web" / "dist"


def create_app(session_factory: sessionmaker, settings: Settings | None = None) -> FastAPI:
    effective_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        with session_factory() as session:
            bootstrap.ensure_admin_user(session, effective_settings)
        yield

    app = FastAPI(title="SignalRoom API", lifespan=lifespan)
    app.state.session_factory = session_factory

    app.include_router(auth.router)
    app.include_router(members.router)
    app.include_router(calls.router)
    app.include_router(bot.router)
    app.include_router(executor.router)
    app.include_router(ws_router)

    if WEB_DIST_DIR.is_dir():
        app.mount("/", StaticFiles(directory=WEB_DIST_DIR, html=True), name="dashboard")

    return app


def _build_real_app() -> FastAPI:
    settings = get_settings()
    db_engine = create_engine(settings.database_url)
    session_factory = sessionmaker(bind=db_engine)
    return create_app(session_factory, settings=settings)


app = _build_real_app()
