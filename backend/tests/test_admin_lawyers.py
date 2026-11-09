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


def lawyer_payload(
    username: str,
    license_no: str,
    *,
    password: str = "NewLawyer123!",
) -> dict[str, str]:
    return {
        "username": username,
        "password": password,
        "display_name": "自动化测试律师",
        "phone": "13800001111",
        "license_no": license_no,
        "specialties": "欠薪、违法解除",
        "bio": "用于验证管理员创建律师账号。",
        "status": "active",
    }


def test_admin_can_create_lawyer_account_and_new_lawyer_can_login() -> None:
    with TestClient(app) as client:
        admin_token = login(client, "admin", "Admin123!")
        created = client.post(
            "/api/v1/admin/lawyers",
            headers=auth(admin_token),
            json=lawyer_payload("created_lawyer", "TEST-LAWYER-001"),
        )
        assert created.status_code == 201
        assert created.json()["username"] == "created_lawyer"
        assert created.json()["license_no"] == "TEST-LAWYER-001"
        assert created.json()["status"] == "active"

        lawyer_token = login(client, "created_lawyer", "NewLawyer123!")
        me = client.get("/api/v1/auth/me", headers=auth(lawyer_token))
        assert me.status_code == 200
        assert me.json()["role"] == "lawyer"
        assert me.json()["display_name"] == "自动化测试律师"

        lawyers = client.get("/api/v1/admin/lawyers", headers=auth(admin_token))
        assert lawyers.status_code == 200
        assert any(
            item["username"] == "created_lawyer" for item in lawyers.json()
        )

        audit = client.get(
            "/api/v1/admin/audit-logs?limit=30",
            headers=auth(admin_token),
        )
        assert audit.status_code == 200
        assert any(
            item["action"] == "admin.lawyer_created"
            for item in audit.json()
        )


def test_admin_lawyer_creation_rejects_duplicates_and_invalid_payload() -> None:
    with TestClient(app) as client:
        admin_token = login(client, "admin", "Admin123!")
        first = client.post(
            "/api/v1/admin/lawyers",
            headers=auth(admin_token),
            json=lawyer_payload("duplicate_lawyer", "TEST-LAWYER-002"),
        )
        assert first.status_code == 201

        duplicate_username = client.post(
            "/api/v1/admin/lawyers",
            headers=auth(admin_token),
            json=lawyer_payload("duplicate_lawyer", "TEST-LAWYER-003"),
        )
        assert duplicate_username.status_code == 409
        assert "用户名" in duplicate_username.json()["detail"]

        duplicate_license = client.post(
            "/api/v1/admin/lawyers",
            headers=auth(admin_token),
            json=lawyer_payload("duplicate_license", "TEST-LAWYER-002"),
        )
        assert duplicate_license.status_code == 409
        assert "执业证号" in duplicate_license.json()["detail"]

        short_password = client.post(
            "/api/v1/admin/lawyers",
            headers=auth(admin_token),
            json=lawyer_payload(
                "short_password_lawyer",
                "TEST-LAWYER-004",
                password="short",
            ),
        )
        assert short_password.status_code == 422


def test_non_admin_cannot_create_lawyer_account() -> None:
    with TestClient(app) as client:
        lawyer_token = login(client, "lawyer", "Lawyer123!")
        response = client.post(
            "/api/v1/admin/lawyers",
            headers=auth(lawyer_token),
            json=lawyer_payload("forbidden_lawyer", "TEST-LAWYER-005"),
        )
        assert response.status_code == 403
