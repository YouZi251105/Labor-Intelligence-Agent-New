from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

StageStatus = Literal["completed", "current", "available", "locked"]


class WorkflowStage(BaseModel):
    stage: str
    label: str
    status: StageStatus
    required_actions: list[str] = Field(default_factory=list)


class WorkflowDeadline(BaseModel):
    id: str
    title: str
    description: str
    basis: str
    start_event: str
    review_status: str
    due_at: datetime | None = None


class WorkflowOption(BaseModel):
    id: str
    target_stage: str
    target_node: str
    label: str
    description: str
    outcome: str
    next_step: str
    enabled: bool
    blocked_reasons: list[str] = Field(default_factory=list)
    deadlines: list[WorkflowDeadline] = Field(default_factory=list)


class WorkflowDecision(BaseModel):
    option_id: str
    label: str
    from_node: str
    to_node: str
    rule_package_version: str
    selected_at: datetime
    note: str = ""


class WorkflowRulePackageInfo(BaseModel):
    package_id: str
    version: str
    jurisdiction: str
    review_status: str
    disclaimer: str


class WorkflowResponse(BaseModel):
    case_id: int
    current_node: str
    current_stage: str
    decision_path: list[WorkflowDecision] = Field(default_factory=list)
    stages: list[WorkflowStage]
    options: list[WorkflowOption]
    rule_package: WorkflowRulePackageInfo


class TransitionRequest(BaseModel):
    target_stage: str | None = Field(default=None, min_length=1, max_length=40)
    option_id: str | None = Field(default=None, min_length=1, max_length=80)
    note: str = Field(default="", max_length=2_000)

    @model_validator(mode="after")
    def require_target(self) -> "TransitionRequest":
        if self.target_stage is None and self.option_id is None:
            raise ValueError("target_stage or option_id is required")
        return self
