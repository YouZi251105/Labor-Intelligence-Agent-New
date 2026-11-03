"""独立证据规则模块（开发 B 负责）。

接收结构化输入（纠纷类型 + 证据条目列表），返回可解释的"四性"判断结果：

- legality     合法性：形式异常与隔离状态复核。
- relevance    关联性：证据类别是否与案件纠纷类型相关。
- sufficiency  充分性：核心证据类别是否具备。
- completeness 完整性：所需证据类别覆盖与缺口。

设计约束：

- 与上传、存储、权限和数据库解耦，只接收结构化输入、返回可解释结果。
- 不直接改变案件状态，不修改 routes/evidence.py、services/evidence.py、
  证据模型或数据库迁移。
- 结果只用于材料整理提示，不下真伪鉴定结论。

规则样例为本地演示规则，正式法律依据由法律内容负责人复核后补充。
"""

from typing import Any

from app.services.dictionary import CATEGORY_LABELS

# 纠纷类型 -> 需要覆盖的证据类别（完整性，与演示规则一致）
REQUIRED_CATEGORIES: dict[str, list[str]] = {
    "labor_confirmation": ["contract", "payroll", "chat"],
    "labor_contract": ["contract", "chat", "attendance"],
    "labor_termination": ["contract", "chat", "payroll"],
    "labor_benefits": ["social_insurance", "payroll", "contract"],
    "labor_pay": ["payroll", "chat", "contract"],
    "labor_other": ["contract", "chat", "payroll"],
    "service_pay": ["settlement", "chat", "payroll"],
    "service_quality": ["settlement", "chat"],
    "service_injury": ["medical", "chat"],
    "service_breach": ["contract", "chat"],
}

# 纠纷类型 -> 核心证据类别（充分性，缺失时提示优先补充）
CORE_CATEGORIES: dict[str, list[str]] = {
    "labor_confirmation": ["payroll", "chat"],
    "labor_contract": ["contract", "chat"],
    "labor_termination": ["contract", "chat"],
    "labor_benefits": ["social_insurance", "payroll"],
    "labor_pay": ["payroll", "chat"],
    "labor_other": ["contract", "chat"],
    "service_pay": ["settlement", "chat"],
    "service_quality": ["settlement", "chat"],
    "service_injury": ["medical", "chat"],
    "service_breach": ["contract", "chat"],
}

# 旧纠纷枚举 -> 新纠纷枚举，保证历史案件继续参与证据评估。
LEGACY_DISPUTE_TYPES: dict[str, str] = {
    "general": "labor_other",
    "wage": "labor_pay",
    "overtime": "labor_pay",
    "injury": "labor_pay",
    "insurance": "labor_benefits",
    "contract": "labor_contract",
    "termination": "labor_termination",
    "service_pay": "service_pay",
}

# 允许的文件 MIME 前缀（形式合法性，与上传校验边界一致）
ALLOWED_CONTENT_TYPES = (
    "image/",
    "application/pdf",
    "text/",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
)

MAX_FILE_SIZE = 20 * 1024 * 1024

DISCLAIMER = "规则评估仅用于材料整理提示，不构成证据合法性或证明力结论。"


def refresh_runtime_rules() -> None:
    """从字典运行时源重建证据规则映射（字典包发布后由字典服务调用）。"""
    from app.services.dictionary import DEFAULT_DISPUTE_RULES, get_runtime_rules

    for value in DEFAULT_DISPUTE_RULES:
        required, core = get_runtime_rules(value)
        REQUIRED_CATEGORIES[value] = required
        CORE_CATEGORIES[value] = core


def assess_evidence_rules(
    dispute_type: str,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    """评估证据四性，返回可解释的判断结果。

    参数 ``items`` 中每一项至少包含 ``category`` 和 ``screening_status``，
    可选 ``filename``、``content_type``、``file_size``。

    返回值不直接修改案件状态，仅提供结构化、可解释的提示。
    """
    from app.services.dictionary import get_runtime_migrations, get_runtime_rules

    normalized = get_runtime_migrations().get(dispute_type, dispute_type)
    required, core = get_runtime_rules(normalized)
    dispute_type = normalized

    present = sorted({item.get("category", "other") for item in items})
    missing = [category for category in required if category not in present]
    missing_core = [category for category in core if category not in present]

    legality = _assess_legality(items)
    relevance = _assess_relevance(dispute_type, required, items)
    sufficiency = _assess_sufficiency(core, missing_core)
    completeness = _assess_completeness(required, present, missing)

    return {
        "legality": legality,
        "relevance": relevance,
        "sufficiency": sufficiency,
        "completeness": completeness,
        "disclaimer": DISCLAIMER,
    }


def _assess_legality(items: list[dict[str, Any]]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    for item in items:
        name = item.get("filename") or item.get("category") or "材料"
        if item.get("screening_status") == "quarantined":
            findings.append(
                {"level": "issue", "message": f"{name} 已被隔离，需人工复核。"}
            )
            continue

        content_type = item.get("content_type", "")
        if content_type and not content_type.startswith(ALLOWED_CONTENT_TYPES):
            findings.append(
                {"level": "issue", "message": f"{name} 文件形式异常，需人工确认。"}
            )

        file_size = item.get("file_size")
        if isinstance(file_size, int) and file_size > MAX_FILE_SIZE:
            findings.append(
                {"level": "issue", "message": f"{name} 超过 20MB 限制。"}
            )

    status = "issue" if any(f["level"] == "issue" for f in findings) else "ok"
    return {"status": status, "findings": findings}


def _assess_relevance(
    dispute_type: str,
    required: list[str],
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    for item in items:
        category = item.get("category", "other")
        if category == "other":
            findings.append(
                {
                    "level": "warning",
                    "message": "存在未识别类别的材料，关联性需要人工确认。",
                }
            )
        elif category not in required:
            findings.append(
                {
                    "level": "warning",
                    "message": (
                        f"{CATEGORY_LABELS.get(category, category)} 与"
                        f"“{dispute_type}”案件的关联性需要人工确认。"
                    ),
                }
            )

    status = "warning" if findings else "ok"
    return {"status": status, "findings": findings}


def _assess_sufficiency(
    core: list[str],
    missing_core: list[str],
) -> dict[str, Any]:
    if not missing_core:
        return {"status": "ok", "findings": []}

    labels = [CATEGORY_LABELS.get(item, item) for item in missing_core]
    findings = [
        {"level": "issue", "message": f"缺少核心证据：{'、'.join(labels)}。"}
    ]
    return {"status": "issue", "findings": findings}


def _assess_completeness(
    required: list[str],
    present: list[str],
    missing: list[str],
) -> dict[str, Any]:
    return {
        "status": "ready" if not missing else "needs_more",
        "required_categories": required,
        "present_categories": present,
        "missing_categories": missing,
        "missing_labels": [CATEGORY_LABELS.get(item, item) for item in missing],
    }
