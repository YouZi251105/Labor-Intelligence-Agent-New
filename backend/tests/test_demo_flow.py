from fastapi.testclient import TestClient

from app.main import app


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_demo_end_to_end_flow() -> None:
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "demo", "password": "Demo123!"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]

        created = client.post(
            "/api/v1/cases",
            headers=auth_headers(token),
            json={
                "title": "工地欠薪咨询",
                "dispute_type": "labor_pay",
                "location": "上海市",
                "facts": "在工地工作三个月，没有签合同，老板拖欠工资。",
            },
        )
        assert created.status_code == 201
        case_id = created.json()["id"]

        consultation = client.post(
            f"/api/v1/cases/{case_id}/consultations",
            headers=auth_headers(token),
            json={"message": "老板已经两个月没有发工资，我该怎么办？"},
        )
        assert consultation.status_code == 200
        payload = consultation.json()
        assert payload["classification"]["dispute_type"] == "labor_pay"
        assert payload["assistant_message"]

        messages = client.get(
            f"/api/v1/cases/{case_id}/messages",
            headers=auth_headers(token),
        )
        assert messages.status_code == 200
        assert len(messages.json()) >= 2

        continued = client.post(
            f"/api/v1/cases/{case_id}/consultations",
            headers=auth_headers(token),
            json={"message": "我再补充一下，老板把我踢出工作群了。"},
        )
        assert continued.status_code == 200
        assert "结合此前对话" in continued.json()["assistant_message"]["content"]

        uploaded = client.post(
            f"/api/v1/cases/{case_id}/evidence",
            headers=auth_headers(token),
            files={
                "file": (
                    "工资流水.txt",
                    "9月工资5000元，10月工资5000元，尚未支付。".encode(),
                    "text/plain",
                )
            },
        )
        assert uploaded.status_code == 201
        assert uploaded.json()["category"] == "payroll"

        review = client.post(
            f"/api/v1/cases/{case_id}/contract-review",
            headers=auth_headers(token),
            json={
                "text": "甲方可以随时解除合同，乙方自愿放弃社会保险，工资另行约定。"
            },
        )
        assert review.status_code == 200
        assert review.json()["risk_level"] in {"medium", "high"}

        document = client.post(
            f"/api/v1/cases/{case_id}/documents",
            headers=auth_headers(token),
            json={"doc_type": "arbitration"},
        )
        assert document.status_code == 201
        assert "仲裁" in document.json()["content"]

        admin_login = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "Admin123!"},
        )
        admin_token = admin_login.json()["access_token"]
        lawyers = client.get(
            "/api/v1/admin/lawyers",
            headers=auth_headers(admin_token),
        )
        assert lawyers.status_code == 200
        lawyer_id = lawyers.json()[0]["id"]

        assigned = client.post(
            f"/api/v1/admin/cases/{case_id}/assign",
            headers=auth_headers(admin_token),
            json={"lawyer_id": lawyer_id},
        )
        assert assigned.status_code == 200
        assert assigned.json()["assigned_lawyer_id"] == lawyer_id

        lawyer_login = client.post(
            "/api/v1/auth/login",
            json={"username": "lawyer", "password": "Lawyer123!"},
        )
        lawyer_token = lawyer_login.json()["access_token"]
        lawyer_cases = client.get(
            "/api/v1/lawyer/cases",
            headers=auth_headers(lawyer_token),
        )
        assert lawyer_cases.status_code == 200
        assert any(item["id"] == case_id for item in lawyer_cases.json())

        forbidden = client.get(
            "/api/v1/admin/users",
            headers=auth_headers(lawyer_token),
        )
        assert forbidden.status_code == 403


def test_user_can_register() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "new-worker",
                "password": "NewWorker123!",
                "display_name": "新用户",
            },
        )

    assert response.status_code == 201
    assert response.json()["user"]["role"] == "user"
    assert response.json()["access_token"]


def test_document_can_be_marked_ready_only_after_filing_review() -> None:
    with TestClient(app) as client:
        user_login = client.post(
            "/api/v1/auth/login",
            json={"username": "demo", "password": "Demo123!"},
        )
        user_token = user_login.json()["access_token"]
        created = client.post(
            "/api/v1/cases",
            headers=auth_headers(user_token),
            json={
                "title": "正式文书复核门槛",
                "dispute_type": "labor_pay",
                "location": "上海市",
                "facts": "公司拖欠工资，准备申请仲裁。",
            },
        )
        case_id = created.json()["id"]
        document = client.post(
            f"/api/v1/cases/{case_id}/documents",
            headers=auth_headers(user_token),
            json={"doc_type": "arbitration"},
        )
        document_id = document.json()["id"]

        blocked = client.post(
            f"/api/v1/cases/{case_id}/documents/{document_id}/mark-ready",
            headers=auth_headers(user_token),
        )
        assert blocked.status_code == 409

        review = client.post(
            f"/api/v1/lawyer-service/cases/{case_id}/review",
            headers=auth_headers(user_token),
        )
        lawyer_login = client.post(
            "/api/v1/auth/login",
            json={"username": "lawyer", "password": "Lawyer123!"},
        )
        lawyer_token = lawyer_login.json()["access_token"]
        submitted = client.post(
            f"/api/v1/lawyer-service/reviews/{review.json()['id']}/submit",
            headers=auth_headers(lawyer_token),
            json={"conclusion": "ready_to_file", "comment": "材料可以提交"},
        )
        assert submitted.status_code == 200

        ready = client.post(
            f"/api/v1/cases/{case_id}/documents/{document_id}/mark-ready",
            headers=auth_headers(user_token),
        )
        assert ready.status_code == 200
        assert ready.json()["status"] == "ready"
