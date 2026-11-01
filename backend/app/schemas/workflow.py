from typing import Literal

from pydantic import BaseModel, Field

StageStatus = Literal["completed", "current", "available", "locked"]


class WorkflowStage(BaseModel):
    stage: str
    label: str
    status: StageStatus
    required_actions: list[str] = []


class WorkflowOption(BaseModel):
    target_stage: str
    label: str
    description: str
    enabled: bool
    blocked_reasons: list[str] = []


class WorkflowResponse(BaseModel):
    case_id: int
    current_stage: str
    stages: list[WorkflowStage]
    options: list[WorkflowOption]


class TransitionRequest(BaseModel):
    target_stage: str = Field(min_length=1, max_length=40)
    note: str = Field(default="", max_length=2_000)
