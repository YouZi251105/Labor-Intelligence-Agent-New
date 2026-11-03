"""业务字典的单一数据源。

集中定义纠纷类型、案件阶段、证据类别及其识别关键词和中文标签，
供字典接口、AI 分类和证据规则共同引用，避免前后端多处硬编码。

法律内容由人工复核人员校验；此模块只提供数据结构与展示映射，
不自行确认法律内容正确性。
"""

from typing import Any

from sqlalchemy import select

# 纠纷分类采用两级法定口径：劳动争议与劳务纠纷。
# 分类名称来源由人工复核人员提供；此模块只负责数据结构与展示映射，
# 不自行确认法律内容正确性。
DISPUTE_TYPES: list[dict[str, Any]] = [
    {
        "value": "labor_confirmation",
        "label": "确认劳动关系争议",
        "group": "labor",
        "keywords": ["确认劳动关系", "事实劳动关系", "劳动关系认定", "算不算员工"],
    },
    {
        "value": "labor_contract",
        "label": "劳动合同订立、履行、变更、解除、终止争议",
        "group": "labor",
        "keywords": ["劳动合同", "合同", "续签", "试用期", "变更岗位", "双倍工资", "终止"],
    },
    {
        "value": "labor_termination",
        "label": "除名、辞退、辞职、自动离职争议",
        "group": "labor",
        "keywords": ["辞退", "开除", "解雇", "除名", "辞职", "自动离职", "裁员", "劝退"],
    },
    {
        "value": "labor_benefits",
        "label": "工作时间、休息休假、社会保险、福利、培训、劳动保护争议",
        "group": "labor",
        "keywords": [
            "工时",
            "休假",
            "年假",
            "社保",
            "社会保险",
            "公积金",
            "福利",
            "培训",
            "劳动保护",
        ],
    },
    {
        "value": "labor_pay",
        "label": "劳动报酬、加班费、工伤医疗费、经济补偿、赔偿金争议",
        "group": "labor",
        "keywords": [
            "工资",
            "欠薪",
            "拖欠",
            "讨薪",
            "加班",
            "加班费",
            "工伤",
            "医疗费",
            "经济补偿",
            "赔偿金",
            "伤残",
        ],
    },
    {"value": "labor_other", "label": "其他法定劳动争议", "group": "labor", "keywords": []},
    {
        "value": "service_pay",
        "label": "劳务费拖欠纠纷",
        "group": "service",
        "keywords": ["劳务费", "劳务报酬", "包工头", "结算", "工钱"],
    },
    {
        "value": "service_quality",
        "label": "劳务成果、质量纠纷",
        "group": "service",
        "keywords": ["劳务成果", "质量", "验收", "返工"],
    },
    {
        "value": "service_injury",
        "label": "提供劳务致人、自身损害赔偿纠纷",
        "group": "service",
        "keywords": ["劳务损害", "人身损害", "提供劳务受伤", "受伤赔偿"],
    },
    {
        "value": "service_breach",
        "label": "劳务合同解除、违约责任、违约金纠纷",
        "group": "service",
        "keywords": ["劳务合同", "违约", "违约金", "解除劳务"],
    },
]

# 旧枚举值 -> 新枚举值，用于数据库迁移与历史数据兼容。
DISPUTE_TYPE_MIGRATIONS: dict[str, str] = {
    "general": "labor_other",
    "wage": "labor_pay",
    "overtime": "labor_pay",
    "injury": "labor_pay",
    "insurance": "labor_benefits",
    "contract": "labor_contract",
    "termination": "labor_termination",
    "service_pay": "service_pay",
}

# 与规则包 workflow_rules.v1.json 中的 stages 保持一致。
STAGES: list[dict[str, Any]] = [
    {"value": "intake", "label": "识别问题", "description": "确认纠纷类型、劳动关系和当前诉求"},
    {"value": "evidence", "label": "整理证据", "description": "核对现有材料、证据缺口和形式风险"},
    {
        "value": "procedure",
        "label": "选择办理路径",
        "description": "比较协商、监察、仲裁或律师协助等路径",
    },
    {
        "value": "document",
        "label": "准备文书",
        "description": "生成并核对和解协议、仲裁申请或起诉材料",
    },
    {
        "value": "lawyer_help",
        "label": "律师协助",
        "description": "由平台律师复核材料、路径和文书",
    },
    {"value": "closed", "label": "结束处理", "description": "记录处理结果并结束本次案件流程"},
]

