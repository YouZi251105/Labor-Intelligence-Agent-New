from fastapi.testclient import TestClient

from app.core.rate_limit import FixedWindowRateLimiter
from app.main import app


def test_responses_include_request_id() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers["x-request-id"]


def test_metrics_endpoint_returns_prometheus_text() -> None:
    with TestClient(app) as client:
        client.get("/api/v1/health")
        response = client.get("/metrics")

    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds_count" in response.text


def test_fixed_window_limiter_blocks_and_resets() -> None:
    now = [100.0]
    limiter = FixedWindowRateLimiter(limit=2, window_seconds=60, clock=lambda: now[0])

    assert limiter.allow("127.0.0.1:/auth/login")
    assert limiter.allow("127.0.0.1:/auth/login")
    assert not limiter.allow("127.0.0.1:/auth/login")

    now[0] += 61
    assert limiter.allow("127.0.0.1:/auth/login")
