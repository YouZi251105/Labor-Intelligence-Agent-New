import json

import pytest
from pydantic import ValidationError

from app.schemas.workflow_rules import WorkflowRulePackage
from app.services.rule_packages import (
    DEFAULT_WORKFLOW_PACKAGE_PATH,
    load_default_workflow_package,
)


def test_default_package_is_versioned_and_pending_review() -> None:
    package = load_default_workflow_package()

    assert package.schema_version == 1
    assert package.package_id == "cn-labor-workflow"
    assert package.version
    assert package.review_status == "pending_review"
    assert package.start_node in package.nodes
    assert any(len(node.options) > 1 for node in package.nodes.values())


def test_package_rejects_option_targeting_unknown_node() -> None:
    raw = json.loads(DEFAULT_WORKFLOW_PACKAGE_PATH.read_text(encoding="utf-8"))
    raw["nodes"][raw["start_node"]]["options"][0]["target_node"] = "missing-node"

    with pytest.raises(ValidationError, match="unknown target node"):
        WorkflowRulePackage.model_validate(raw)


def test_package_rejects_invalid_workflow_identifier() -> None:
    raw = json.loads(DEFAULT_WORKFLOW_PACKAGE_PATH.read_text(encoding="utf-8"))
    raw["nodes"][raw["start_node"]]["options"][0]["id"] = "invalid path id"

    with pytest.raises(ValidationError, match="String should match pattern"):
        WorkflowRulePackage.model_validate(raw)
