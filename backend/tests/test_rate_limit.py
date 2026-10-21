from app.rate_limit import RateLimiter


def test_limiter_blocks_then_recovers(monkeypatch):
    limiter = RateLimiter(max_calls=2, period_seconds=10)
    clock = [1000.0]
    monkeypatch.setattr("app.rate_limit.time.time", lambda: clock[0])
    assert limiter.allow("a") and limiter.allow("a")
    assert not limiter.allow("a")
    clock[0] += 11
    assert limiter.allow("a")


def test_limiter_purges_idle_keys(monkeypatch):
    limiter = RateLimiter(max_calls=5, period_seconds=10)
    clock = [1000.0]
    monkeypatch.setattr("app.rate_limit.time.time", lambda: clock[0])
    for i in range(100):
        limiter.allow(f"ip-{i}")
    clock[0] += 60
    for _ in range(RateLimiter._GC_EVERY):
        limiter.allow("actif")
    assert set(limiter._hits) == {"actif"}
