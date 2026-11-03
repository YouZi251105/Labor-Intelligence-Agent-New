"""字典接口的单元测试。"""
from fastapi.testclient import TestClient

from app.main import app


def test_dictionary_returns_disputes_stages_categories() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/meta/dictionary")

    assert response.status_code == 200
    data = response.json()

    disputes = {item["value"]: item["label"] for item in data["disputes"]}
    assert disputes["labor_pay"] == "劳动报酬、加班费、工伤医疗费、经济补偿、赔偿金争议"
    assert disputes["service_pay"] == "劳务费拖欠纠纷"
    assert len(disputes) == 10

    groups = {item["value"]: item.get("group") for item in data["disputes"]}
    labor_values = {value for value, group in groups.items() if group == "labor"}
    service_values = {value for value, group in groups.items() if group == "service"}
    assert len(labor_values) == 6
    assert len(service_values) == 4

    stages = {item["value"] for item in data["stages"]}
    assert "closed" in stages

    categories = {item["value"] for item in data["evidence_categories"]}
    assert "social_insurance" in categories
    assert "other" in categories
