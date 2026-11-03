import asyncio
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.services.simulation import generate_simulation_reply


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
        profile = client.put(
            "/api/v1/users/me/profile",
            headers=auth_headers(other_token),
            json={
                "real_name": "其他用户",
                "phone": "13900000000",
                "id_number": "110101199001011234",
            },
        )
        assert profile.status_code == 200
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


class _FakeQwenResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "choices": [
                {
                    "message": {
                        "content": "【单位负责人模拟】请把欠薪月份和金额说清楚。"
                    }
                }
            ]
        }


class _FakeQwenClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args) -> None:
        return None

    async def post(self, *_args, **_kwargs) -> _FakeQwenResponse:
        return _FakeQwenResponse()


def test_simulation_uses_qwen_when_configured(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.simulation.get_settings",
        lambda: SimpleNamespace(
            qianwen_api_key="test-key",
            qianwen_model="qwen-plus",
        ),
    )

    reply = asyncio.run(
        generate_simulation_reply(
            "boss",
            "确认拖欠工资的支付时间",
            "请您确认9月和10月工资的支付时间。",
            1,
            client=_FakeQwenClient(),
        )
    )

    assert reply == "【单位负责人模拟】请把欠薪月份和金额说清楚。"


def test_simulation_falls_back_when_qwen_is_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.simulation.get_settings",
        lambda: SimpleNamespace(qianwen_api_key="", qianwen_model="qwen-plus"),
    )

    reply = asyncio.run(
        generate_simulation_reply(
            "boss",
            "确认拖欠工资的支付时间",
            "请您确认9月和10月工资的支付时间。",
            1,
        )
    )

    assert "【单位负责人模拟】" in reply
