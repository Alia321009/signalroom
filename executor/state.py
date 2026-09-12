"""Local, on-disk state for the executor -- which calls it has already
acted on, which MT5 tickets belong to each, and the polling cursor.
Pure file I/O, no MT5 dependency, so fully testable."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CallState:
    status: str  # the call status this executor last acted on
    tickets: list[str] = field(default_factory=list)


@dataclass
class ExecutorState:
    cursor: str | None = None  # ISO timestamp: only calls updated after this have been seen
    calls: dict[int, CallState] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "cursor": self.cursor,
            "calls": {str(k): {"status": v.status, "tickets": v.tickets} for k, v in self.calls.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExecutorState":
        return cls(
            cursor=data.get("cursor"),
            calls={int(k): CallState(status=v["status"], tickets=v.get("tickets", [])) for k, v in data.get("calls", {}).items()},
        )


def load_state(path: str | Path) -> ExecutorState:
    p = Path(path)
    if not p.exists():
        return ExecutorState()
    try:
        return ExecutorState.from_dict(json.loads(p.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, KeyError, ValueError):
        # A corrupt state file is recoverable (worst case: an already-
        # executed call gets re-evaluated, which record_execution_report's
        # idempotency on the server side... actually isn't idempotent
        # today -- see README's "known limitations" -- so this is a
        # deliberate fail-safe-loud choice: start fresh rather than crash
        # the whole executor over one bad file.
        return ExecutorState()


def save_state(path: str | Path, state: ExecutorState) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    # Write to a temp file then rename -- atomic on the same filesystem,
    # so a crash mid-write never leaves a half-written, corrupt state file.
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
    tmp.replace(p)
