from fastapi.testclient import TestClient

from app.main import app


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_workflow_requires_evidence_before_procedure() -> None:
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "demo", "password": "Demo123!"},
        )
        token = login.json()["access_token"]
        headers = auth_headers(token)

        created = client.post(
            "/api/v1/cases",
            headers=headers,
            json={
                "title": "工作流欠薪案件",
                "dispute_type": "wage",
                "location": "上海市",
                "facts": "公司拖欠工资，目前没有书面合同。",
            },
        )
        case_id = created.json()["id"]
        client.post(
            f"/api/v1/cases/{case_id}/consultations",
            headers=headers,
            json={"message": "老板拖欠工资两个月了。"},
        )

        workflow = client.get(
            f"/api/v1/cases/{case_id}/workflow",
            headers=headers,
        )
        assert workflow.status_code == 200
        payload = workflow.json()
        assert payload["current_stage"] == "evidence"
        option = next(
            item for item in payload["options"] if item["target_stage"] == "procedure"
        )
        assert option["enabled"] is False
        assert option["blocked_reasons"]

        blocked = client.post(
            f"/api/v1/cases/{case_id}/transitions",
            headers=headers,
            json={"target_stage": "procedure", "note": "尝试直接推进"},
        )
        assert blocked.status_code == 400

        uploads = [
            ("工资流水.txt", "9月工资5000元，10月工资5000元，尚未支付。"),
            ("聊天记录.txt", "老板：工资下周再发。劳动者：已经拖欠两个月。"),
            ("劳动合同.txt", "劳动合同约定月工资5000元，按月支付。"),
        ]
        for filename, content in uploads:
            response = client.post(
                f"/api/v1/cases/{case_id}/evidence",
                headers=headers,
                files={"file": (filename, content.encode(), "text/plain")},
            )
            assert response.status_code == 201

        ready_workflow = client.get(
            f"/api/v1/cases/{case_id}/workflow",
            headers=headers,
        ).json()
        ready_option = next(
            item
            for item in ready_workflow["options"]
            if item["target_stage"] == "procedure"
        )
        assert ready_option["enabled"] is True

        transitioned = client.post(
            f"/api/v1/cases/{case_id}/transitions",
            headers=headers,
            json={"target_stage": "procedure", "note": "材料已补齐"},
        )
        assert transitioned.status_code == 200
        assert transitioned.json()["current_stage"] == "procedure"


def test_consultation_returns_structured_ai_result() -> None:
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "demo", "password": "Demo123!"},
        )
        headers = auth_headers(login.json()["access_token"])
        created = client.post(
            "/api/v1/cases",
            headers=headers,
            json={
                "title": "AI结构化测试",
                "dispute_type": "general",
                "facts": "公司拖欠工资。",
            },
        )
        case_id = created.json()["id"]

        response = client.post(
            f"/api/v1/cases/{case_id}/consultations",
            headers=headers,
            json={"message": "公司拖欠我两个月工资，我该怎么处理？"},
        )

    assert response.status_code == 200
    structured = response.json()["structured"]
    assert structured["intent"] == "wage"
    assert structured["demo_mode"] is True
    assert structured["suggested_next_step"]
    assert structured["required_information"]


def test_workflow_exposes_reviewed_rule_package_and_multiple_paths() -> None:
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "demo", "password": "Demo123!"},
        )
        headers = auth_headers(login.json()["access_token"])
        created = client.post(
            "/api/v1/cases",
            headers=headers,
            json={
                "title": "决策树多路径测试",
                "dispute_type": "wage",
                "facts": "公司拖欠工资。",
            },
        )
        case_id = created.json()["id"]

        workflow = client.get(
            f"/api/v1/cases/{case_id}/workflow",
            headers=headers,
        )

    assert workflow.status_code == 200
    payload = workflow.json()
    assert payload["current_node"] == "intake"
    assert payload["rule_package"]["package_id"] == "cn-labor-workflow"
    assert payload["rule_package"]["review_status"] == "pending_review"
    assert payload["decision_path"] == []

    options = {item["id"]: item for item in payload["options"]}
    assert {"start-evidence", "request-lawyer-first"} <= options.keys()
    assert options["start-evidence"]["outcome"]
    assert options["start-evidence"]["next_step"]
    assert options["start-evidence"]["deadlines"][0]["review_status"] == (
        "pending_review"
    )


def test_option_id_transition_persists_decision_path() -> None:
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "demo", "password": "Demo123!"},
        )
        headers = auth_headers(login.json()["access_token"])
        created = client.post(
            "/api/v1/cases",
            headers=headers,
            json={
                "title": "决策路径持久化测试",
                "dispute_type": "wage",
                "facts": "需要先咨询律师。",
            },
        )
        case_id = created.json()["id"]

        transitioned = client.post(
            f"/api/v1/cases/{case_id}/transitions",
            headers=headers,
            json={
                "option_id": "request-lawyer-first",
                "note": "期限可能比较紧急",
            },
        )
        refreshed = client.get(
            f"/api/v1/cases/{case_id}",
            headers=headers,
        )
        workflow = client.get(
            f"/api/v1/cases/{case_id}/workflow",
            headers=headers,
        )
        invalid = client.post(
            f"/api/v1/cases/{case_id}/transitions",
            headers=headers,
            json={"option_id": "missing-option"},
        )

    assert transitioned.status_code == 200
    transitioned_payload = transitioned.json()
    assert transitioned_payload["current_stage"] == "lawyer_help"
    assert transitioned_payload["decision_path"][0]["option_id"] == (
        "request-lawyer-first"
    )
    assert transitioned_payload["decision_path"][0]["rule_package_version"]
    assert refreshed.status_code == 200
    choices = refreshed.json()["classification"]["workflow_choices"]
    assert choices[0]["to_node"] == "lawyer_help"
    assert choices[0]["note"] == "期限可能比较紧急"
    assert workflow.json()["decision_path"][0]["option_id"] == (
        "request-lawyer-first"
    )
    assert invalid.status_code == 400
