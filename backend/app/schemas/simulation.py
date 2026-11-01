from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SimulationRole = Literal["boss", "hr", "arbitrator", "judge", "lawyer"]


class SimulationCreate(BaseModel):
    role_type: SimulationRole
    scenario: str = Field(min_length=2, max_length=160)


class SimulationMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4_000)


class SimulationScore(BaseModel):
    clarity: int = Field(ge=0, le=10)
    evidence_awareness: int = Field(ge=0, le=10)
    legal_appropriateness: int = Field(ge=0, le=10)
    overall: int = Field(ge=0, le=10)
    suggestions: list[str]


class SimulationMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: Literal["user", "assistant"]
    content: str
    score: SimulationScore | None = None
    created_at: datetime


class SimulationSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    user_id: int
    role_type: SimulationRole
    scenario: str
    status: str
    created_at: datetime
    updated_at: datetime


class SimulationSessionDetail(SimulationSessionRead):
    messages: list[SimulationMessageRead]


class SimulationReply(BaseModel):
    session: SimulationSessionRead
    user_message: SimulationMessageRead
    assistant_message: SimulationMessageRead
    score: SimulationScore
