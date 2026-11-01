from datetime import datetime

from pydantic import BaseModel


class TopicSummary(BaseModel):
    dispute_type: str
    label: str
    count: int


class TopicsResponse(BaseModel):
    topics: list[TopicSummary]
    total: int


class HistoryCaseSummary(BaseModel):
    case_id: int
    title: str
    dispute_type: str
    stage: str
    summary: str
    updated_at: datetime


class HistoryResponse(BaseModel):
    cases: list[HistoryCaseSummary]
