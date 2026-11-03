from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

RequestStatus = Literal[
    "pending", "accepted", "rejected", "in_session", "completed", "cancelled"
]
RequestPriority = Literal["normal", "urgent"]
RequestSlot = Literal["morning", "afternoon", "evening"]
ReviewConclusion = Literal["ready_to_file", "need_more", "not_recommended"]

SLOT_LABELS: dict[str, str] = {
    "morning": "上午 09:00-12:00",
    "afternoon": "下午 14:00-18:00",
    "evening": "晚间 18:00-21:00",
}


class LawyerRequestCreate(BaseModel):
    case_id: int
    reason: str = Field(min_length=1, max_length=2_000)
    preferred_time: str = Field(default="", max_length=160)
    preferred_date: date | None = None
    preferred_slot: RequestSlot | None = None
    priority: RequestPriority = "normal"


class LawyerRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    user_id: int
    lawyer_id: int | None
    reason: str
    preferred_time: str
    preferred_date: date | None
    preferred_slot: str | None
    priority: str
    status: str
    reject_reason: str
    created_at: datetime
    updated_at: datetime
    accepted_at: datetime | None
    completed_at: datetime | None


class LawyerRequestAction(BaseModel):
    accept: bool
    reject_reason: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def reject_reason_required(self) -> "LawyerRequestAction":
        if not self.accept and not self.reject_reason.strip():
            raise ValueError("拒绝预约时必须填写理由")
        return self


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
