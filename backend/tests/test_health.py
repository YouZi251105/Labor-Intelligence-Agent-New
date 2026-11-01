from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "labor-intelligence-agent"
    assert payload["version"] == "0.2.0"
    assert payload["environment"] in {"development", "test", "production"}


def test_root_endpoint_points_to_docs() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json()["docs"] == "/docs"


def test_docs_use_local_swagger_assets() -> None:
    with TestClient(app) as client:
        response = client.get("/docs")
        script = client.get("/static/swagger-ui/swagger-ui-bundle.js")

    assert response.status_code == 200
    assert "/static/swagger-ui/swagger-ui-bundle.js" in response.text
    assert "cdn.jsdelivr.net" not in response.text
    assert script.status_code == 200
