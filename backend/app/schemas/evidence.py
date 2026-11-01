from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    filename: str
    content_type: str
    file_size: int
    sha256: str
    category: str
    screening_status: str
    assessment: dict[str, Any]
    created_at: datetime


class ContractReviewRequest(BaseModel):
    text: str = Field(min_length=10, max_length=50_000)


class ContractFinding(BaseModel):
    level: Literal["info", "medium", "high"]
    title: str
    detail: str


class ContractReviewResponse(BaseModel):
    risk_level: Literal["low", "medium", "high"]
    findings: list[ContractFinding]
    missing_items: list[str]
    disclaimer: str
