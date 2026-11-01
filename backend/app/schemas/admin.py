from typing import Literal

from pydantic import BaseModel, Field


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
