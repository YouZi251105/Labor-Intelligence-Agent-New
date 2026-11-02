from copy import deepcopy
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return auth_headers(response.json()["access_token"])


def test_admin_rule_package_lifecycle_and_runtime_publication() -> None:
    version = f"test-admin-{uuid4().hex[:8]}"
    with TestClient(app) as client:
        admin_headers = login(client, "admin", "Admin123!")
        template = client.get(
            "/api/v1/admin/rule-packages/template",
            headers=admin_headers,
        )
        assert template.status_code == 200
        content = deepcopy(template.json())
        content["version"] = version
        content["nodes"]["intake"]["options"][0]["label"] = "管理端发布路径"

        validation = client.post(
            "/api/v1/admin/rule-packages/validate",
            headers=admin_headers,
            json={"content": content},
        )
        assert validation.status_code == 200
        assert validation.json()["valid"] is True
        assert validation.json()["summary"]["option_count"] >= 2

        imported = client.post(
            "/api/v1/admin/rule-packages/import",
            headers=admin_headers,
            json={"content": content},
        )
        assert imported.status_code == 201
        package = imported.json()
        package_id = package["id"]
        assert package["version"] == version
        assert package["status"] == "draft"

        submitted = client.post(
            f"/api/v1/admin/rule-packages/{package_id}/submit",
            headers=admin_headers,
        )
        assert submitted.status_code == 200
        assert submitted.json()["status"] == "pending_review"

        approved = client.post(
            f"/api/v1/admin/rule-packages/{package_id}/review",
            headers=admin_headers,
            json={"decision": "approved", "note": "测试审核通过"},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"

        published = client.post(
            f"/api/v1/admin/rule-packages/{package_id}/publish",
            headers=admin_headers,
        )
        assert published.status_code == 200
        assert published.json()["status"] == "published"

        worker_headers = login(client, "demo", "Demo123!")
        workflow = client.get(
            "/api/v1/cases/1/workflow",
            headers=worker_headers,
        )
        assert workflow.status_code == 200
        assert workflow.json()["rule_package"]["version"] == version

        retired = client.post(
            f"/api/v1/admin/rule-packages/{package_id}/retire",
            headers=admin_headers,
        )
        assert retired.status_code == 200
        assert retired.json()["status"] == "retired"

        fallback = client.get(
            "/api/v1/cases/1/workflow",
            headers=worker_headers,
        )
        assert fallback.status_code == 200
        assert fallback.json()["rule_package"]["version"] != version


def test_invalid_rule_package_is_rejected_and_permissions_enforced() -> None:
    with TestClient(app) as client:
        admin_headers = login(client, "admin", "Admin123!")
        worker_headers = login(client, "demo", "Demo123!")
        template = client.get(
            "/api/v1/admin/rule-packages/template",
            headers=admin_headers,
        ).json()
        invalid = deepcopy(template)
        invalid["version"] = f"invalid-{uuid4().hex[:8]}"
        invalid["nodes"]["intake"]["options"][0]["target_node"] = "missing-node"

        validation = client.post(
            "/api/v1/admin/rule-packages/validate",
            headers=admin_headers,
            json={"content": invalid},
        )
        assert validation.status_code == 200
        assert validation.json()["valid"] is False
        assert validation.json()["errors"]

        imported = client.post(
            "/api/v1/admin/rule-packages/import",
            headers=admin_headers,
            json={"content": invalid},
        )
        assert imported.status_code == 422

        forbidden = client.get(
            "/api/v1/admin/rule-packages",
            headers=worker_headers,
        )
        assert forbidden.status_code == 403


def test_draft_cannot_be_published_without_review() -> None:
    with TestClient(app) as client:
        headers = login(client, "admin", "Admin123!")
        content = client.get(
            "/api/v1/admin/rule-packages/template",
            headers=headers,
        ).json()
        content["version"] = f"draft-only-{uuid4().hex[:8]}"
        imported = client.post(
            "/api/v1/admin/rule-packages/import",
            headers=headers,
            json={"content": content},
        )
        package_id = imported.json()["id"]

        published = client.post(
            f"/api/v1/admin/rule-packages/{package_id}/publish",
            headers=headers,
        )

    assert published.status_code == 409
