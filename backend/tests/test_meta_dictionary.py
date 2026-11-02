"""字典接口的单元测试。"""
from fastapi.testclient import TestClient

from app.main import app


def test_dictionary_returns_disputes_stages_categories() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/meta/dictionary")

    assert response.status_code == 200
    data = response.json()

    disputes = {item["value"]: item["label"] for item in data["disputes"]}
    assert disputes["wage"] == "欠薪"
    assert disputes["insurance"] == "社会保险"

    stages = {item["value"] for item in data["stages"]}
    assert "closed" in stages

    categories = {item["value"] for item in data["evidence_categories"]}
    assert "social_insurance" in categories
    assert "other" in categories
