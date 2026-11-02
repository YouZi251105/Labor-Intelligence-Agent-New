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


def create_worker_case(client: TestClient, token: str) -> int:
    response = client.post(
        "/api/v1/cases",
        headers=auth(token),
        json={
            "title": "权限边界测试",
            "dispute_type": "wage",
            "facts": "公司拖欠工资。",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def assign_lawyer(
    client: TestClient,
    admin_token: str,
    case_id: int,
    lawyer_id: int,
) -> None:
    response = client.post(
        f"/api/v1/admin/cases/{case_id}/assign",
        headers=auth(admin_token),
        json={"lawyer_id": lawyer_id},
    )
    assert response.status_code == 200


def test_profile_endpoints_are_worker_only() -> None:
    with TestClient(app) as client:
        admin_token = login(client, "admin", "Admin123!")
        lawyer_token = login(client, "lawyer", "Lawyer123!")

        admin_response = client.get(
            "/api/v1/users/me/profile",
            headers=auth(admin_token),
        )
        lawyer_response = client.put(
            "/api/v1/users/me/profile",
            headers=auth(lawyer_token),
            json={
                "real_name": "测试律师",
                "phone": "13800000000",
                "id_number": "110101199001011234",
            },
        )

    assert admin_response.status_code == 403
    assert lawyer_response.status_code == 403


def test_only_workers_can_create_cases() -> None:
    with TestClient(app) as client:
        admin_token = login(client, "admin", "Admin123!")
        lawyer_token = login(client, "lawyer", "Lawyer123!")

        admin_response = client.post(
            "/api/v1/cases",
            headers=auth(admin_token),
            json={"title": "管理员不应创建的案件"},
        )
        lawyer_response = client.post(
            "/api/v1/cases",
            headers=auth(lawyer_token),
            json={"title": "律师不应创建的案件"},
        )

    assert admin_response.status_code == 403
    assert lawyer_response.status_code == 403


def test_lawyer_can_read_assigned_case_but_cannot_consult_as_worker() -> None:
    with TestClient(app) as client:
        worker_token = login(client, "demo", "Demo123!")
        admin_token = login(client, "admin", "Admin123!")
        lawyer_token = login(client, "lawyer", "Lawyer123!")
        case_id = create_worker_case(client, worker_token)
        lawyers = client.get("/api/v1/admin/lawyers", headers=auth(admin_token))
        lawyer_id = lawyers.json()[0]["id"]
        assign_lawyer(client, admin_token, case_id, lawyer_id)

        read_response = client.get(
            f"/api/v1/cases/{case_id}/messages",
            headers=auth(lawyer_token),
        )
        consult_response = client.post(
            f"/api/v1/cases/{case_id}/consultations",
            headers=auth(lawyer_token),
            json={"message": "律师不能替用户生成普通咨询记录。"},
        )

    assert read_response.status_code == 200
    assert consult_response.status_code == 403


def test_admin_cannot_consult_as_worker() -> None:
    with TestClient(app) as client:
        worker_token = login(client, "demo", "Demo123!")
        admin_token = login(client, "admin", "Admin123!")
        case_id = create_worker_case(client, worker_token)

        response = client.post(
            f"/api/v1/cases/{case_id}/consultations",
            headers=auth(admin_token),
            json={"message": "管理员不能写入普通用户咨询。"},
        )

    assert response.status_code == 403


def test_lawyer_cannot_upload_evidence_as_worker() -> None:
    with TestClient(app) as client:
        worker_token = login(client, "demo", "Demo123!")
        admin_token = login(client, "admin", "Admin123!")
        lawyer_token = login(client, "lawyer", "Lawyer123!")
        case_id = create_worker_case(client, worker_token)
        lawyers = client.get("/api/v1/admin/lawyers", headers=auth(admin_token))
        lawyer_id = lawyers.json()[0]["id"]
        assign_lawyer(client, admin_token, case_id, lawyer_id)

        response = client.post(
            f"/api/v1/cases/{case_id}/evidence",
            headers=auth(lawyer_token),
            files={"file": ("律师上传.txt", b"test", "text/plain")},
        )

    assert response.status_code == 403


def test_lawyer_cannot_run_worker_actions_on_assigned_case() -> None:
    with TestClient(app) as client:
        worker_token = login(client, "demo", "Demo123!")
        admin_token = login(client, "admin", "Admin123!")
        lawyer_token = login(client, "lawyer", "Lawyer123!")
        case_id = create_worker_case(client, worker_token)
        lawyers = client.get("/api/v1/admin/lawyers", headers=auth(admin_token))
        lawyer_id = lawyers.json()[0]["id"]
        assign_lawyer(client, admin_token, case_id, lawyer_id)

        document_response = client.post(
            f"/api/v1/cases/{case_id}/documents",
            headers=auth(lawyer_token),
            json={"doc_type": "complaint"},
        )
        transition_response = client.post(
            f"/api/v1/cases/{case_id}/transitions",
            headers=auth(lawyer_token),
            json={"target_stage": "document"},
        )
        contract_response = client.post(
            f"/api/v1/cases/{case_id}/contract-review",
            headers=auth(lawyer_token),
            json={"text": "这是一份用于权限边界测试的劳动合同文本。"},
        )

    assert document_response.status_code == 403
    assert transition_response.status_code == 403
    assert contract_response.status_code == 403


def test_lawyer_and_admin_still_cannot_access_admin_endpoints() -> None:
    with TestClient(app) as client:
        lawyer_token = login(client, "lawyer", "Lawyer123!")
        worker_token = login(client, "demo", "Demo123!")

        lawyer_response = client.get(
            "/api/v1/admin/users",
            headers=auth(lawyer_token),
        )
        worker_response = client.get(
            "/api/v1/lawyer/cases",
            headers=auth(worker_token),
        )

    assert lawyer_response.status_code == 403
    assert worker_response.status_code == 403
