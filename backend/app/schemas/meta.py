"""字典接口的数据结构。"""

from pydantic import BaseModel


class DisputeTypeDict(BaseModel):
    value: str
    label: str
    keywords: list[str]


class StageDict(BaseModel):
    value: str
    label: str
    description: str = ""


class EvidenceCategoryDict(BaseModel):
    value: str
    label: str
    keywords: list[str]


class DictionaryResponse(BaseModel):
    disputes: list[DisputeTypeDict]
    stages: list[StageDict]
    evidence_categories: list[EvidenceCategoryDict]
