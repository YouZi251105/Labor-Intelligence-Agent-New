from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RequestStatus = Literal[
    "pending", "accepted", "rejected", "in_session", "completed", "cancelled"
]
RequestPriority = Literal["normal", "urgent"]
ReviewConclusion = Literal["ready_to_file", "need_more", "not_recommended"]


class LawyerRequestCreate(BaseModel):
    case_id: int
    reason: str = Field(min_length=1, max_length=2_000)
    preferred_time: str = Field(default="", max_length=160)
    priority: RequestPriority = "normal"


class LawyerRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    user_id: int
    lawyer_id: int | None
    reason: str
    preferred_time: str
    priority: str
    status: str
    created_at: datetime
    updated_at: datetime
    accepted_at: datetime | None
    completed_at: datetime | None


class LawyerRequestAction(BaseModel):
    accept: bool


class ConsultationMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4_000)


class ConsultationMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    sender_role: str
    content: str
    created_at: datetime


class ConsultationSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: int | None
    case_id: int
    user_id: int
    lawyer_id: int
    status: str
    created_at: datetime
    closed_at: datetime | None


class CaseReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    lawyer_id: int | None
    status: str
    conclusion: str | None
    comment: str
    created_at: datetime
    reviewed_at: datetime | None


class CaseReviewSubmit(BaseModel):
    conclusion: ReviewConclusion
    comment: str = Field(default="", max_length=2_000)
