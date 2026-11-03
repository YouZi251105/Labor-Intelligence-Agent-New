"""字典管理 Schema：字典包内容结构与校验。"""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

ALLOWED_GROUPS = {"labor", "service"}
VALUE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,38}$")
FALLBACK_DISPUTE_VALUE = "labor_other"


class DictionaryDisputeItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str = Field(min_length=2, max_length=40)
    label: str = Field(min_length=2, max_length=80)
    group: str = "labor"
    keywords: list[str] = Field(default_factory=list)
    required_categories: list[str] = Field(default_factory=list)
    core_categories: list[str] = Field(default_factory=list)
    claim_text: str = ""


class DictionaryStageItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str = Field(min_length=2, max_length=40)
    label: str = Field(min_length=2, max_length=80)
    description: str = ""


class DictionaryCategoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str = Field(min_length=2, max_length=40)
    label: str = Field(min_length=2, max_length=80)
    keywords: list[str] = Field(default_factory=list)


class DictionaryPackageContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    disputes: list[DictionaryDisputeItem] = Field(min_length=1)
    stages: list[DictionaryStageItem] = Field(min_length=1)
    evidence_categories: list[DictionaryCategoryItem] = Field(min_length=1)
    migrations: dict[str, str] = Field(default_factory=dict)


class DictionaryPackageContentRequest(BaseModel):
    content: DictionaryPackageContent


class DictionaryVersionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: int
    status: str
    checksum: str
    created_by_id: int | None = None
    created_at: datetime
    published_at: datetime | None = None


class DictionaryVersionDetail(DictionaryVersionSummary):
    content: DictionaryPackageContent


class DictionaryActiveResponse(BaseModel):
    """当前生效字典：已发布包或内置默认，供管理端编辑器初始化。"""

    source: str  # published | default
    version: int | None = None
    content: DictionaryPackageContent


def validate_dictionary_package(content: DictionaryPackageContent) -> list[str]:
    """跨字段业务校验，返回错误列表（空列表表示通过）。"""
    errors: list[str] = []

    seen_values: set[str] = set()
    for item in content.disputes:
        if not VALUE_PATTERN.match(item.value):
            errors.append(f"纠纷标识 {item.value} 只能使用小写字母、数字和下划线")
        if item.value in seen_values:
            errors.append(f"纠纷标识 {item.value} 重复")
        seen_values.add(item.value)
        if item.group not in ALLOWED_GROUPS:
            errors.append(
                f"纠纷 {item.value} 的分组必须是 labor 或 service"
            )
        if not set(item.core_categories) <= set(item.required_categories):
            errors.append(f"纠纷 {item.value} 的核心材料必须包含在必需材料中")

    category_values = {item.value for item in content.evidence_categories}
    if len(category_values) != len(content.evidence_categories):
        errors.append("证据类别标识存在重复")
    for item in content.disputes:
        for category in item.required_categories:
            if category not in category_values:
                errors.append(
                    f"纠纷 {item.value} 的必需材料 {category} 不在证据类别中"
                )

    if FALLBACK_DISPUTE_VALUE not in seen_values:
        errors.append("字典必须保留 labor_other 作为兜底分类")

    stage_values = [item.value for item in content.stages]
    if len(set(stage_values)) != len(stage_values):
        errors.append("案件阶段标识存在重复")

    for old, new in content.migrations.items():
        if new not in seen_values:
            errors.append(f"迁移映射 {old} 的目标 {new} 不是有效的纠纷标识")

    return errors
