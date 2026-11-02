from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

RulePackageStatus = Literal[
    "draft",
    "pending_review",
    "approved",
    "rejected",
    "published",
    "retired",
]


class RulePackageSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    package_type: str
    package_id: str
    version: str
    status: RulePackageStatus
    checksum: str
    created_by_id: int | None
    reviewed_by_id: int | None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None


class RulePackageDetail(RulePackageSummary):
    content: dict[str, Any]


class RulePackageContentRequest(BaseModel):
    content: dict[str, Any]


class RulePackageValidationSummary(BaseModel):
    package_id: str
    version: str
    jurisdiction: str
    start_node: str
    stage_count: int
    node_count: int
    option_count: int
    block_count: int = 0
    block_types: dict[str, int] = Field(default_factory=dict)
    review_status: str


class RulePackageValidationResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    summary: RulePackageValidationSummary | None = None


class RulePackageReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str = Field(default="", max_length=2_000)
