"""律师服务（预约/对话/复核）接口的单元测试。"""
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
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


def test_first_message_starts_session_and_close_completes_request() -> None:
    with TestClient(app) as client:
        user_token = login(client, "demo", "Demo123!")
        lawyer_token = login(client, "lawyer", "Lawyer123!")
        case_id = create_case(client, user_token, "会话状态流转测试")

        created = client.post(
            "/api/v1/lawyer-service/requests",
            headers=auth(user_token),
            json={"case_id": case_id, "reason": "需要律师在线沟通"},
        )
        request_id = created.json()["id"]
        accepted = client.patch(
            f"/api/v1/lawyer-service/requests/{request_id}",
            headers=auth(lawyer_token),
            json={"accept": True},
        )
        assert accepted.status_code == 200

        sessions = client.get(
            "/api/v1/lawyer-service/sessions",
            headers=auth(user_token),
        ).json()
        session_id = sessions[0]["id"]
        sent = client.post(
            f"/api/v1/lawyer-service/sessions/{session_id}/messages",
            headers=auth(user_token),
            json={"content": "请帮我确认下一步。"},
        )
        assert sent.status_code == 201

        requests = client.get(
            "/api/v1/lawyer-service/requests",
            headers=auth(user_token),
        ).json()
        current = next(item for item in requests if item["id"] == request_id)
        assert current["status"] == "in_session"

        duplicate = client.post(
            "/api/v1/lawyer-service/requests",
            headers=auth(user_token),
            json={"case_id": case_id, "reason": "重复预约"},
        )
        assert duplicate.status_code == 409

        closed = client.post(
            f"/api/v1/lawyer-service/sessions/{session_id}/close",
            headers=auth(user_token),
        )
        assert closed.status_code == 200

        requests = client.get(
            "/api/v1/lawyer-service/requests",
            headers=auth(user_token),
        ).json()
        current = next(item for item in requests if item["id"] == request_id)
        assert current["status"] == "completed"


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


def test_assigned_case_queue_and_review_stay_with_assigned_lawyer() -> None:
    with TestClient(app) as client:
        user_token = login(client, "demo", "Demo123!")
        lawyer_token = login(client, "lawyer", "Lawyer123!")
        admin_token = login(client, "admin", "Admin123!")
        case_id = create_case(client, user_token, "复核分配冲突测试")

        assigned_lawyer = client.get("/api/v1/auth/me", headers=auth(lawyer_token)).json()
        assigned = client.post(
            f"/api/v1/admin/cases/{case_id}/assign",
            headers=auth(admin_token),
            json={"lawyer_id": assigned_lawyer["id"]},
        )
        assert assigned.status_code == 200

        username = f"lawyer_review_conflict_{uuid4().hex}"
        asyncio.run(_insert_lawyer_user(username))
        other_token = login(client, username, "Lawyer123!")
        pending_request = client.post(
            "/api/v1/lawyer-service/requests",
            headers=auth(user_token),
            json={"case_id": case_id, "reason": "仅应由承办律师处理"},
        )
        assert pending_request.status_code == 201
        other_requests = client.get(
            "/api/v1/lawyer-service/requests",
            headers=auth(other_token),
        )
        assert pending_request.json()["id"] not in [
            item["id"] for item in other_requests.json()
        ]
        rejected_by_other = client.patch(
            f"/api/v1/lawyer-service/requests/{pending_request.json()['id']}",
            headers=auth(other_token),
            json={"accept": False, "reject_reason": "不应由其他律师拒绝"},
        )
        assert rejected_by_other.status_code == 409

        review = client.post(
            f"/api/v1/lawyer-service/cases/{case_id}/review",
            headers=auth(user_token),
        )
        assert review.status_code == 201
        review_id = review.json()["id"]
        other_todos = client.get(
            "/api/v1/lawyer-service/todos",
            headers=auth(other_token),
        )
        assert review_id not in [item["id"] for item in other_todos.json()["reviews"]]
        other_brief = client.get(
            f"/api/v1/lawyer-service/reviews/{review_id}/case-brief",
            headers=auth(other_token),
        )
        assert other_brief.status_code == 404

        blocked = client.post(
            f"/api/v1/lawyer-service/reviews/{review_id}/submit",
            headers=auth(other_token),
            json={"conclusion": "need_more", "comment": "由其他律师承办"},
        )
        assert blocked.status_code == 409


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
                "reason": "超过 7 天",
                "preferred_date": far,
                "preferred_slot": "morning",
            },
        )
        assert far_response.status_code == 400
        assert "7 天" in far_response.json()["detail"]

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


