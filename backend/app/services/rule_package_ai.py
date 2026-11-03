from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.workflow_rules import WorkflowRulePackage
from app.services.rule_packages import load_default_workflow_package

QIANWEN_CHAT_URL = (
    "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
)


class RulePackageAIUnavailableError(RuntimeError):
    pass


class RulePackageAIError(RuntimeError):
    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        self.errors = errors or [message]
        super().__init__(message)


async def generate_rule_package_draft(
    instruction: str,
) -> WorkflowRulePackage:
    settings = get_settings()
    if not settings.qianwen_api_key:
        raise RulePackageAIUnavailableError("AI 服务尚未配置")

    base_content = load_default_workflow_package().model_dump(mode="json")
    system_prompt = (
        "你是劳动法律服务平台的流程配置助手。"
        "请以给定基线规则包为结构基础，根据用户要求修改并返回完整 JSON。"
        "必须保留 package_id 为 cn-labor-workflow，version 和 review_status 由系统覆盖。"
        "只返回 JSON 对象，不要 Markdown 代码块，不要解释。"
        "节点 ID、阶段 ID、路径 ID 和期限 ID 只能使用 ASCII 字母、数字、下划线和短横线。"
        "designer.blocks 必须与 nodes 一一对应，block_type 只能是 "
        "stage、decision、evidence_gate、lawyer_gate、end。"
        "不得创建任意表达式或未登记字段。所有节点必须从起点可达。"
        "用户看到的名称、说明、结果和下一步必须使用中文。"
        f"\n基线规则包：{json.dumps(base_content, ensure_ascii=False)}"
    )
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"请生成规则包草稿。用户要求：{instruction.strip()}",
        },
    ]

    async with httpx.AsyncClient(timeout=90, trust_env=False) as client:
        for attempt in range(2):
            try:
                response = await client.post(
                    QIANWEN_CHAT_URL,
                    headers={
                        "Authorization": f"Bearer {settings.qianwen_api_key}",
                    },
                    json={
                        "model": settings.qianwen_model,
                        "messages": messages,
                        "temperature": 0.2,
                        "max_tokens": 6_000,
                    },
                )
                response.raise_for_status()
                raw_content = response.json()["choices"][0]["message"]["content"]
                generated = _parse_json_object(raw_content)
                generated["package_id"] = base_content["package_id"]
                generated["version"] = _new_version()
                generated["review_status"] = "draft"
                generated["designer"] = _normalize_designer(generated)
                return WorkflowRulePackage.model_validate(generated)
            except ValidationError as error:
                validation_errors = [
                    f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
                    for item in error.errors()[:20]
                ]
                if attempt == 0:
                    messages.extend(
                        [
                            {"role": "assistant", "content": raw_content},
                            {
                                "role": "user",
                                "content": (
                                    "上一个 JSON 未通过结构校验，请修正后只返回完整 JSON。"
                                    f"校验错误：{json.dumps(validation_errors, ensure_ascii=False)}"
                                ),
                            },
                        ]
                    )
                    continue
                raise RulePackageAIError(
                    "AI 生成的规则包未通过结构校验",
                    validation_errors,
                ) from error
            except (
                httpx.HTTPError,
                KeyError,
                TypeError,
                ValueError,
                json.JSONDecodeError,
            ) as error:
                raise RulePackageAIError(
                    "AI 规则生成失败，请稍后重试或检查模型配置",
                    [str(error)],
                ) from error

    raise RulePackageAIError("AI 规则生成失败")


def _parse_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("模型响应中没有 JSON 对象")
    parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("模型响应必须是 JSON 对象")
    return parsed


def _new_version() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return f"ai-{timestamp}-{uuid4().hex[:6]}"


def _normalize_designer(content: dict[str, Any]) -> dict[str, Any]:
    nodes = content.get("nodes")
    if not isinstance(nodes, dict):
        return {"version": 1, "blocks": {}}
    raw_designer = content.get("designer")
    raw_blocks = raw_designer.get("blocks") if isinstance(raw_designer, dict) else []
    existing: dict[str, dict[str, Any]] = {}
    if isinstance(raw_blocks, dict):
        existing = {
            str(key): value
            for key, value in raw_blocks.items()
            if isinstance(value, dict)
        }
    elif isinstance(raw_blocks, list):
        existing = {
            str(item["id"]): item
            for item in raw_blocks
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }

    blocks: dict[str, dict[str, Any]] = {}
    for index, (node_id, node) in enumerate(nodes.items()):
        if not isinstance(node, dict):
            continue
        previous = existing.get(str(node_id), {})
        position = previous.get("position")
        if not isinstance(position, dict):
            position = {
                "x": 30 + (index % 2) * 360,
                "y": 40 + (index // 2) * 230,
            }
        blocks[str(node_id)] = {
            "id": str(node_id),
            "block_type": previous.get("block_type")
            or _infer_block_type(node),
            "position": {
                "x": float(position.get("x", 0)),
                "y": float(position.get("y", 0)),
            },
        }
    return {"version": 1, "blocks": blocks}


def _infer_block_type(node: dict[str, Any]) -> str:
    options = node.get("options")
    if not isinstance(options, list) or not options:
        return "end"
    requirements = [
        requirement.get("type")
        for option in options
        if isinstance(option, dict)
        for requirement in option.get("requirements", [])
        if isinstance(requirement, dict)
    ]
    if "evidence_ready" in requirements:
        return "evidence_gate"
    if "lawyer_assigned" in requirements:
        return "lawyer_gate"
    if len(options) > 1:
        return "decision"
    return "stage"
