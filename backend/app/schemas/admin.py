from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class LawyerSummary(BaseModel):
    id: int
    username: str
    display_name: str
    license_no: str
    specialties: str
    status: str


class CaseAssignmentRequest(BaseModel):
    lawyer_id: int


class PasswordResetRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


class AdminUserUpdate(BaseModel):
    is_active: bool | None = None
    role: Literal["user", "lawyer", "admin"] | None = None


class AdminUserSummary(BaseModel):
    id: int
    username: str
    role: Literal["user", "lawyer", "admin"]
    display_name: str
    phone: str
    is_active: bool
    real_name: str | None = None
    verification_status: Literal["unverified", "pending", "verified", "rejected"]
    id_number_masked: str | None = None
    created_at: datetime


class AdminUserPage(BaseModel):
    items: list[AdminUserSummary]
    total: int
    page: int
    page_size: int


class MaterialSummary(BaseModel):
    id: int
    case_id: int
    filename: str
    content_type: str
    file_size: int
    category: str
    screening_status: str
    extraction_status: str
    created_at: datetime


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: int | None
    action: str
    object_type: str
    object_id: int
    metadata_json: dict[str, Any]
    created_at: datetime


class RuleConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dispute_type: str
    name: str
    evidence_requirements: list[str]
    next_steps: list[str]
    source_note: str
    review_status: str
    version: int
    created_at: datetime
    updated_at: datetime


class RuleReviewUpdate(BaseModel):
    review_status: Literal["pending_review", "approved", "rejected"]
    source_note: str = Field(default="", max_length=2_000)


class LawyerStatusUpdate(BaseModel):
    status: Literal["pending", "active", "suspended"]


class VerificationStatusUpdate(BaseModel):
    verification_status: Literal["unverified", "pending", "verified", "rejected"]
