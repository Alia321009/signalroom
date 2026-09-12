from executor.state import CallState, ExecutorState, load_state, save_state


def test_load_state_returns_empty_state_when_file_missing(tmp_path):
    state = load_state(tmp_path / "does-not-exist.json")
    assert state.cursor is None
    assert state.calls == {}


def test_save_then_load_round_trips(tmp_path):
    path = tmp_path / "state.json"
    original = ExecutorState(cursor="2026-01-01T00:00:00Z", calls={1: CallState(status="active", tickets=["111", "112"])})

    save_state(path, original)
    loaded = load_state(path)

    assert loaded.cursor == "2026-01-01T00:00:00Z"
    assert loaded.calls[1].status == "active"
    assert loaded.calls[1].tickets == ["111", "112"]


def test_load_state_recovers_from_corrupt_file(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{not valid json", encoding="utf-8")

    state = load_state(path)

    assert state.cursor is None
    assert state.calls == {}


def test_save_creates_parent_directories(tmp_path):
    path = tmp_path / "nested" / "dir" / "state.json"
    save_state(path, ExecutorState())
    assert path.exists()


def test_save_is_atomic_no_leftover_tmp_file(tmp_path):
    path = tmp_path / "state.json"
    save_state(path, ExecutorState(cursor="x"))
    assert not path.with_suffix(".json.tmp").exists()


def test_call_state_defaults_to_empty_ticket_list():
    cs = CallState(status="pending")
    assert cs.tickets == []