EVIDENCE_CATEGORIES: list[dict[str, Any]] = [
    {"value": "contract", "label": "合同或协议", "keywords": ["合同", "协议", "contract"]},
    {"value": "chat", "label": "聊天记录", "keywords": ["聊天", "微信", "chat"]},
    {
        "value": "payroll",
        "label": "工资或转账记录",
        "keywords": ["工资", "流水", "转账", "payroll"],
    },
    {
        "value": "attendance",
        "label": "考勤或排班记录",
        "keywords": ["考勤", "排班", "attendance"],
    },
    {
        "value": "medical",
        "label": "就医或伤情材料",
        "keywords": ["医院", "病历", "医疗", "medical"],
    },
    {
        "value": "social_insurance",
        "label": "社保记录",
        "keywords": ["社保", "公积金", "insurance"],
    },
    {"value": "settlement", "label": "结算单", "keywords": ["结算", "工程款", "settlement"]},
    {"value": "other", "label": "其他材料", "keywords": []},
]


# ---------------------------------------------------------------------------
# 运行时字典包：管理端可发布新版本，业务服务（AI 分类、证据规则、文书）
# 从这里读取行为数据；无包时回落内置默认。
# ---------------------------------------------------------------------------

# 每个纠纷类目的证据材料要求（必需 / 核心），可作为默认来源被包内容覆盖。
DEFAULT_DISPUTE_RULES: dict[str, dict[str, list[str]]] = {
    "labor_confirmation": {
        "required": ["contract", "payroll", "chat"],
        "core": ["payroll", "chat"],
    },
    "labor_contract": {
        "required": ["contract", "chat", "attendance"],
        "core": ["contract", "chat"],
    },
    "labor_termination": {
        "required": ["contract", "chat", "payroll"],
        "core": ["contract", "chat"],
    },
    "labor_benefits": {
        "required": ["social_insurance", "payroll", "contract"],
        "core": ["social_insurance", "payroll"],
    },
    "labor_pay": {"required": ["payroll", "chat", "contract"], "core": ["payroll", "chat"]},
    "labor_other": {"required": ["contract", "chat", "payroll"], "core": ["contract", "chat"]},
    "service_pay": {"required": ["settlement", "chat", "payroll"], "core": ["settlement", "chat"]},
    "service_quality": {"required": ["settlement", "chat"], "core": ["settlement", "chat"]},
    "service_injury": {"required": ["medical", "chat"], "core": ["medical", "chat"]},
    "service_breach": {"required": ["contract", "chat"], "core": ["contract", "chat"]},
}

# 每个纠纷类目在文书中的请求事项表述。
DEFAULT_DISPUTE_CLAIMS: dict[str, str] = {
    "labor_confirmation": "请求依法确认申请人与被申请人之间存在劳动关系。",
    "labor_contract": "请求裁决被申请人支付未签订书面劳动合同期间的二倍工资差额。",
    "labor_termination": "请求裁决被申请人支付违法解除劳动合同赔偿金。",
    "labor_benefits": "请求依法处理工作时间、休息休假、社会保险及劳动保护相关事项。",
    "labor_pay": "请求裁决被申请人支付拖欠的劳动报酬、加班费或经济补偿。",
    "labor_other": "请求依法处理双方劳动纠纷。",
    "service_pay": "请求判令被告支付拖欠的劳务报酬。",
    "service_quality": "请求依法处理劳务成果与质量相关争议。",
    "service_injury": "请求判令被告承担提供劳务受害的赔偿责任。",
    "service_breach": "请求判令被告承担劳务合同违约责任。",
}

DISPUTE_LABELS: dict[str, str] = {item["value"]: item["label"] for item in DISPUTE_TYPES}
DISPUTE_KEYWORDS: dict[str, list[str]] = {
    item["value"]: list(item["keywords"]) for item in DISPUTE_TYPES
}
CATEGORY_LABELS: dict[str, str] = {
    item["value"]: item["label"] for item in EVIDENCE_CATEGORIES
}

_RUNTIME_RULES: dict[str, dict[str, list[str]]] = {
    value: {"required": list(rule["required"]), "core": list(rule["core"])}
    for value, rule in DEFAULT_DISPUTE_RULES.items()
}
_RUNTIME_CLAIMS: dict[str, str] = dict(DEFAULT_DISPUTE_CLAIMS)
_RUNTIME_MIGRATIONS: dict[str, str] = dict(DISPUTE_TYPE_MIGRATIONS)

_CACHE_TTL_SECONDS = 60.0
_cache: tuple[float, dict[str, Any]] | None = None


def get_runtime_rules(dispute_type: str) -> tuple[list[str], list[str]]:
    """返回纠纷类目的 (必需材料, 核心材料)，未知类目回落默认。"""
    rule = _RUNTIME_RULES.get(dispute_type) or DEFAULT_DISPUTE_RULES.get(dispute_type)
    if rule is None:
        fallback = DEFAULT_DISPUTE_RULES["labor_other"]
        return list(fallback["required"]), list(fallback["core"])
    return list(rule["required"]), list(rule["core"])


