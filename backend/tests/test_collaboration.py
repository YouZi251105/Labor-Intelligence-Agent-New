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


def create_case(client: TestClient, token: str, title: str) -> int:
    response = client.post(
        "/api/v1/cases",
        headers=auth(token),
        json={
            "title": title,
            "dispute_type": "wage",
            "facts": "公司拖欠工资。",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def assign_demo_lawyer(client: TestClient, admin_token: str, case_id: int) -> int:
    lawyers = client.get("/api/v1/admin/lawyers", headers=auth(admin_token))
    lawyer_id = lawyers.json()[0]["id"]
    assigned = client.post(
        f"/api/v1/admin/cases/{case_id}/assign",
        headers=auth(admin_token),
        json={"lawyer_id": lawyer_id},
    )
    assert assigned.status_code == 200
    return lawyer_id


def test_lawyer_can_add_opinion_and_service_record() -> None:
    with TestClient(app) as client:
        admin_token = login(client, "admin", "Admin123!")
        user_token = login(client, "demo", "Demo123!")
        lawyer_token = login(client, "lawyer", "Lawyer123!")
        case_id = create_case(client, user_token, "律师协作测试")
        lawyer_id = assign_demo_lawyer(client, admin_token, case_id)

        opinion = client.post(
            f"/api/v1/lawyer/cases/{case_id}/opinions",
            headers=auth(lawyer_token),
            json={"content": "建议补充工资流水，并向单位发送书面催告。"},
        )
        record = client.post(
            "/api/v1/lawyer/service-records",
            headers=auth(lawyer_token),
            json={
                "case_id": case_id,
                "service_type": "consultation",
                "summary": "电话沟通证据清单",
                "duration_minutes": 30,
            },
        )

    assert opinion.status_code == 201
    assert opinion.json()["lawyer_id"] == lawyer_id
    assert record.status_code == 201
    assert record.json()["status"] == "pending"


def test_service_status_transitions_are_ordered() -> None:
    with TestClient(app) as client:
        admin_token = login(client, "admin", "Admin123!")
        user_token = login(client, "demo", "Demo123!")
        lawyer_token = login(client, "lawyer", "Lawyer123!")
        case_id = create_case(client, user_token, "服务状态测试")
        assign_demo_lawyer(client, admin_token, case_id)
        record = client.post(
            "/api/v1/lawyer/service-records",
            headers=auth(lawyer_token),
            json={
                "case_id": case_id,
                "service_type": "evidence",
                "summary": "整理工资记录",
                "duration_minutes": 20,
            },
        )
        record_id = record.json()["id"]
        completed_directly = client.patch(
            f"/api/v1/lawyer/service-records/{record_id}/status",
            headers=auth(lawyer_token),
            json={"status": "completed"},
        )
        in_progress = client.patch(
            f"/api/v1/lawyer/service-records/{record_id}/status",
            headers=auth(lawyer_token),
            json={"status": "in_progress"},
        )
        completed = client.patch(
            f"/api/v1/lawyer/service-records/{record_id}/status",
            headers=auth(lawyer_token),
            json={"status": "completed"},
        )

    assert completed_directly.status_code == 400
    assert in_progress.status_code == 200
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"


def test_revenue_is_created_by_lawyer_and_confirmed_by_admin() -> None:
    with TestClient(app) as client:
        admin_token = login(client, "admin", "Admin123!")
        user_token = login(client, "demo", "Demo123!")
        lawyer_token = login(client, "lawyer", "Lawyer123!")
        case_id = create_case(client, user_token, "收益台账测试")
        lawyer_id = assign_demo_lawyer(client, admin_token, case_id)
        created = client.post(
            "/api/v1/lawyer/revenue",
            headers=auth(lawyer_token),
            json={
                "case_id": case_id,
                "amount_cents": 19900,
                "entry_type": "consultation",
                "note": "演示咨询收入",
            },
        )
        entry_id = created.json()["id"]
        admin_list = client.get("/api/v1/admin/revenue", headers=auth(admin_token))
        lawyer_status_attempt = client.patch(
            f"/api/v1/admin/revenue/{entry_id}/status",
            headers=auth(lawyer_token),
            json={"status": "confirmed"},
        )
        confirmed = client.patch(
            f"/api/v1/admin/revenue/{entry_id}/status",
            headers=auth(admin_token),
            json={"status": "confirmed"},
        )

    assert created.status_code == 201
    assert created.json()["lawyer_id"] == lawyer_id
    assert created.json()["status"] == "pending"
    assert any(item["id"] == entry_id for item in admin_list.json())
    assert lawyer_status_attempt.status_code == 403
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"


def test_lawyer_cannot_add_opinion_to_unassigned_case() -> None:
    with TestClient(app) as client:
        user_token = login(client, "demo", "Demo123!")
        lawyer_token = login(client, "lawyer", "Lawyer123!")
        case_id = create_case(client, user_token, "未分配案件")
        response = client.post(
            f"/api/v1/lawyer/cases/{case_id}/opinions",
            headers=auth(lawyer_token),
            json={"content": "不应写入的律师意见内容。"},
        )

    assert response.status_code == 404
