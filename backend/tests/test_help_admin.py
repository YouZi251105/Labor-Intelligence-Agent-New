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


def test_help_resources_and_site_lawyers_are_available() -> None:
    with TestClient(app) as client:
        token = login(client, "demo", "Demo123!")
        resources = client.get("/api/v1/help/resources", headers=auth(token))
        lawyers = client.get("/api/v1/help/site-lawyers", headers=auth(token))

    assert resources.status_code == 200
    assert any(item["resource_type"] == "arbitration" for item in resources.json())
    assert lawyers.status_code == 200
    assert lawyers.json()
    assert "password_hash" not in lawyers.json()[0]
    assert "phone" not in lawyers.json()[0]


def test_profile_masks_identity_number_and_is_user_scoped() -> None:
    with TestClient(app) as client:
        token = login(client, "demo", "Demo123!")
        updated = client.put(
            "/api/v1/users/me/profile",
            headers=auth(token),
            json={
                "real_name": "张三",
                "phone": "13800000000",
                "id_number": "110101199001011234",
            },
        )
        fetched = client.get("/api/v1/users/me/profile", headers=auth(token))

    assert updated.status_code == 200
    payload = updated.json()
    assert payload["id_number_masked"] == "110***********1234"
    assert payload["verification_status"] == "pending"
    assert "id_number" not in payload
    assert "id_number_hash" not in payload
    assert fetched.json()["real_name"] == "张三"


def test_topics_only_expose_aggregated_dispute_counts() -> None:
    with TestClient(app) as client:
        token = login(client, "demo", "Demo123!")
        created = client.post(
            "/api/v1/cases",
            headers=auth(token),
            json={
                "title": "匿名聚合测试",
                "dispute_type": "overtime",
                "facts": "这一段不应出现在公共话题中的原始案情。",
            },
        )
        case_id = created.json()["id"]
        client.post(
            f"/api/v1/cases/{case_id}/consultations",
            headers=auth(token),
            json={"message": "请问加班费如何准备证据？"},
        )
        topics = client.get("/api/v1/analytics/topics", headers=auth(token))

    assert topics.status_code == 200
    serialized = topics.text
    assert "原始案情" not in serialized
    assert "case_id" not in serialized
    assert "user_id" not in serialized
    assert any(item["dispute_type"] == "overtime" for item in topics.json()["topics"])


def test_admin_can_review_rules_and_query_audit_logs() -> None:
    with TestClient(app) as client:
        admin_token = login(client, "admin", "Admin123!")
        rules = client.get("/api/v1/admin/rules", headers=auth(admin_token))
        assert rules.status_code == 200
        rule_id = rules.json()[0]["id"]
        updated = client.patch(
            f"/api/v1/admin/rules/{rule_id}",
            headers=auth(admin_token),
            json={
                "review_status": "approved",
            "source_note": "内容复核人员演示校验",
            },
        )
        audit = client.get(
            "/api/v1/admin/audit-logs?action=admin.rule_reviewed",
            headers=auth(admin_token),
        )
        user_token = login(client, "demo", "Demo123!")
        forbidden = client.get("/api/v1/admin/audit-logs", headers=auth(user_token))

    assert updated.status_code == 200
    assert updated.json()["review_status"] == "approved"
    assert audit.status_code == 200
    assert audit.json()
    assert forbidden.status_code == 403


def test_admin_material_list_omits_material_text() -> None:
    with TestClient(app) as client:
        admin_token = login(client, "admin", "Admin123!")
        response = client.get("/api/v1/admin/materials", headers=auth(admin_token))

    assert response.status_code == 200
    if response.json():
        assert "text_content" not in response.json()[0]
        assert "assessment" not in response.json()[0]


def test_admin_user_management_supports_search_pagination_and_masked_detail() -> None:
    with TestClient(app) as client:
        worker_token = login(client, "demo", "Demo123!")
        client.put(
            "/api/v1/users/me/profile",
            headers=auth(worker_token),
            json={
                "real_name": "测试劳动者",
                "phone": "13800000000",
                "id_number": "110101199001011234",
            },
        )

        admin_token = login(client, "admin", "Admin123!")
        page = client.get(
            "/api/v1/admin/users/manage?q=demo&role=user&status=active&page=1&page_size=1",
            headers=auth(admin_token),
        )
        assert page.status_code == 200
        payload = page.json()
        assert payload["total"] >= 1
        assert len(payload["items"]) == 1
        item = payload["items"][0]
        assert item["username"] == "demo"
        assert item["real_name"] == "测试劳动者"
        assert item["verification_status"] == "pending"
        assert item["id_number_masked"] == "110***********1234"
        assert "id_number" not in item
        assert "id_number_hash" not in item

        detail = client.get(
            f"/api/v1/admin/users/{item['id']}",
            headers=auth(admin_token),
        )
        verification = client.patch(
            f"/api/v1/admin/users/{item['id']}/verification",
            headers=auth(admin_token),
            json={"verification_status": "verified"},
        )
        worker_forbidden = client.get(
            "/api/v1/admin/users/manage",
            headers=auth(worker_token),
        )

    assert detail.status_code == 200
    assert detail.json()["verification_status"] == "pending"
    assert "id_number_hash" not in detail.text
    assert verification.status_code == 200
    assert verification.json()["verification_status"] == "verified"
    assert worker_forbidden.status_code == 403


def test_incomplete_profile_is_blocked_from_core_worker_features() -> None:
    with TestClient(app) as client:
        registered = client.post(
            "/api/v1/auth/register",
            json={
                "username": "profile_gate_user",
                "password": "ProfileGate123!",
                "display_name": "资料门槛用户",
            },
        )
        assert registered.status_code == 201
        token = registered.json()["access_token"]
        assert registered.json()["user"]["profile_completed"] is False

        blocked = client.post(
            "/api/v1/cases",
            headers=auth(token),
            json={"title": "未完善资料时不能创建"},
        )
        assert blocked.status_code == 403

        profile = client.put(
            "/api/v1/users/me/profile",
            headers=auth(token),
            json={
                "real_name": "资料门槛用户",
                "phone": "13900000000",
                "id_number": "110101199001011234",
            },
        )
        assert profile.status_code == 200

        me = client.get("/api/v1/auth/me", headers=auth(token))
        created = client.post(
            "/api/v1/cases",
            headers=auth(token),
            json={"title": "完善资料后可创建"},
        )

    assert me.json()["profile_completed"] is True
    assert created.status_code == 201


def test_admin_dashboard_returns_chart_ready_aggregates() -> None:
    with TestClient(app) as client:
        admin_token = login(client, "admin", "Admin123!")
        response = client.get("/api/v1/admin/dashboard", headers=auth(admin_token))
        worker_token = login(client, "demo", "Demo123!")
        forbidden = client.get("/api/v1/admin/dashboard", headers=auth(worker_token))

    assert response.status_code == 200
    payload = response.json()
    assert payload["totals"]["users"] >= 3
    assert len(payload["trends"]) == 7
    assert payload["disputes"]
    assert payload["stages"]
    assert payload["roles"]
    assert payload["verification"]
    assert forbidden.status_code == 403
