from app.models.case import Case
from app.models.evidence import Evidence
from app.schemas.workflow import WorkflowOption, WorkflowResponse, WorkflowStage
from app.services.evidence import assess_case_evidence

STAGE_DEFINITIONS = [
    ("intake", "识别问题"),
    ("evidence", "整理证据"),
    ("procedure", "协商或仲裁"),
    ("document", "文书准备"),
    ("lawyer_help", "律师协助"),
    ("closed", "案件结束"),
]
NEXT_STAGE = {
    "intake": "evidence",
    "evidence": "procedure",
    "procedure": "document",
    "document": "lawyer_help",
    "lawyer_help": "closed",
}
STAGE_LABELS = dict(STAGE_DEFINITIONS)


def build_workflow(case: Case, evidence_items: list[Evidence]) -> WorkflowResponse:
    current_stage = case.stage if case.stage in STAGE_LABELS else "intake"
    current_index = next(
        index
        for index, (stage, _) in enumerate(STAGE_DEFINITIONS)
        if stage == current_stage
    )
    next_stage = NEXT_STAGE.get(current_stage)
    options: list[WorkflowOption] = []

    if next_stage:
        enabled = True
        blocked_reasons: list[str] = []
        if current_stage == "evidence":
            assessment = assess_case_evidence(case, evidence_items)
            enabled = assessment["status"] == "ready"
            blocked_reasons = assessment["missing_labels"]
        elif current_stage == "document" and case.assigned_lawyer_id is None:
            enabled = False
            blocked_reasons = ["尚未分配律师"]

        options.append(
            WorkflowOption(
                target_stage=next_stage,
                label=_option_label(current_stage, next_stage),
                description=_option_description(current_stage, next_stage),
                enabled=enabled,
                blocked_reasons=blocked_reasons,
            )
        )

    stages: list[WorkflowStage] = []
    for index, (stage, label) in enumerate(STAGE_DEFINITIONS):
        if index < current_index:
            status = "completed"
        elif index == current_index:
            status = "current"
        elif index == current_index + 1 and options and options[0].enabled:
            status = "available"
        else:
            status = "locked"
        stages.append(
            WorkflowStage(
                stage=stage,
                label=label,
                status=status,
                required_actions=_required_actions(case, stage, evidence_items),
            )
        )

    return WorkflowResponse(
        case_id=case.id,
        current_stage=current_stage,
        stages=stages,
        options=options,
    )


def _required_actions(
    case: Case,
    stage: str,
    evidence_items: list[Evidence],
) -> list[str]:
    if stage == "intake":
        return []
    if stage == "evidence":
        if case.stage != "evidence":
            return []
        assessment = assess_case_evidence(case, evidence_items)
        return assessment["missing_labels"]
    if stage == "procedure":
        return ["确认协商或仲裁路径"]
    if stage == "document":
        return ["生成并核对文书草稿"]
    if stage == "lawyer_help":
        return ["等待律师处理并记录结果"]
    return []


def _option_label(current_stage: str, next_stage: str) -> str:
    return {
        ("intake", "evidence"): "开始整理证据",
        ("evidence", "procedure"): "进入协商或仲裁",
        ("procedure", "document"): "准备法律文书",
        ("document", "lawyer_help"): "申请律师协助",
        ("lawyer_help", "closed"): "结束案件",
    }.get((current_stage, next_stage), f"进入{STAGE_LABELS[next_stage]}")


def _option_description(current_stage: str, next_stage: str) -> str:
    return {
        ("intake", "evidence"): "根据纠纷类型整理材料并检查缺口。",
        ("evidence", "procedure"): "材料满足当前规则后选择协商或仲裁路径。",
        ("procedure", "document"): "生成协商方案、仲裁申请或起诉状草稿。",
        ("document", "lawyer_help"): "需要专业判断时转人工律师。",
        ("lawyer_help", "closed"): "记录处理结果并结束当前案件。",
    }.get((current_stage, next_stage), STAGE_LABELS[next_stage])
