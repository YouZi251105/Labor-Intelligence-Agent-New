"""流式咨询接口和千问 token 解析测试。"""

import json
import re
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import ai
from app.services.ai import extract_qwen_stream_text


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in re.split(r"\r?\n\r?\n", text.strip()):
        if not block.strip():
            continue
        event_name = "message"
        data_lines: list[str] = []
        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line.removeprefix("event:").strip()
            elif line.startswith("data:"):
                data_lines.append(line.removeprefix("data:").strip())
        if data_lines:
            events.append((event_name, json.loads("\n".join(data_lines))))
    return events


def test_extract_qwen_stream_text() -> None:
    assert (
        extract_qwen_stream_text(
            'data: {"choices":[{"delta":{"content":"工资应当按月支付。"}}]}'
        )
        == "工资应当按月支付。"
    )
    assert extract_qwen_stream_text("data: [DONE]") is None
    assert extract_qwen_stream_text(": keep-alive") is None


@pytest.mark.asyncio
async def test_qwen_stream_tokens_are_forwarded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        ai,
        "get_settings",
        lambda: SimpleNamespace(
            qianwen_api_key="test-key",
            qianwen_model="qwen-test",
        ),
    )

    async def fake_stream(**_kwargs):
        yield "**重点**"
        yield "\n\n先整理工资流水。"

    monkeypatch.setattr(ai, "_stream_qwen_content", fake_stream)
    case = SimpleNamespace(facts="公司拖欠工资。")

    events = [
        event
        async for event in ai.generate_ai_reply_stream(
            case,
            "公司拖欠工资应该怎么办？",
            [],
        )
    ]

    assert "".join(
        event["text"] for event in events if event["type"] == "delta"
    ) == "**重点**\n\n先整理工资流水。"
    result = next(event["result"] for event in events if event["type"] == "complete")
    assert result.demo_mode is False
    assert result.reply == "**重点**\n\n先整理工资流水。"


def test_consultation_stream_emits_progress_deltas_and_done() -> None:
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "demo", "password": "Demo123!"},
        )
        token = login.json()["access_token"]
        created = client.post(
            "/api/v1/cases",
            headers=auth(token),
            json={
                "title": "流式咨询测试",
                "dispute_type": "labor_pay",
                "location": "上海市",
                "facts": "公司拖欠工资。",
            },
        )
        case_id = created.json()["id"]

        response = client.post(
            f"/api/v1/cases/{case_id}/consultations/stream",
            headers=auth(token),
            json={"message": "公司拖欠两个月工资，我应该先准备什么？"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        events = parse_sse(response.text)
        statuses = [
            payload["stage"]
            for event, payload in events
            if event == "status"
        ]
        assert statuses[:2] == ["thinking", "generating"]

        deltas = [
            payload["text"]
            for event, payload in events
            if event == "delta"
        ]
        assert deltas
        assert any("工资" in chunk or "材料" in chunk for chunk in deltas)

        done_events = [payload for event, payload in events if event == "done"]
        assert len(done_events) == 1, response.text[-1200:]
        done = done_events[0]
        assert done["assistant_message"]["role"] == "assistant"
        assert done["assistant_message"]["content"] == "".join(deltas)
        assert done["structured"]["references"] == []

        persisted = client.get(
            f"/api/v1/cases/{case_id}/messages",
            headers=auth(token),
        )
        assert persisted.status_code == 200
        messages = persisted.json()
        assert [item["role"] for item in messages] == ["user", "assistant"]
        assert messages[-1]["content"] == done["assistant_message"]["content"]


def test_streaming_consultation_hides_completed_review_action() -> None:
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "demo", "password": "Demo123!"},
        )
        token = login.json()["access_token"]
        created = client.post(
            "/api/v1/cases",
            headers=auth(token),
            json={
                "title": "流式追问动作去重",
                "dispute_type": "labor_pay",
                "location": "上海市",
                "facts": "工伤后公司不承认，我准备马上申请仲裁。",
            },
        )
        case_id = created.json()["id"]
        review = client.post(
            f"/api/v1/lawyer-service/cases/{case_id}/review",
            headers=auth(token),
        )

        response = client.post(
            f"/api/v1/cases/{case_id}/consultations/stream",
            headers=auth(token),
            json={"message": "我已经申请复核了，接下来还要准备什么？"},
        )

    assert review.status_code == 201
    assert response.status_code == 200
    events = parse_sse(response.text)
    done = next(payload for event, payload in events if event == "done")
    options = done["structured"]["follow_up_options"]
    assert "filing_review" not in {item["kind"] for item in options}
    assert any("复核" in item["label"] or "复核" in item["message"] for item in options)
