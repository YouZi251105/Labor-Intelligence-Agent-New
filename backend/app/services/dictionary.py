"""业务字典的单一数据源。

集中定义纠纷类型、案件阶段、证据类别及其识别关键词和中文标签，
供字典接口、AI 分类和证据规则共同引用，避免前后端多处硬编码。

法律内容由人工复核人员校验；此模块只提供数据结构与展示映射，
不自行确认法律内容正确性。
"""

from typing import Any

DISPUTE_TYPES: list[dict[str, Any]] = [
    {
        "value": "wage",
        "label": "欠薪",
        "keywords": ["工资", "欠薪", "拖欠", "工钱", "不发", "讨薪"],
    },
    {
        "value": "termination",
        "label": "违法解除",
        "keywords": ["辞退", "开除", "解雇", "裁员", "解除"],
    },
    {
        "value": "contract",
        "label": "劳动合同",
        "keywords": ["合同", "没签", "双倍工资", "试用期"],
    },
    {
        "value": "overtime",
        "label": "加班费",
        "keywords": ["加班", "加班费", "工时"],
    },
    {
        "value": "injury",
        "label": "工伤待遇",
        "keywords": ["工伤", "受伤", "医疗费", "伤残"],
    },
    {
        "value": "insurance",
        "label": "社会保险",
        "keywords": ["社保", "保险", "公积金"],
    },
    {
        "value": "service_pay",
        "label": "劳务报酬",
        "keywords": ["劳务费", "劳务报酬", "包工头"],
    },
    {"value": "general", "label": "一般劳动纠纷", "keywords": []},
]

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
