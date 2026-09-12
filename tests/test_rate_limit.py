import app.rate_limit as rate_limit


def test_allows_up_to_the_max_attempts():
    for _ in range(rate_limit.MAX_ATTEMPTS):
        assert rate_limit.check_and_record("1.2.3.4") is True


def test_blocks_after_max_attempts():
    for _ in range(rate_limit.MAX_ATTEMPTS):
        rate_limit.check_and_record("1.2.3.4")
    assert rate_limit.check_and_record("1.2.3.4") is False


def test_different_ips_are_tracked_independently():
    for _ in range(rate_limit.MAX_ATTEMPTS):
        rate_limit.check_and_record("1.1.1.1")
    assert rate_limit.check_and_record("2.2.2.2") is True


def test_reset_all_clears_every_ip():
    for _ in range(rate_limit.MAX_ATTEMPTS):
        rate_limit.check_and_record("1.2.3.4")
    rate_limit.reset_all()
    assert rate_limit.check_and_record("1.2.3.4") is True


def test_old_attempts_outside_the_window_do_not_count(monkeypatch):
    import time

    t = [1000.0]
    monkeypatch.setattr(time, "monotonic", lambda: t[0])

    for _ in range(rate_limit.MAX_ATTEMPTS):
        rate_limit.check_and_record("1.2.3.4")
    assert rate_limit.check_and_record("1.2.3.4") is False

    t[0] += rate_limit.WINDOW_SECONDS + 1
    assert rate_limit.check_and_record("1.2.3.4") is True
