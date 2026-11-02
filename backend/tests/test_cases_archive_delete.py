"""案件归档与删除接口的单元测试。"""
from fastapi.testclient import TestClient

from app.main import app


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login_demo(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "demo", "password": "Demo123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def create_case(
    client: TestClient,
    token: str,
    title: str,
    dispute_type: str = "wage",
    facts: str = "公司拖欠工资。",
) -> int:
    response = client.post(
        "/api/v1/cases",
        headers=auth_headers(token),
        json={
            "title": title,
            "dispute_type": dispute_type,
            "location": "上海市",
            "facts": facts,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def list_ids(client: TestClient, token: str, status: str = "active") -> set[int]:
    response = client.get(
        f"/api/v1/cases?status={status}",
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    return {item["id"] for item in response.json()}


def test_archive_toggles_between_active_and_archived() -> None:
    with TestClient(app) as client:
        token = login_demo(client)
        case_id = create_case(client, token, "归档测试案件")

        archive = client.patch(
            f"/api/v1/cases/{case_id}/archive",
            headers=auth_headers(token),
            json={"archived": True},
        )
        assert archive.status_code == 200
        assert archive.json()["archived"] is True
        assert case_id not in list_ids(client, token, "active")
        assert case_id in list_ids(client, token, "archived")

        unarchive = client.patch(
            f"/api/v1/cases/{case_id}/archive",
            headers=auth_headers(token),
            json={"archived": False},
        )
        assert unarchive.status_code == 200
        assert unarchive.json()["archived"] is False
        assert case_id in list_ids(client, token, "active")


def test_delete_empty_case_succeeds() -> None:
    with TestClient(app) as client:
        token = login_demo(client)
        case_id = create_case(client, token, "空案件删除测试")

        delete = client.delete(f"/api/v1/cases/{case_id}", headers=auth_headers(token))
        assert delete.status_code == 204
        assert case_id not in list_ids(client, token, "all")


def test_delete_case_with_evidence_conflicts() -> None:
    with TestClient(app) as client:
        token = login_demo(client)
        case_id = create_case(client, token, "有证据案件删除测试")

        upload = client.post(
            f"/api/v1/cases/{case_id}/evidence",
            headers=auth_headers(token),
            files={"file": ("工资条.txt", "2026年10月工资 8500元".encode(), "text/plain")},
        )
        assert upload.status_code == 201

        delete = client.delete(f"/api/v1/cases/{case_id}", headers=auth_headers(token))
        assert delete.status_code == 409


def test_filter_by_dispute_type_and_search() -> None:
    with TestClient(app) as client:
        token = login_demo(client)
        case_id = create_case(client, token, "欠薪搜索关键词案件", dispute_type="wage")

        by_type = client.get(
            "/api/v1/cases?dispute_type=wage",
            headers=auth_headers(token),
        )
        assert by_type.status_code == 200
        assert all(item["dispute_type"] == "wage" for item in by_type.json())
        assert case_id in {item["id"] for item in by_type.json()}

        by_query = client.get(
            "/api/v1/cases?q=欠薪搜索关键词",
            headers=auth_headers(token),
        )
        assert by_query.status_code == 200
        assert case_id in {item["id"] for item in by_query.json()}
