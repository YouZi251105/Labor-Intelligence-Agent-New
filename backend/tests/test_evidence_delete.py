"""证据删除接口的单元测试。"""
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


def create_case(client: TestClient, token: str, title: str) -> int:
    response = client.post(
        "/api/v1/cases",
        headers=auth_headers(token),
        json={
            "title": title,
            "dispute_type": "wage",
            "location": "上海市",
            "facts": "公司拖欠工资，双方签订过劳动合同。",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_delete_evidence_removes_record_and_file() -> None:
    with TestClient(app) as client:
        token = login_demo(client)
        case_id = create_case(client, token, "证据删除")

        upload = client.post(
            f"/api/v1/cases/{case_id}/evidence",
            headers=auth_headers(token),
            files={"file": ("工资条.txt", "2026年10月工资 8500元".encode(), "text/plain")},
        )
        assert upload.status_code == 201
        evidence_id = upload.json()["id"]

        delete = client.delete(
            f"/api/v1/cases/{case_id}/evidence/{evidence_id}",
            headers=auth_headers(token),
        )
        assert delete.status_code == 204

        listing = client.get(
            f"/api/v1/cases/{case_id}/evidence",
            headers=auth_headers(token),
        )
        assert evidence_id not in [item["id"] for item in listing.json()["items"]]

        download = client.get(
            f"/api/v1/cases/{case_id}/evidence/{evidence_id}/download",
            headers=auth_headers(token),
        )
        assert download.status_code == 404