def test_review_case_brief_accessible_to_lawyer() -> None:
    with TestClient(app) as client:
        user_token = login(client, "demo", "Demo123!")
        lawyer_token = login(client, "lawyer", "Lawyer123!")
        case_id = create_case(client, user_token, "复核简报测试")

        created = client.post(
            f"/api/v1/lawyer-service/cases/{case_id}/review",
            headers=auth(user_token),
        )
        assert created.status_code == 201
        review_id = created.json()["id"]

        brief = client.get(
            f"/api/v1/lawyer-service/reviews/{review_id}/case-brief",
            headers=auth(lawyer_token),
        )
        assert brief.status_code == 200
        body = brief.json()
        assert body["case"]["id"] == case_id
        assert body["case"]["facts"]
        assert body["evidence"]["items"] == []
        assert "missing_labels" in body["evidence"]["assessment"]
        assert body["documents"] == []

        forbidden = client.get(
            f"/api/v1/lawyer-service/reviews/{review_id}/case-brief",
            headers=auth(user_token),
        )
        assert forbidden.status_code == 403


def test_review_user_decision_flow() -> None:
    with TestClient(app) as client:
        user_token = login(client, "demo", "Demo123!")
        lawyer_token = login(client, "lawyer", "Lawyer123!")
        case_id = create_case(client, user_token, "复核后选择测试")

        review = client.post(
            f"/api/v1/lawyer-service/cases/{case_id}/review",
            headers=auth(user_token),
        )
        assert review.status_code == 201
        review_id = review.json()["id"]

        early = client.post(
            f"/api/v1/lawyer-service/reviews/{review_id}/decision",
            headers=auth(user_token),
            json={"decision": "self_handle"},
        )
        assert early.status_code == 409

        submitted = client.post(
            f"/api/v1/lawyer-service/reviews/{review_id}/submit",
            headers=auth(lawyer_token),
            json={"conclusion": "ready_to_file", "comment": "材料齐全"},
        )
        assert submitted.status_code == 200

        decided = client.post(
            f"/api/v1/lawyer-service/reviews/{review_id}/decision",
            headers=auth(user_token),
            json={"decision": "self_handle"},
        )
        assert decided.status_code == 200
        body = decided.json()
        assert body["user_decision"] == "self_handle"
        assert body["user_decision_at"]

        changed = client.post(
            f"/api/v1/lawyer-service/reviews/{review_id}/decision",
            headers=auth(user_token),
            json={"decision": "lawyer_assist"},
        )
        assert changed.status_code == 200
        assert changed.json()["user_decision"] == "lawyer_assist"

        detail = client.get(
            f"/api/v1/lawyer-service/cases/{case_id}/review",
            headers=auth(user_token),
        )
        assert detail.status_code == 200
        assert detail.json()["user_decision"] == "lawyer_assist"


def test_todos_urgent_first() -> None:
    with TestClient(app) as client:
        user_token = login(client, "demo", "Demo123!")
        lawyer_token = login(client, "lawyer", "Lawyer123!")
        normal_id = create_case(client, user_token, "普通预约")
        urgent_id = create_case(client, user_token, "加急预约")

        client.post(
            "/api/v1/lawyer-service/requests",
            headers=auth(user_token),
            json={"case_id": normal_id, "reason": "普通问题"},
        )
        client.post(
            "/api/v1/lawyer-service/requests",
            headers=auth(user_token),
            json={"case_id": urgent_id, "reason": "紧急问题", "priority": "urgent"},
        )

        todos = client.get("/api/v1/lawyer-service/todos", headers=auth(lawyer_token))
        assert todos.status_code == 200
        request_cases = [item["case_id"] for item in todos.json()["requests"]]
        assert request_cases.index(urgent_id) < request_cases.index(normal_id)


