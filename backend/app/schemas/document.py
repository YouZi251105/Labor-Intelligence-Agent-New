from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    doc_type: Literal["arbitration", "complaint", "settlement"]


class DocumentEvidenceRead(BaseModel):
    evidence_id: int
    filename: str
    category: str
    sha256: str


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    doc_type: str
    title: str
    content: str
    status: str
    version: int
    evidence: list[DocumentEvidenceRead] = Field(default_factory=list)
    created_at: datetime


class DocumentRevisionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=10, max_length=100_000)
    status: Literal["draft"] = "draft"
