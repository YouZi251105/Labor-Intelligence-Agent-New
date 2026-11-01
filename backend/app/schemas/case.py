from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CaseCreate(BaseModel):
    title: str = Field(default="新的劳动纠纷咨询", min_length=2, max_length=160)
    dispute_type: str = Field(default="general", max_length=40)
    location: str = Field(default="", max_length=120)
    facts: str = Field(default="", max_length=10_000)


class CaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    assigned_lawyer_id: int | None
    title: str
    dispute_type: str
    legal_relationship: str
    stage: str
    status: str
    location: str
    facts: str
    summary: str
    classification: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=8_000)


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    metadata_json: dict[str, Any]
    created_at: datetime


class StructuredAIResult(BaseModel):
    intent: str
    dispute_label: str
    legal_relationship: str
    summary: str
    suggested_next_step: str
    required_information: list[str]
    evidence_gaps: list[str]
    risk_flags: list[str]
    citations: list[str]
    demo_mode: bool


class ConsultationResponse(BaseModel):
    case: CaseRead
    user_message: MessageRead
    assistant_message: MessageRead
    classification: dict[str, Any]
    structured: StructuredAIResult
    suggested_next_step: str
    demo_mode: bool
