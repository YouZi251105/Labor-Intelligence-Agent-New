"""律师服务（预约/对话/复核）接口的单元测试。"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.main import app


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def create_case(client: TestClient, token: str, title: str = "律师服务测试") -> int:
    response = client.post(
        "/api/v1/cases",
        headers=auth(token),
        json={
            "title": title,
            "dispute_type": "wage",
            "location": "上海市",
            "facts": "公司拖欠工资。",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_request_accept_and_message_flow() -> None:
    with TestClient(app) as client:
        user_token = login(client, "demo", "Demo123!")
        lawyer_token = login(client, "lawyer", "Lawyer123!")
        case_id = create_case(client, user_token)

        created = client.post(
            "/api/v1/lawyer-service/requests",
            headers=auth(user_token),
            json={"case_id": case_id, "reason": "需要律师帮忙看材料", "priority": "normal"},
        )
        assert created.status_code == 201
        request_id = created.json()["id"]
        assert created.json()["status"] == "pending"

        todos = client.get("/api/v1/lawyer-service/todos", headers=auth(lawyer_token))
        assert todos.status_code == 200
        assert request_id in [item["id"] for item in todos.json()["requests"]]

        accepted = client.patch(
            f"/api/v1/lawyer-service/requests/{request_id}",
            headers=auth(lawyer_token),
            json={"accept": True},
        )
        assert accepted.status_code == 200
        assert accepted.json()["status"] == "accepted"

        sessions = client.get("/api/v1/lawyer-service/sessions", headers=auth(user_token))
        assert sessions.status_code == 200
        assert len(sessions.json()) == 1
        session_id = sessions.json()[0]["id"]

        sent_user = client.post(
            f"/api/v1/lawyer-service/sessions/{session_id}/messages",
            headers=auth(user_token),
            json={"content": "你好律师"},
        )
        assert sent_user.status_code == 201
        sent_lawyer = client.post(
            f"/api/v1/lawyer-service/sessions/{session_id}/messages",
            headers=auth(lawyer_token),
            json={"content": "你好，请说明情况"},
        )
        assert sent_lawyer.status_code == 201

        messages = client.get(
            f"/api/v1/lawyer-service/sessions/{session_id}/messages",
            headers=auth(user_token),
        )
        assert messages.status_code == 200
        assert len(messages.json()) == 2


def test_accept_assigns_case_and_todos_expose_case_summary() -> None:
    with TestClient(app) as client:
        user_token = login(client, "demo", "Demo123!")
        lawyer_token = login(client, "lawyer", "Lawyer123!")
        case_id = create_case(client, user_token, "受理分配测试")

        created = client.post(
            "/api/v1/lawyer-service/requests",
            headers=auth(user_token),
            json={"case_id": case_id, "reason": "材料复杂需要人工判断"},
        )
        assert created.status_code == 201

        todos = client.get("/api/v1/lawyer-service/todos", headers=auth(lawyer_token))
        assert todos.status_code == 200
        summary = todos.json()["cases"].get(str(case_id))
        assert summary is not None
        assert summary["title"] == "受理分配测试"

        accepted = client.patch(
            f"/api/v1/lawyer-service/requests/{created.json()['id']}",
            headers=auth(lawyer_token),
            json={"accept": True},
        )
        assert accepted.status_code == 200

        case_view = client.get(f"/api/v1/cases/{case_id}", headers=auth(lawyer_token))
        assert case_view.status_code == 200
        assert case_view.json()["assigned_lawyer_id"] is not None


def test_review_submit_assigns_case_to_lawyer() -> None:
    with TestClient(app) as client:
        user_token = login(client, "demo", "Demo123!")
        lawyer_token = login(client, "lawyer", "Lawyer123!")
        case_id = create_case(client, user_token, "复核分配测试")

        requested = client.post(
            f"/api/v1/lawyer-service/cases/{case_id}/review",
            headers=auth(user_token),
        )
        assert requested.status_code == 201
        review_id = requested.json()["id"]

        todos = client.get("/api/v1/lawyer-service/todos", headers=auth(lawyer_token))
        assert todos.status_code == 200
        assert review_id in [item["id"] for item in todos.json()["reviews"]]
        assert str(case_id) in todos.json()["cases"]

        submitted = client.post(
            f"/api/v1/lawyer-service/reviews/{review_id}/submit",
            headers=auth(lawyer_token),
            json={"conclusion": "need_more", "comment": "缺少工资流水"},
        )
        assert submitted.status_code == 200

        case_view = client.get(f"/api/v1/cases/{case_id}", headers=auth(lawyer_token))
        assert case_view.status_code == 200


def test_request_preferred_slot_and_date_validation() -> None:
    with TestClient(app) as client:
        user_token = login(client, "demo", "Demo123!")
        lawyer_token = login(client, "lawyer", "Lawyer123!")
        case_id = create_case(client, user_token, "时段预约测试")
        today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
        past = (today - timedelta(days=1)).isoformat()
        far = (today + timedelta(days=15)).isoformat()
        valid = (today + timedelta(days=3)).isoformat()

        past_response = client.post(
            "/api/v1/lawyer-service/requests",
            headers=auth(user_token),
            json={
                "case_id": case_id,
                "reason": "日期已过去",
                "preferred_date": past,
                "preferred_slot": "evening",
            },
        )
        assert past_response.status_code == 400
        assert "不能早于" in past_response.json()["detail"]

        far_response = client.post(
            "/api/v1/lawyer-service/requests",
            headers=auth(user_token),
            json={
                "case_id": case_id,
                "reason": "超过 14 天",
                "preferred_date": far,
                "preferred_slot": "morning",
            },
        )
        assert far_response.status_code == 400
        assert "14 天" in far_response.json()["detail"]

        created = client.post(
            "/api/v1/lawyer-service/requests",
            headers=auth(user_token),
            json={
                "case_id": case_id,
                "reason": "材料复杂，希望晚间沟通",
                "preferred_date": valid,
                "preferred_slot": "evening",
            },
        )
        assert created.status_code == 201
        body = created.json()
        assert body["preferred_date"] == valid
        assert body["preferred_slot"] == "evening"
        assert "18:00" in body["preferred_time"]

        todos = client.get("/api/v1/lawyer-service/todos", headers=auth(lawyer_token))
        assert todos.status_code == 200
        assert body["id"] in [item["id"] for item in todos.json()["requests"]]


def test_reject_request_requires_reason() -> None:
    with TestClient(app) as client:
        user_token = login(client, "demo", "Demo123!")
        lawyer_token = login(client, "lawyer", "Lawyer123!")
        case_id = create_case(client, user_token, "拒绝理由测试")

        created = client.post(
            "/api/v1/lawyer-service/requests",
            headers=auth(user_token),
            json={"case_id": case_id, "reason": "需要人工判断"},
        )
        assert created.status_code == 201
        request_id = created.json()["id"]

        missing_reason = client.patch(
            f"/api/v1/lawyer-service/requests/{request_id}",
            headers=auth(lawyer_token),
            json={"accept": False},
        )
        assert missing_reason.status_code == 422

        rejected = client.patch(
            f"/api/v1/lawyer-service/requests/{request_id}",
            headers=auth(lawyer_token),
            json={"accept": False, "reject_reason": "近期时段已排满，请改约"},
        )
        assert rejected.status_code == 200
        body = rejected.json()
        assert body["status"] == "rejected"
        assert body["reject_reason"] == "近期时段已排满，请改约"


def test_duplicate_active_request_conflict() -> None:
    with TestClient(app) as client:
        user_token = login(client, "demo", "Demo123!")
        case_id = create_case(client, user_token)

        first = client.post(
            "/api/v1/lawyer-service/requests",
            headers=auth(user_token),
            json={"case_id": case_id, "reason": "第一次预约"},
        )
        assert first.status_code == 201

        second = client.post(
            "/api/v1/lawyer-service/requests",
            headers=auth(user_token),
            json={"case_id": case_id, "reason": "重复预约"},
        )
        assert second.status_code == 409


def test_cancel_request() -> None:
    with TestClient(app) as client:
        user_token = login(client, "demo", "Demo123!")
        case_id = create_case(client, user_token)

        created = client.post(
            "/api/v1/lawyer-service/requests",
            headers=auth(user_token),
            json={"case_id": case_id, "reason": "预约后取消"},
        )
        request_id = created.json()["id"]

        cancelled = client.post(
            f"/api/v1/lawyer-service/requests/{request_id}/cancel",
            headers=auth(user_token),
        )
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"


def test_message_permission_rejects_non_participant() -> None:
    with TestClient(app) as client:
        user_token = login(client, "demo", "Demo123!")
        lawyer_token = login(client, "lawyer", "Lawyer123!")
        admin_token = login(client, "admin", "Admin123!")
        case_id = create_case(client, user_token)

        created = client.post(
            "/api/v1/lawyer-service/requests",
            headers=auth(user_token),
            json={"case_id": case_id, "reason": "权限测试"},
        )
        request_id = created.json()["id"]
        client.patch(
            f"/api/v1/lawyer-service/requests/{request_id}",
            headers=auth(lawyer_token),
            json={"accept": True},
        )
        sessions = client.get("/api/v1/lawyer-service/sessions", headers=auth(user_token))
        session_id = sessions.json()[0]["id"]

        forbidden = client.get(
            f"/api/v1/lawyer-service/sessions/{session_id}/messages",
            headers=auth(admin_token),
        )
        assert forbidden.status_code == 404


def test_review_flow_and_duplicate_conflict() -> None:
    with TestClient(app) as client:
        user_token = login(client, "demo", "Demo123!")
        lawyer_token = login(client, "lawyer", "Lawyer123!")
        case_id = create_case(client, user_token)

        requested = client.post(
            f"/api/v1/lawyer-service/cases/{case_id}/review",
            headers=auth(user_token),
        )
        assert requested.status_code == 201
        review_id = requested.json()["id"]
        assert requested.json()["status"] == "pending"

        duplicate = client.post(
            f"/api/v1/lawyer-service/cases/{case_id}/review",
            headers=auth(user_token),
        )
        assert duplicate.status_code == 409

        submitted = client.post(
            f"/api/v1/lawyer-service/reviews/{review_id}/submit",
            headers=auth(lawyer_token),
            json={"conclusion": "ready_to_file", "comment": "材料齐全，可以立案"},
        )
        assert submitted.status_code == 200
        assert submitted.json()["status"] == "reviewed"
        assert submitted.json()["conclusion"] == "ready_to_file"

        got = client.get(
            f"/api/v1/lawyer-service/cases/{case_id}/review",
            headers=auth(user_token),
        )
        assert got.status_code == 200
        assert got.json()["conclusion"] == "ready_to_file"
