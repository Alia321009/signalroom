"""Config for the LOCAL executor -- runs on a member's own machine, next
to their own already-logged-in MT5 terminal. Nothing here is a broker
credential; MT5Adapter attaches to whatever terminal is already open via
the MetaTrader5 package's IPC connection, the same mechanism the
trading-bot project's engine/adapters/mt5_adapter.py uses."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class ExecutorSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    api_base_url: str = "http://localhost:8000"
    api_key: str = ""
    poll_interval_seconds: float = 5.0
    # Where this executor remembers which calls it has already acted on
    # and which MT5 tickets belong to them -- survives a restart so it
    # never double-opens a position for a call it already executed.
    state_file: str = "./executor_state.json"


def get_executor_settings() -> ExecutorSettings:
    return ExecutorSettings()
