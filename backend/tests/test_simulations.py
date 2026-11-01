from fastapi.testclient import TestClient

from app.main import app


def auth_headers(token: str) -> dict[str, str]:
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
        headers=auth_headers(token),
        json={
            "title": title,
            "dispute_type": "wage",
            "facts": "公司拖欠两个月工资。",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_simulation_flow_returns_score_and_messages() -> None:
    with TestClient(app) as client:
        token = login(client, "demo", "Demo123!")
        case_id = create_case(client, token, "模拟工资沟通")
        created = client.post(
            f"/api/v1/cases/{case_id}/simulations",
            headers=auth_headers(token),
            json={
                "role_type": "boss",
                "scenario": "向老板确认拖欠工资的支付时间",
            },
        )
        assert created.status_code == 201
        session_id = created.json()["id"]

        replied = client.post(
            f"/api/v1/cases/{case_id}/simulations/{session_id}/messages",
            headers=auth_headers(token),
            json={
                "content": "请您确认9月和10月工资的支付时间，并书面确认欠薪金额。"
            },
        )
        detail = client.get(
            f"/api/v1/cases/{case_id}/simulations/{session_id}",
            headers=auth_headers(token),
        )

    assert replied.status_code == 200
    payload = replied.json()
    assert payload["score"]["overall"] >= 0
    assert payload["score"]["suggestions"]
    assert payload["assistant_message"]["role"] == "assistant"
    assert detail.status_code == 200
    assert len(detail.json()["messages"]) == 2


def test_simulation_is_scoped_to_case_owner() -> None:
    with TestClient(app) as client:
        owner_token = login(client, "demo", "Demo123!")
        case_id = create_case(client, owner_token, "模拟权限")
        session = client.post(
            f"/api/v1/cases/{case_id}/simulations",
            headers=auth_headers(owner_token),
            json={"role_type": "hr", "scenario": "沟通工资支付"},
        )
        session_id = session.json()["id"]

        registered = client.post(
            "/api/v1/auth/register",
            json={
                "username": "simulation-other",
                "password": "Simulation123!",
                "display_name": "其他用户",
            },
        )
        other_token = registered.json()["access_token"]
        forbidden = client.get(
            f"/api/v1/cases/{case_id}/simulations/{session_id}",
            headers=auth_headers(other_token),
        )

    assert forbidden.status_code == 404


def test_simulation_rejects_unknown_role() -> None:
    with TestClient(app) as client:
        token = login(client, "demo", "Demo123!")
        case_id = create_case(client, token, "模拟角色校验")
        response = client.post(
            f"/api/v1/cases/{case_id}/simulations",
            headers=auth_headers(token),
            json={"role_type": "stranger", "scenario": "测试"},
        )

    assert response.status_code == 422
