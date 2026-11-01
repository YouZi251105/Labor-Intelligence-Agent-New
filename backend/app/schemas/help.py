from datetime import datetime

from pydantic import BaseModel, ConfigDict


class HelpResourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resource_type: str
    name: str
    region: str
    address: str
    website: str
    phone: str
    description: str
    status: str
    created_at: datetime


class SiteLawyerRead(BaseModel):
    id: int
    display_name: str
    specialties: str
    bio: str
    status: str
