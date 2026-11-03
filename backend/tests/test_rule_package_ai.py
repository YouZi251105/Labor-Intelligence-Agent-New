import json
from types import SimpleNamespace

import pytest

from app.services import rule_package_ai
from app.services.rule_packages import load_default_workflow_package


class FakeResponse:
    def __init__(self, content: str) -> None:
        self._content = content

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


class FakeClient:
    def __init__(self, content: str, **_: object) -> None:
        self.content = content

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def post(self, *_: object, **__: object) -> FakeResponse:
        return FakeResponse(self.content)


@pytest.mark.asyncio
async def test_ai_generation_parses_and_normalizes_rule_package(monkeypatch) -> None:
    content = load_default_workflow_package().model_dump(mode="json")
    content["version"] = "model-returned-version"
    content["review_status"] = "published"

    monkeypatch.setattr(
        rule_package_ai,
        "get_settings",
        lambda: SimpleNamespace(
            qianwen_api_key="test-key",
            qianwen_model="qwen-plus",
        ),
    )
    monkeypatch.setattr(
        rule_package_ai.httpx,
        "AsyncClient",
        lambda **kwargs: FakeClient(
            "```json\n" + json.dumps(content, ensure_ascii=False) + "\n```",
            **kwargs,
        ),
    )

    generated = await rule_package_ai.generate_rule_package_draft(
        "增加工伤咨询分支，并保留律师复核入口。"
    )

    assert generated.package_id == "cn-labor-workflow"
    assert generated.version.startswith("ai-")
    assert generated.review_status == "draft"
    assert generated.designer is not None
    assert len(generated.designer.blocks) == len(generated.nodes)


@pytest.mark.asyncio
async def test_ai_generation_reports_invalid_model_output(monkeypatch) -> None:
    monkeypatch.setattr(
        rule_package_ai,
        "get_settings",
        lambda: SimpleNamespace(
            qianwen_api_key="test-key",
            qianwen_model="qwen-plus",
        ),
    )
    monkeypatch.setattr(
        rule_package_ai.httpx,
        "AsyncClient",
        lambda **kwargs: FakeClient('{"not":"a rule package"}', **kwargs),
    )

    with pytest.raises(rule_package_ai.RulePackageAIError):
        await rule_package_ai.generate_rule_package_draft(
            "增加工伤咨询分支，并保留律师复核入口。"
        )