def get_runtime_claim(dispute_type: str) -> str:
    """返回纠纷类目的文书请求事项表述。"""
    return _RUNTIME_CLAIMS.get(dispute_type) or DEFAULT_DISPUTE_CLAIMS.get(
        dispute_type, DEFAULT_DISPUTE_CLAIMS["labor_other"]
    )


def get_runtime_migrations() -> dict[str, str]:
    return dict(_RUNTIME_MIGRATIONS)


def build_default_package() -> dict[str, Any]:
    """内置默认字典包（无已发布包时的回落内容）。"""
    disputes: list[dict[str, Any]] = []
    for item in DISPUTE_TYPES:
        rule = DEFAULT_DISPUTE_RULES[item["value"]]
        disputes.append(
            {
                "value": item["value"],
                "label": item["label"],
                "group": item["group"],
                "keywords": list(item["keywords"]),
                "required_categories": list(rule["required"]),
                "core_categories": list(rule["core"]),
                "claim_text": DEFAULT_DISPUTE_CLAIMS[item["value"]],
            }
        )
    return {
        "disputes": disputes,
        "stages": [dict(item) for item in STAGES],
        "evidence_categories": [dict(item) for item in EVIDENCE_CATEGORIES],
        "migrations": dict(DISPUTE_TYPE_MIGRATIONS),
    }


def apply_package(content: dict[str, Any]) -> None:
    """公开入口：把字典包内容应用到运行时数据源。"""
    _apply_package(content)


def dictionary_checksum(content: dict[str, Any]) -> str:
    """字典包内容指纹（规范化 JSON 后 sha256）。"""
    import hashlib
    import json

    canonical = json.dumps(
        content, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _apply_package(content: dict[str, Any]) -> None:
    """把字典包内容应用到运行时数据源（原地更新，保持引用稳定）。"""
    disputes = content.get("disputes") or []
    rules: dict[str, dict[str, list[str]]] = {}
    claims: dict[str, str] = {}
    labels: dict[str, str] = {}
    keywords: dict[str, list[str]] = {}
    for item in disputes:
        value = str(item["value"])
        labels[value] = str(item["label"])
        keywords[value] = [str(word) for word in item.get("keywords") or []]
        rules[value] = {
            "required": [str(c) for c in item.get("required_categories") or []],
            "core": [str(c) for c in item.get("core_categories") or []],
        }
        claims[value] = str(item.get("claim_text") or "")

    DISPUTE_LABELS.clear()
    DISPUTE_LABELS.update(labels)
    DISPUTE_KEYWORDS.clear()
    DISPUTE_KEYWORDS.update(keywords)
    _RUNTIME_RULES.clear()
    _RUNTIME_RULES.update(rules)
    _RUNTIME_CLAIMS.clear()
    _RUNTIME_CLAIMS.update(claims)
    _RUNTIME_MIGRATIONS.clear()
    _RUNTIME_MIGRATIONS.update(
        {str(old): str(new) for old, new in (content.get("migrations") or {}).items()}
    )

    # 延迟导入避免模块级循环依赖。
    from app.services.documents import apply_package_claims
    from app.services.evidence_rules import refresh_runtime_rules

    refresh_runtime_rules()
    apply_package_claims(_RUNTIME_CLAIMS)


async def get_active_package(session: Any) -> dict[str, Any]:
    """返回当前生效字典包：最新已发布版本，无包时回落内置默认。

    结果带进程内 TTL 缓存；发布新版本后调用 :func:`invalidate_cache`。
    """
    global _cache
    import time

    now = time.monotonic()
    if _cache is not None and now - _cache[0] < _CACHE_TTL_SECONDS:
        return _cache[1]

    from app.models.dictionary_version import DictionaryVersion

    row = await session.scalar(
        select(DictionaryVersion)
        .where(DictionaryVersion.status == "published")
        .order_by(DictionaryVersion.id.desc())
    )
    content = dict(row.content) if row is not None else build_default_package()
    _cache = (now, content)
    return content


def invalidate_cache() -> None:
    """清空字典包缓存（发布新版本后调用，立即生效于本进程）。"""
    global _cache
    _cache = None


def reset_runtime() -> None:
    """把运行时数据源还原为内置默认（测试隔离用）。"""
    global _cache
    _cache = None
    _apply_package(build_default_package())


def dictionary_payload(content: dict[str, Any] | None = None) -> dict[str, Any]:
    """组装 meta/dictionary 响应（仅下发展示字段）。"""
    package = content or build_default_package()
    return {
        "disputes": [
            {
                "value": item["value"],
                "label": item["label"],
                "group": item.get("group", "labor"),
                "keywords": list(item.get("keywords") or []),
            }
            for item in package["disputes"]
        ],
        "stages": package["stages"],
        "evidence_categories": package["evidence_categories"],
    }

STAGE_LABELS: dict[str, str] = {item["value"]: item["label"] for item in STAGES}