async def _insert_lawyer_user(username: str) -> int:
    from app.core.security import hash_password
    from app.db.session import get_session_factory
    from app.models.user import User

    factory = get_session_factory()
    async with factory() as session:
        user = User(
            username=username,
            password_hash=hash_password("Lawyer123!"),
            role="lawyer",
            display_name=username,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user.id


def test_accept_request_blocked_when_case_assigned_to_other_lawyer() -> None:
    with TestClient(app) as client:
        user_token = login(client, "demo", "Demo123!")
        lawyer_token = login(client, "lawyer", "Lawyer123!")
        admin_token = login(client, "admin", "Admin123!")
        case_id = create_case(client, user_token, "分配冲突测试")

        me = client.get("/api/v1/auth/me", headers=auth(lawyer_token)).json()
        assigned = client.post(
            f"/api/v1/admin/cases/{case_id}/assign",
            headers=auth(admin_token),
            json={"lawyer_id": me["id"]},
        )
        assert assigned.status_code == 200

        asyncio.run(_insert_lawyer_user("lawyer_conflict"))
        other_token = login(client, "lawyer_conflict", "Lawyer123!")

        request = client.post(
            "/api/v1/lawyer-service/requests",
            headers=auth(user_token),
            json={"case_id": case_id, "reason": "需要律师判断"},
        )
        assert request.status_code == 201
        request_id = request.json()["id"]

        blocked = client.patch(
            f"/api/v1/lawyer-service/requests/{request_id}",
            headers=auth(other_token),
            json={"accept": True},
        )
        assert blocked.status_code == 409

        accepted = client.patch(
            f"/api/v1/lawyer-service/requests/{request_id}",
            headers=auth(lawyer_token),
            json={"accept": True},
        )
        assert accepted.status_code == 200
        assert accepted.json()["lawyer_id"] == me["id"]


def test_consultation_attachment_flow() -> None:
    with TestClient(app) as client:
        user_token = login(client, "demo", "Demo123!")
        lawyer_token = login(client, "lawyer", "Lawyer123!")
        admin_token = login(client, "admin", "Admin123!")
        case_id = create_case(client, user_token, "附件流程测试")

        created = client.post(
            "/api/v1/lawyer-service/requests",
            headers=auth(user_token),
            json={"case_id": case_id, "reason": "发附件给律师"},
        )
        assert created.status_code == 201
        request_id = created.json()["id"]
        accepted = client.patch(
            f"/api/v1/lawyer-service/requests/{request_id}",
            headers=auth(lawyer_token),
            json={"accept": True},
        )
        assert accepted.status_code == 200
        sessions = client.get("/api/v1/lawyer-service/sessions", headers=auth(user_token))
        session_id = sessions.json()[0]["id"]

        attachment = client.post(
            f"/api/v1/lawyer-service/sessions/{session_id}/messages/file",
            headers=auth(user_token),
            data={"content": "这是我的工资流水"},
            files={"file": ("工资流水.txt", "实发工资 5000 元，拖欠两个月".encode(), "text/plain")},
        )
        assert attachment.status_code == 201
        payload = attachment.json()
        assert payload["attachment_name"] == "工资流水.txt"
        assert payload["attachment_size"] > 0

        messages = client.get(
            f"/api/v1/lawyer-service/sessions/{session_id}/messages",
            headers=auth(user_token),
        )
        target = [m for m in messages.json() if m["id"] == payload["id"]][0]
        assert target["attachment_name"] == "工资流水.txt"

        download = client.get(
            f"/api/v1/lawyer-service/sessions/{session_id}/messages/{payload['id']}/attachment",
            headers=auth(lawyer_token),
        )
        assert download.status_code == 200
        assert b"5000" in download.content

        non_party = client.get(
            f"/api/v1/lawyer-service/sessions/{session_id}/messages/{payload['id']}/attachment",
            headers=auth(admin_token),
        )
        assert non_party.status_code == 404

        rejected = client.post(
            f"/api/v1/lawyer-service/sessions/{session_id}/messages/file",
            headers=auth(user_token),
            files={"file": ("恶意.exe", b"MZ", "application/x-msdownload")},
        )
        assert rejected.status_code == 400


def test_request_date_within_seven_days() -> None:
    with TestClient(app) as client:
        user_token = login(client, "demo", "Demo123!")
        case_id = create_case(client, user_token, "七日预约测试")
        far = (datetime.now(ZoneInfo("Asia/Shanghai")).date() + timedelta(days=10)).isoformat()

        created = client.post(
            "/api/v1/lawyer-service/requests",
            headers=auth(user_token),
            json={"case_id": case_id, "reason": "预约超出范围", "preferred_date": far},
        )
        assert created.status_code == 400
        assert "7 天" in created.json()["detail"]


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


def test_lawyer_cannot_cancel_another_users_request() -> None:
    with TestClient(app) as client:
        user_token = login(client, "demo", "Demo123!")
        case_id = create_case(client, user_token, "取消预约权限测试")
        created = client.post(
            "/api/v1/lawyer-service/requests",
            headers=auth(user_token),
            json={"case_id": case_id, "reason": "预约后由他人尝试取消"},
        )
        assert created.status_code == 201

        username = f"lawyer_cancel_guard_{uuid4().hex}"
        asyncio.run(_insert_lawyer_user(username))
        lawyer_token = login(client, username, "Lawyer123!")
        forbidden = client.post(
            f"/api/v1/lawyer-service/requests/{created.json()['id']}/cancel",
            headers=auth(lawyer_token),
        )
        assert forbidden.status_code == 404


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


def test_case_resolution_is_recorded_in_case_context() -> None:
    with TestClient(app) as client:
        user_token = login(client, "demo", "Demo123!")
        case_id = create_case(client, user_token, "最终去向确认")

        response = client.post(
            f"/api/v1/lawyer-service/cases/{case_id}/resolution",
            headers=auth(user_token),
            json={"decision": "self_handle"},
        )

        assert response.status_code == 200
        classification = response.json()["classification"]
        assert classification["resolution_decision"] == "self_handle"
        assert classification["resolution_confirmed_at"]
