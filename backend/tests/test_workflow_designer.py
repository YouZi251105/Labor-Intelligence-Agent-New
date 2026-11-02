import pytest
from pydantic import ValidationError

from app.models.case import Case
from app.schemas.workflow_rules import WorkflowRulePackage
from app.services.rule_packages import load_default_workflow_package
from app.services.workflow import build_workflow


def designer_content() -> dict:
    content = load_default_workflow_package().model_dump(mode="json")
    content["designer"] = {
        "version": 1,
        "blocks": [
            {
                "id": "intake",
                "block_type": "decision",
                "position": {"x": 40, "y": 40},
            },
            {
                "id": "evidence",
                "block_type": "evidence_gate",
                "position": {"x": 360, "y": 40},
            },
            {
                "id": "procedure",
                "block_type": "decision",
                "position": {"x": 680, "y": 40},
            },
            {
                "id": "document",
                "block_type": "lawyer_gate",
                "position": {"x": 1000, "y": 40},
            },
            {
                "id": "lawyer_help",
                "block_type": "stage",
                "position": {"x": 1320, "y": 40},
            },
            {
                "id": "closed",
                "block_type": "end",
                "position": {"x": 1640, "y": 40},
            },
        ],
    }
    return content


def test_designer_package_accepts_constrained_blocks() -> None:
    package = WorkflowRulePackage.model_validate(designer_content())

    assert package.designer is not None
    assert package.designer.blocks["evidence"].block_type == "evidence_gate"


def test_evidence_gate_requires_evidence_condition() -> None:
    content = designer_content()
    content["nodes"]["evidence"]["options"][0]["requirements"] = [{"type": "always"}]

    with pytest.raises(ValidationError, match="evidence_gate"):
        WorkflowRulePackage.model_validate(content)


def test_designer_rejects_unreachable_block() -> None:
    content = designer_content()
    content["nodes"]["orphan"] = {"stage": "intake", "options": []}
    content["designer"]["blocks"].append(
        {
            "id": "orphan",
            "block_type": "end",
            "position": {"x": 80, "y": 320},
        }
    )

    with pytest.raises(ValidationError, match="unreachable"):
        WorkflowRulePackage.model_validate(content)


def test_runtime_uses_workflow_node_id_independent_of_stage() -> None:
    content = designer_content()
    content["start_node"] = "start-choice"
    content["nodes"]["start-choice"] = content["nodes"].pop("intake")
    for block in content["designer"]["blocks"]:
        if block["id"] == "intake":
            block["id"] = "start-choice"
    package = WorkflowRulePackage.model_validate(content)
    case = Case(
        id=1,
        owner_id=1,
        title="积木运行测试",
        dispute_type="wage",
        stage="intake",
        classification={"workflow_node_id": "start-choice"},
    )

    workflow = build_workflow(case, [], package)

    assert workflow.current_node == "start-choice"
    assert workflow.current_stage == "intake"
    assert workflow.options[0].target_node == "evidence"
