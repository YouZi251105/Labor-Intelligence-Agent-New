from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class DocumentCreate(BaseModel):
    doc_type: Literal["arbitration", "complaint", "settlement"]


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    doc_type: str
    title: str
    content: str
    status: str
    version: int
    created_at: datetime
