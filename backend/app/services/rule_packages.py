from functools import lru_cache
from pathlib import Path

from app.schemas.workflow_rules import WorkflowRulePackage

DEFAULT_WORKFLOW_PACKAGE_PATH = (
    Path(__file__).resolve().parents[1] / "content" / "workflow_rules.v1.json"
)


@lru_cache
def load_default_workflow_package() -> WorkflowRulePackage:
    return WorkflowRulePackage.model_validate_json(
        DEFAULT_WORKFLOW_PACKAGE_PATH.read_text(encoding="utf-8")
    )
