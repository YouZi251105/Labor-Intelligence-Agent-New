from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UserProfileUpdate(BaseModel):
    real_name: str = Field(min_length=2, max_length=80)
    phone: str = Field(pattern=r"^1\d{10}$")
    id_number: str = Field(pattern=r"^(\d{15}|\d{17}[\dXx])$")


class UserProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    real_name: str
    phone: str
    id_number_masked: str
    verification_status: Literal["unverified", "pending", "verified", "rejected"]
    created_at: datetime
    updated_at: datetime
