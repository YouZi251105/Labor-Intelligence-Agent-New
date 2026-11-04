"""AI 追问选项和模型结构化输出的测试。"""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.services.ai import (
    FollowUpProgress,
    InterventionRecommendation,
    _build_qwen_prompt,
    build_follow_up_options,
    parse_qwen_follow_ups,
)


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


def test_qwen_prompt_reflects_platform_lawyer_service() -> None:
    prompt = _build_qwen_prompt(
        SimpleNamespace(facts="公司拖欠工资。"),
        "可以帮我找律师吗？",
        [],
        request_follow_ups=True,
    )

    assert "平台设有律师端" in prompt
    assert "不得回答平台不提供律师服务" in prompt


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


def test_completed_review_action_is_not_recommended_again() -> None:
    recommendation = InterventionRecommendation(
        recommended=True,
        level="urgent",
        reasons=["涉及仲裁和材料完整性"],
        action="filing_review",
    )

    options = build_follow_up_options(
        "工伤后公司不承认，准备申请仲裁。",
        ["赔偿金额"],
        "核对仲裁材料",
        recommendation,
        history=[],
        progress=FollowUpProgress(
            stage="procedure",
            has_evidence=True,
            case_review_status="pending",
        ),
    )

    assert "filing_review" not in {item.kind for item in options}
    assert any("复核" in item.label or "复核" in item.message for item in options)


def test_lawyer_request_does_not_hide_filing_review_action() -> None:
    recommendation = InterventionRecommendation(
        recommended=True,
        level="urgent",
        reasons=["涉及仲裁和材料完整性"],
        action="filing_review",
    )

    options = build_follow_up_options(
        "工伤后公司不承认，准备申请仲裁。",
        ["赔偿金额"],
        "核对仲裁材料",
        recommendation,
        history=[],
        progress=FollowUpProgress(
            stage="procedure",
            has_evidence=True,
            lawyer_request_status="pending",
        ),
    )

    assert "filing_review" in {item.kind for item in options}
    assert "lawyer_request" not in {item.kind for item in options}


def test_follow_up_questions_follow_case_progress() -> None:
    recommendation = InterventionRecommendation(
        recommended=False,
        level="none",
        reasons=[],
        action="lawyer_request",
    )
    evidence_options = build_follow_up_options(
        "公司拖欠工资。",
        ["金额"],
        "整理工资流水",
        recommendation,
        history=[],
        progress=FollowUpProgress(stage="evidence", has_evidence=False),
    )
    document_options = build_follow_up_options(
        "工资流水已经上传，金额是8000元。",
        ["金额"],
        "核对文书",
        recommendation,
        history=[
            SimpleNamespace(
                role="user",
                content="请帮我检查现有材料还缺什么。",
            )
        ],
        progress=FollowUpProgress(
            stage="document",
            has_evidence=True,
            has_documents=True,
        ),
    )

    assert any("上传" in item.label or "材料" in item.label for item in evidence_options)
    assert any("文书" in item.label or "文书" in item.message for item in document_options)
    assert all(
        item.message != "请帮我检查现有材料还缺什么。"
        for item in document_options
    )


def test_consultation_hides_filing_review_after_request_exists() -> None:
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
                "title": "复核动作去重",
                "dispute_type": "labor_pay",
                "location": "上海市",
                "facts": "工伤后公司不承认，我准备马上申请仲裁。",
            },
        )
        case_id = created.json()["id"]
        review = client.post(
            f"/api/v1/lawyer-service/cases/{case_id}/review",
            headers=auth(token),
        )

        response = client.post(
            f"/api/v1/cases/{case_id}/consultations",
            headers=auth(token),
            json={"message": "我已经申请复核了，接下来还要准备什么？"},
        )

    assert review.status_code == 201
    assert response.status_code == 200
    options = response.json()["structured"]["follow_up_options"]
    assert "filing_review" not in {item["kind"] for item in options}
