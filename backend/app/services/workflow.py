from typing import Any

from app.models.case import Case
from app.models.evidence import Evidence
from app.schemas.workflow import (
    StageStatus,
    WorkflowDeadline,
    WorkflowDecision,
    WorkflowOption,
    WorkflowResponse,
    WorkflowRulePackageInfo,
    WorkflowStage,
)
from app.schemas.workflow_rules import WorkflowOptionRule, WorkflowRulePackage
from app.services.evidence import assess_case_evidence
from app.services.rule_packages import load_default_workflow_package


def build_workflow(
    case: Case,
    evidence_items: list[Evidence],
    package: WorkflowRulePackage | None = None,
) -> WorkflowResponse:
    rule_package = package or load_default_workflow_package()
    stored_node = case.classification.get("workflow_node_id")
    current_node = (
        stored_node
        if isinstance(stored_node, str) and stored_node in rule_package.nodes
        else case.stage
        if case.stage in rule_package.nodes
        else rule_package.start_node
    )
    node = rule_package.nodes[current_node]
    current_stage = node.stage
    evidence_assessment = assess_case_evidence(case, evidence_items)
    options = [
        _build_option(option, case, evidence_assessment)
        for option in node.options
    ]
    decisions = _decision_path(case)
    available_targets = {
        option.target_stage for option in options if option.enabled
    }
    visited_stages = {
        rule_package.nodes[node_id].stage
        for decision in decisions
        for node_id in (decision.from_node, decision.to_node)
        if node_id in rule_package.nodes
    }
    visited_stages.add(current_stage)

    stages = [
        WorkflowStage(
            stage=stage.key,
            label=stage.label,
            status=_stage_status(
                stage.key,
                current_stage,
                visited_stages,
                available_targets,
            ),
            required_actions=_required_actions(
                stage.key,
                case,
                current_stage,
                evidence_assessment,
            ),
        )
        for stage in rule_package.stages
    ]
    return WorkflowResponse(
        case_id=case.id,
        current_node=current_node,
        current_stage=current_stage,
        decision_path=decisions,
        stages=stages,
        options=options,
        rule_package=WorkflowRulePackageInfo(
            package_id=rule_package.package_id,
            version=rule_package.version,
            jurisdiction=rule_package.jurisdiction,
            review_status=rule_package.review_status,
            disclaimer=rule_package.disclaimer,
        ),
    )


def _build_option(
    option: WorkflowOptionRule,
    case: Case,
    evidence_assessment: dict[str, Any],
) -> WorkflowOption:
    blocked_reasons: list[str] = []
    for requirement in option.requirements:
        if requirement.type == "evidence_ready":
            if evidence_assessment["status"] != "ready":
                missing_labels = [
                    str(item) for item in evidence_assessment["missing_labels"]
                ]
                if missing_labels:
                    blocked_reasons.append(
                        f"{requirement.message}缺少：{'、'.join(missing_labels)}"
                    )
                else:
                    blocked_reasons.append(requirement.message or "证据尚未准备完成")
        elif requirement.type == "lawyer_assigned" and case.assigned_lawyer_id is None:
            blocked_reasons.append(requirement.message or "尚未分配律师")

    return WorkflowOption(
        id=option.id,
        target_stage=option.target_stage,
        target_node=option.target_node,
        label=option.label,
        description=option.description,
        outcome=option.outcome,
        next_step=option.next_step,
        enabled=not blocked_reasons,
        blocked_reasons=blocked_reasons,
        deadlines=[
            WorkflowDeadline(
                id=deadline.id,
                title=deadline.title,
                description=deadline.description,
                basis=deadline.basis,
                start_event=deadline.start_event,
                review_status=deadline.review_status,
            )
            for deadline in option.deadlines
        ],
    )


def _decision_path(case: Case) -> list[WorkflowDecision]:
    raw_choices = case.classification.get("workflow_choices", [])
    if not isinstance(raw_choices, list):
        return []
    decisions: list[WorkflowDecision] = []
    for item in raw_choices:
        if not isinstance(item, dict):
            continue
        try:
            decisions.append(WorkflowDecision.model_validate(item))
        except ValueError:
            continue
    return decisions


def _stage_status(
    stage: str,
    current_node: str,
    visited_stages: set[str],
    available_targets: set[str],
) -> StageStatus:
    if stage == current_node:
        return "current"
    if stage in visited_stages:
        return "completed"
    if stage in available_targets:
        return "available"
    return "locked"


def _required_actions(
    stage: str,
    case: Case,
    current_stage: str,
    evidence_assessment: dict[str, Any],
) -> list[str]:
    if stage == "evidence" and current_stage == "evidence":
        return [
            str(item) for item in evidence_assessment["missing_labels"]
        ]
    if stage == "procedure" and current_stage == "procedure":
        return ["比较协商、监察、仲裁、诉讼和律师协助的适用条件"]
    if stage == "document" and current_stage == "document":
        return ["生成并核对文书主体、金额、请求事项和事实理由"]
    if stage == "lawyer_help" and current_stage == "lawyer_help":
        if case.assigned_lawyer_id is None:
            return ["等待管理员分配律师"]
        return ["等待律师复核并记录处理结果"]
    return []
