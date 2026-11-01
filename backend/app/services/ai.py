from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings
from app.models.case import Case, Message

DISPUTE_KEYWORDS = {
    "wage": ["工资", "欠薪", "拖欠", "工钱", "不发", "讨薪"],
    "termination": ["辞退", "开除", "解雇", "裁员", "解除"],
    "contract": ["合同", "没签", "双倍工资", "试用期"],
    "overtime": ["加班", "加班费", "工时"],
    "injury": ["工伤", "受伤", "医疗费", "伤残"],
    "insurance": ["社保", "保险", "公积金"],
    "service_pay": ["劳务费", "劳务报酬", "包工头"],
}

DISPUTE_LABELS = {
    "wage": "欠薪",
    "termination": "违法解除",
    "contract": "劳动合同",
    "overtime": "加班费",
    "injury": "工伤待遇",
    "insurance": "社会保险",
    "service_pay": "劳务报酬",
    "general": "一般劳动纠纷",
}


@dataclass
class AIResult:
    reply: str
    classification: dict[str, Any]
    suggested_next_step: str
    demo_mode: bool
    required_information: list[str]
    evidence_gaps: list[str]
    risk_flags: list[str]
    citations: list[str]
    summary: str


def classify_message(text: str) -> dict[str, Any]:
    scores = {
        dispute: sum(1 for keyword in keywords if keyword in text)
        for dispute, keywords in DISPUTE_KEYWORDS.items()
    }
    dispute_type = max(scores, key=scores.get)
    if scores[dispute_type] == 0:
        dispute_type = "general"

    service_markers = ["包工头", "个人雇佣", "劳务关系", "临时工", "按次结算"]
    legal_relationship = "service" if any(marker in text for marker in service_markers) else "labor"
    return {
        "dispute_type": dispute_type,
        "dispute_label": DISPUTE_LABELS[dispute_type],
        "legal_relationship": legal_relationship,
        "signals": [keyword for keyword in DISPUTE_KEYWORDS.get(dispute_type, []) if keyword in text],
    }


def build_demo_reply(
    case: Case,
    text: str,
    classification: dict[str, Any],
    history: list[Message],
) -> str:
    label = classification["dispute_label"]
    relationship = "劳务关系" if classification["legal_relationship"] == "service" else "劳动关系"
    evidence_hint = {
        "wage": "工资流水、聊天记录、考勤记录和欠薪金额说明",
        "termination": "解除通知、聊天记录、劳动合同和工资流水",
        "contract": "实际用工记录、工资流水和工作安排聊天记录",
        "overtime": "考勤记录、排班表、加班通知和工资流水",
        "injury": "就医材料、事故经过、同事证言和用工记录",
        "insurance": "社保缴费记录、工资流水和劳动合同",
        "service_pay": "结算单、聊天记录、转账记录和工作成果",
        "general": "聊天记录、合同、工资记录和能够说明事情经过的材料",
    }[classification["dispute_type"]]

    previous_user_messages = [item.content for item in history if item.role == "user"]
    context_line = (
        f"结合此前对话，你已经提到“{previous_user_messages[-1][:60]}”，"
        "我会把这些信息作为同一案件背景继续处理。"
        if previous_user_messages
        else ""
    )

    return (
        f"我先把你现在的问题归为“{label}”，初步按{relationship}方向了解。\n\n"
        f"{context_line}\n\n"
        f"从你刚才的描述看，关键事实是：{text[:120]}。"
        "这个阶段先不要急着写完整文书，先确认对方主体、工作时间、金额和时间线。\n\n"
        f"下一步建议：先整理{evidence_hint}，再判断是否需要协商、仲裁或直接咨询律师。\n\n"
        "当前使用本地演示规则回复。配置千问 API Key 后，会基于同样案件上下文生成更自然的分析。"
    )


