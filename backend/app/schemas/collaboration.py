from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ServiceType = Literal["consultation", "evidence", "document", "hearing", "other"]
ServiceStatus = Literal["pending", "in_progress", "completed"]
RevenueStatus = Literal["pending", "confirmed", "paid"]


class LawyerOpinionCreate(BaseModel):
    content: str = Field(min_length=10, max_length=20_000)


class LawyerOpinionRead(BaseModel):
    id: int
    case_id: int
    lawyer_id: int
    content: str
    status: str
    created_at: datetime


class ServiceRecordCreate(BaseModel):
    case_id: int
    service_type: ServiceType
    summary: str = Field(min_length=2, max_length=4_000)
    duration_minutes: int = Field(ge=0, le=24 * 60)


class ServiceRecordRead(BaseModel):
    id: int
    case_id: int
    lawyer_id: int
    service_type: str
    summary: str
    duration_minutes: int
    status: str
    occurred_at: datetime
    created_at: datetime


class ServiceStatusUpdate(BaseModel):
    status: ServiceStatus


class RevenueLedgerCreate(BaseModel):
    case_id: int | None = None
    service_record_id: int | None = None
    amount_cents: int = Field(ge=0, le=100_000_000)
    entry_type: str = Field(min_length=2, max_length=30)
    note: str = Field(default="", max_length=1_000)


class RevenueLedgerRead(BaseModel):
    id: int
    lawyer_id: int
    case_id: int | None
    service_record_id: int | None
    amount_cents: int
    entry_type: str
    status: str
    note: str
    created_at: datetime


class RevenueStatusUpdate(BaseModel):
    status: RevenueStatus
