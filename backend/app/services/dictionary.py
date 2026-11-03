"""业务字典的单一数据源。

集中定义纠纷类型、案件阶段、证据类别及其识别关键词和中文标签，
供字典接口、AI 分类和证据规则共同引用，避免前后端多处硬编码。

法律内容由人工复核人员校验；此模块只提供数据结构与展示映射，
不自行确认法律内容正确性。
"""

from typing import Any

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

# 派生映射，供现有服务代码 import 使用，保持单一来源。
DISPUTE_LABELS: dict[str, str] = {
    item["value"]: item["label"] for item in DISPUTE_TYPES
}
DISPUTE_KEYWORDS: dict[str, list[str]] = {
    item["value"]: item["keywords"] for item in DISPUTE_TYPES if item["keywords"]
}
CATEGORY_LABELS: dict[str, str] = {
    item["value"]: item["label"] for item in EVIDENCE_CATEGORIES
}
STAGE_LABELS: dict[str, str] = {item["value"]: item["label"] for item in STAGES}


def dictionary_payload() -> dict[str, Any]:
    """返回字典接口的结构化数据。"""
    return {
        "disputes": DISPUTE_TYPES,
        "stages": STAGES,
        "evidence_categories": EVIDENCE_CATEGORIES,
    }
