import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule_package import RulePackage
from app.schemas.workflow_rules import WorkflowRulePackage

DEFAULT_WORKFLOW_PACKAGE_PATH = (
    Path(__file__).resolve().parents[1] / "content" / "workflow_rules.v1.json"
)


@lru_cache
def load_default_workflow_package() -> WorkflowRulePackage:
    return WorkflowRulePackage.model_validate_json(
        DEFAULT_WORKFLOW_PACKAGE_PATH.read_text(encoding="utf-8")
    )


def rule_package_checksum(content: dict[str, Any]) -> str:
    serialized = json.dumps(
        content,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode()).hexdigest()


def validate_workflow_package(
    content: dict[str, Any],
) -> tuple[WorkflowRulePackage | None, list[str]]:
    try:
        return WorkflowRulePackage.model_validate(content), []
    except ValidationError as error:
        messages = []
        for item in error.errors():
            location = ".".join(str(value) for value in item["loc"])
            messages.append(f"{location}: {item['msg']}")
        return None, messages


async def load_published_workflow_package(
    session: AsyncSession,
) -> WorkflowRulePackage | None:
    package = await session.scalar(
        select(RulePackage)
        .where(
            RulePackage.package_type == "workflow",
            RulePackage.package_id == "cn-labor-workflow",
            RulePackage.status == "published",
        )
        .order_by(RulePackage.published_at.desc(), RulePackage.id.desc())
    )
    if package is None:
        return None
    validated, _ = validate_workflow_package(package.content)
    return validated