def structured_result(result: AIResult) -> dict[str, Any]:
    return {
        "intent": result.classification["dispute_type"],
        "dispute_label": result.classification["dispute_label"],
        "legal_relationship": result.classification["legal_relationship"],
        "summary": result.summary,
        "suggested_next_step": result.suggested_next_step,
        "required_information": result.required_information,
        "evidence_gaps": result.evidence_gaps,
        "risk_flags": result.risk_flags,
        "citations": result.citations,
        "demo_mode": result.demo_mode,
    }


async def generate_ai_reply(
    case: Case,
    text: str,
    history: list[Message],
) -> AIResult:
    settings = get_settings()
    classification = classify_message(text)
    next_step = {
        "wage": "整理工资流水和欠薪聊天记录，确认欠薪金额。",
        "termination": "保存解除通知和沟通记录，核对解除理由。",
        "contract": "补充工作安排、工资支付和考勤记录。",
        "overtime": "收集排班、打卡和加班通知。",
        "injury": "保存就医材料并尽快确认工伤认定时限。",
        "insurance": "查询社保缴费记录并保存工资流水。",
        "service_pay": "整理结算单、聊天记录和转账凭证。",
        "general": "补充对方主体信息、事情经过和现有材料。",
    }[classification["dispute_type"]]
    required_information = {
        "wage": ["用工主体", "入职时间", "工资标准", "欠薪金额和时间"],
        "termination": ["解除时间", "解除原因", "是否收到书面通知", "工资标准"],
        "contract": ["入职时间", "实际用工安排", "工资支付方式"],
        "overtime": ["工作时间", "加班安排", "工资标准"],
        "injury": ["受伤时间", "就医情况", "事故发生经过"],
        "insurance": ["工作起止时间", "工资标准", "社保缴费情况"],
        "service_pay": ["委托方主体", "工作成果", "结算约定", "欠款金额"],
        "general": ["对方主体", "事情经过", "当前诉求", "现有材料"],
    }[classification["dispute_type"]]
    evidence_gaps = {
        "wage": ["工资或转账记录", "聊天记录", "劳动合同或其他用工证明"],
        "termination": ["解除通知", "聊天记录", "劳动合同", "工资流水"],
        "contract": ["实际用工记录", "工资流水", "工作安排聊天记录"],
        "overtime": ["考勤记录", "排班表", "加班通知", "工资流水"],
        "injury": ["就医材料", "事故经过", "同事证言", "用工记录"],
        "insurance": ["社保缴费记录", "工资流水", "劳动合同"],
        "service_pay": ["结算单", "聊天记录", "转账记录", "工作成果"],
        "general": ["聊天记录", "合同", "工资记录", "其他事实材料"],
    }[classification["dispute_type"]]
    risk_flags = ["注意仲裁时效和材料完整性，关键判断建议人工复核。"]

    if settings.qianwen_api_key:
        try:
            context = "\n".join(
                f"{item.role}: {item.content}" for item in history[-8:]
            )
            prompt = (
                "你是劳务通的法律咨询助手。请先识别问题类别，再给出简洁建议。"
                "不得保证结果，不得编造法条。案件事实："
                f"{case.facts}\n历史对话：{context}\n用户新消息：{text}"
            )
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.qianwen_api_key}"},
                    json={
                        "model": settings.qianwen_model,
                        "messages": [
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": text},
                        ],
                        "temperature": 0.3,
                    },
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
            return AIResult(
                reply=content,
                classification=classification,
                suggested_next_step=next_step,
                demo_mode=False,
                required_information=required_information,
                evidence_gaps=evidence_gaps,
                risk_flags=risk_flags,
                citations=[],
                summary=content[:180],
            )
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            pass

    return AIResult(
        reply=build_demo_reply(case, text, classification, history),
        classification=classification,
        suggested_next_step=next_step,
        demo_mode=True,
        required_information=required_information,
        evidence_gaps=evidence_gaps,
        risk_flags=risk_flags,
        citations=[],
        summary=f"初步判断为{classification['dispute_label']}，需要补充信息和材料后继续处理。",
    )
