"""管理端字典版本管理测试：默认回落、草稿、校验、发布与行为生效。"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import dictionary
from app.services.evidence_rules import assess_evidence_rules


@pytest.fixture(autouse=True)
def restore_dictionary_runtime():
    yield
    dictionary.reset_runtime()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_meta_dictionary_falls_back_to_builtin_default() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/meta/dictionary")

    assert response.status_code == 200
    values = [item["value"] for item in response.json()["disputes"]]
    assert len(values) == 10
    assert "labor_other" in values


def test_dictionary_admin_requires_admin_role() -> None:
    with TestClient(app) as client:
        user_token = login(client, "demo", "Demo123!")
        response = client.get(
            "/api/v1/admin/dictionary/versions", headers=auth(user_token)
        )

    assert response.status_code == 403


def test_create_draft_rejects_invalid_content() -> None:
    with TestClient(app) as client:
        admin_token = login(client, "admin", "Admin123!")

        # 缺少兜底分类 labor_other。
        content = dictionary.build_default_package()
        content["disputes"] = [
            item
            for item in content["disputes"]
            if item["value"] != "labor_other"
        ]
        missing_fallback = client.post(
            "/api/v1/admin/dictionary/versions",
            headers=auth(admin_token),
            json={"content": content},
        )
        assert missing_fallback.status_code == 422

        # 核心材料不在必需材料中。
        content = dictionary.build_default_package()
        for item in content["disputes"]:
            if item["value"] == "labor_pay":
                item["core_categories"] = ["medical"]
        bad_core = client.post(
            "/api/v1/admin/dictionary/versions",
            headers=auth(admin_token),
            json={"content": content},
        )
        assert bad_core.status_code == 422

        # 非法分组。
        content = dictionary.build_default_package()
        for item in content["disputes"]:
            if item["value"] == "labor_pay":
                item["group"] = "civil"
        bad_group = client.post(
            "/api/v1/admin/dictionary/versions",
            headers=auth(admin_token),
            json={"content": content},
        )
        assert bad_group.status_code == 422

        # 迁移映射目标不是有效纠纷标识。
        content = dictionary.build_default_package()
        content["migrations"]["wage"] = "not_exist"
        bad_migration = client.post(
            "/api/v1/admin/dictionary/versions",
            headers=auth(admin_token),
            json={"content": content},
        )
        assert bad_migration.status_code == 422


def test_draft_can_be_updated_and_deleted() -> None:
    with TestClient(app) as client:
        admin_token = login(client, "admin", "Admin123!")
        content = dictionary.build_default_package()
        created = client.post(
            "/api/v1/admin/dictionary/versions",
            headers=auth(admin_token),
            json={"content": content},
        )
        assert created.status_code == 201
        version_id = created.json()["id"]
        assert created.json()["status"] == "draft"

        updated = client.put(
            f"/api/v1/admin/dictionary/versions/{version_id}",
            headers=auth(admin_token),
            json={"content": content},
        )
        assert updated.status_code == 200

        deleted = client.delete(
            f"/api/v1/admin/dictionary/versions/{version_id}",
            headers=auth(admin_token),
        )
        assert deleted.status_code == 204
        assert (
            client.get(
                f"/api/v1/admin/dictionary/versions/{version_id}",
                headers=auth(admin_token),
            ).status_code
            == 404
        )


def test_publish_updates_meta_and_runtime_behavior() -> None:
    with TestClient(app) as client:
        admin_token = login(client, "admin", "Admin123!")
        content = dictionary.build_default_package()
        for item in content["disputes"]:
            if item["value"] == "labor_pay":
                item["label"] = "欠薪与加班费争议"
                item["required_categories"] = ["payroll", "chat"]
                item["core_categories"] = ["payroll"]
        created = client.post(
            "/api/v1/admin/dictionary/versions",
            headers=auth(admin_token),
            json={"content": content},
        )
        assert created.status_code == 201
        version_id = created.json()["id"]
        version_number = created.json()["version"]

        published = client.post(
            f"/api/v1/admin/dictionary/versions/{version_id}/publish",
            headers=auth(admin_token),
        )
        assert published.status_code == 200

        meta = client.get("/api/v1/meta/dictionary").json()
        labor_pay = next(
            item for item in meta["disputes"] if item["value"] == "labor_pay"
        )
        assert labor_pay["label"] == "欠薪与加班费争议"

        active = client.get(
            "/api/v1/admin/dictionary/active", headers=auth(admin_token)
        ).json()
        assert active["source"] == "published"
        assert active["version"] == version_number

        # 发布后同一版本不可再发布、不可修改、不可删除。
        assert (
            client.post(
                f"/api/v1/admin/dictionary/versions/{version_id}/publish",
                headers=auth(admin_token),
            ).status_code
            == 409
        )
        assert (
            client.put(
                f"/api/v1/admin/dictionary/versions/{version_id}",
                headers=auth(admin_token),
                json={"content": content},
            ).status_code
            == 409
        )
        assert (
            client.delete(
                f"/api/v1/admin/dictionary/versions/{version_id}",
                headers=auth(admin_token),
            ).status_code
            == 409
        )

    # 运行时行为：证据规则读取包内 required/core。
    required, core = dictionary.get_runtime_rules("labor_pay")
    assert required == ["payroll", "chat"]
    assert core == ["payroll"]
    result = assess_evidence_rules(
        "labor_pay", [{"category": "payroll", "screening_status": "accepted"}]
    )
    assert result["completeness"]["missing_categories"] == ["chat"]


def test_new_custom_dispute_type_supports_consultation() -> None:
    """管理端新增自定义分类后，咨询链路不得因 AI 提示映射缺失而 500。"""
    with TestClient(app) as client:
        admin_token = login(client, "admin", "Admin123!")
        content = dictionary.build_default_package()
        content["disputes"].append(
            {
                "value": "service_contract",
                "label": "劳务合同订立争议",
                "group": "service",
                "keywords": ["劳务合同签订"],
                "required_categories": ["contract", "chat"],
                "core_categories": ["contract"],
                "claim_text": "请求确认劳务合同关系并处理相关争议。",
            }
        )
        created = client.post(
            "/api/v1/admin/dictionary/versions",
            headers=auth(admin_token),
            json={"content": content},
        )
        assert created.status_code == 201
        published = client.post(
            f"/api/v1/admin/dictionary/versions/{created.json()['id']}/publish",
            headers=auth(admin_token),
        )
        assert published.status_code == 200

        user_token = login(client, "demo", "Demo123!")
        case = client.post(
            "/api/v1/cases",
            headers=auth(user_token),
            json={
                "title": "新分类咨询",
                "dispute_type": "service_contract",
                "facts": "双方就劳务合同签订发生争议。",
            },
        )
        assert case.status_code == 201
        consultation = client.post(
            f"/api/v1/cases/{case.json()['id']}/consultations",
            headers=auth(user_token),
            json={"message": "劳务合同签订后对方不认可，怎么办？"},
        )
        assert consultation.status_code == 200


def test_new_publish_retires_previous_version() -> None:
    with TestClient(app) as client:
        admin_token = login(client, "admin", "Admin123!")

        first = client.post(
            "/api/v1/admin/dictionary/versions",
            headers=auth(admin_token),
            json={"content": dictionary.build_default_package()},
        )
        first_id = first.json()["id"]
        assert (
            client.post(
                f"/api/v1/admin/dictionary/versions/{first_id}/publish",
                headers=auth(admin_token),
            ).status_code
            == 200
        )

        second = client.post(
            "/api/v1/admin/dictionary/versions",
            headers=auth(admin_token),
            json={"content": dictionary.build_default_package()},
        )
        second_id = second.json()["id"]
        assert second.json()["version"] > first.json()["version"]
        assert (
            client.post(
                f"/api/v1/admin/dictionary/versions/{second_id}/publish",
                headers=auth(admin_token),
            ).status_code
            == 200
        )

        first_detail = client.get(
            f"/api/v1/admin/dictionary/versions/{first_id}",
            headers=auth(admin_token),
        ).json()
        second_detail = client.get(
            f"/api/v1/admin/dictionary/versions/{second_id}",
            headers=auth(admin_token),
        ).json()
        assert first_detail["status"] == "retired"
        assert second_detail["status"] == "published"
