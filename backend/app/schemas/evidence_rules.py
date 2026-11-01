"""证据四性评估接口的 Pydantic Schema（开发 B 定义）。"""

from typing import Literal

from pydantic import BaseModel


class AssessmentFinding(BaseModel):
    level: str
    message: str


class AssessmentDimension(BaseModel):
    status: str
    findings: list[AssessmentFinding]


class CompletenessAssessment(BaseModel):
    status: Literal["ready", "needs_more"]
    required_categories: list[str]
    present_categories: list[str]
    missing_categories: list[str]
    missing_labels: list[str]


class EvidenceAssessmentResponse(BaseModel):
    case_id: int
    dispute_type: str
    legality: AssessmentDimension
    relevance: AssessmentDimension
    sufficiency: AssessmentDimension
    completeness: CompletenessAssessment
    disclaimer: str
