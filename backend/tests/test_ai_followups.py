"""AI 追问选项和模型结构化输出的测试。"""

from fastapi.testclient import TestClient

from app.main import app
from app.services.ai import parse_qwen_follow_ups


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_consultation_returns_persisted_follow_up_options() -> None:
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "demo", "password": "Demo123!"},
        )
        token = login.json()["access_token"]
        created = client.post(
            "/api/v1/cases",
            headers=auth(token),
            json={
                "title": "AI 追问选项测试",
                "dispute_type": "labor_pay",
                "location": "上海市",
                "facts": "公司拖欠两个月工资，还没有说明具体金额。",
            },
        )
        case_id = created.json()["id"]

        response = client.post(
            f"/api/v1/cases/{case_id}/consultations",
            headers=auth(token),
            json={"message": "老板拖欠工资两个月，我应该先补充什么？"},
        )

    assert response.status_code == 200
    payload = response.json()
    options = payload["structured"]["follow_up_options"]
    assert 2 <= len(options) <= 4
    assert {item["kind"] for item in options} == {"send", "fill"}
    assert all(item["id"] and item["label"] and item["message"] for item in options)
    assert len({item["label"] for item in options}) == len(options)
    persisted = payload["assistant_message"]["metadata_json"]["structured"]
    assert persisted["follow_up_options"] == options


def test_qwen_follow_up_delimiter_is_removed_and_validated() -> None:
    content = (
        "建议先整理工资流水和聊天记录。\n\n"
        '<FOLLOW_UPS>["接下来可以先协商吗？", "仲裁需要哪些材料？", '
        '"怎么证明劳动关系？", "可以申请律师复核吗？", "第五条应被截断"]</FOLLOW_UPS>'
    )

    clean, options = parse_qwen_follow_ups(content)

    assert "<FOLLOW_UPS>" not in clean
    assert clean == "建议先整理工资流水和聊天记录。"
    assert options == [
        "接下来可以先协商吗？",
        "仲裁需要哪些材料？",
        "怎么证明劳动关系？",
        "可以申请律师复核吗？",
    ]


def test_high_risk_case_recommends_filing_review_action() -> None:
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "demo", "password": "Demo123!"},
        )
        token = login.json()["access_token"]
        created = client.post(
            "/api/v1/cases",
            headers=auth(token),
            json={
                "title": "工伤仲裁前复核",
                "dispute_type": "labor_pay",
                "location": "上海市",
                "facts": "工伤后公司不承认，我准备马上申请仲裁。",
            },
        )
        response = client.post(
            f"/api/v1/cases/{created.json()['id']}/consultations",
            headers=auth(token),
            json={"message": "工伤还没处理，我准备直接申请仲裁，需要准备什么？"},
        )

    assert response.status_code == 200
    structured = response.json()["structured"]
    recommendation = structured["intervention_recommendation"]
    assert recommendation["recommended"] is True
    assert recommendation["level"] == "urgent"
    assert recommendation["action"] == "filing_review"
    assert recommendation["reasons"]
    assert "filing_review" in {
        item["kind"] for item in structured["follow_up_options"]
    }
