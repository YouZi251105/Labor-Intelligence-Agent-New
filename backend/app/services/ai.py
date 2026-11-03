from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings
from app.models.case import Case, Message
from app.services.dictionary import DISPUTE_KEYWORDS, DISPUTE_LABELS


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
    dispute_type = max(scores, key=lambda dispute: scores[dispute])
    if scores[dispute_type] == 0:
        dispute_type = "labor_other"

    service_markers = ["包工头", "个人雇佣", "劳务关系", "临时工", "按次结算"]
    legal_relationship = "service" if any(marker in text for marker in service_markers) else "labor"
    return {
        "dispute_type": dispute_type,
        "dispute_label": DISPUTE_LABELS[dispute_type],
        "legal_relationship": legal_relationship,
        "signals": [
            keyword
            for keyword in DISPUTE_KEYWORDS.get(dispute_type, [])
            if keyword in text
        ],
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
        "labor_confirmation": "实际用工记录、工资流水和工作安排聊天记录",
        "labor_contract": "劳动合同、实际用工记录、工资流水和工作安排聊天记录",
        "labor_termination": "解除通知、聊天记录、劳动合同和工资流水",
        "labor_benefits": "社保缴费记录、考勤排班记录、工资流水和劳动合同",
        "labor_pay": "工资流水、聊天记录、考勤记录和金额说明",
        "labor_other": "聊天记录、合同、工资记录和能够说明事情经过的材料",
        "service_pay": "结算单、聊天记录、转账记录和工作成果",
        "service_quality": "劳务合同、工作成果记录、验收或返工沟通记录",
        "service_injury": "就医材料、事故经过、现场记录和劳务关系证明",
        "service_breach": "劳务合同、解除沟通记录和结算凭证",
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
        "labor_confirmation": "补充入职时间、工作安排和工资支付记录，用于确认劳动关系。",
        "labor_contract": "整理劳动合同、续签或变更沟通记录和工资流水。",
        "labor_termination": "保存解除通知和沟通记录，核对解除理由。",
        "labor_benefits": "查询社保缴费记录，保存考勤排班和工资流水。",
        "labor_pay": "整理工资流水和欠薪聊天记录，确认金额。",
        "labor_other": "补充对方主体信息、事情经过和现有材料。",
        "service_pay": "整理结算单、聊天记录和转账凭证。",
        "service_quality": "保存劳务合同、工作成果记录和验收沟通。",
        "service_injury": "保存就医材料并固定事故经过证据。",
        "service_breach": "整理劳务合同、解除沟通和结算凭证。",
    }[classification["dispute_type"]]
    required_information = {
        "labor_confirmation": ["入职时间", "工作安排", "工资支付方式", "管理方式"],
        "labor_contract": ["入职时间", "合同签订情况", "实际用工安排", "工资支付方式"],
        "labor_termination": ["解除时间", "解除原因", "是否收到书面通知", "工资标准"],
        "labor_benefits": ["工作起止时间", "工时安排", "社保缴费情况", "工资标准"],
        "labor_pay": ["用工主体", "入职时间", "工资标准", "金额和发生时间"],
        "labor_other": ["对方主体", "事情经过", "当前诉求", "现有材料"],
        "service_pay": ["委托方主体", "工作成果", "结算约定", "欠款金额"],
        "service_quality": ["委托方主体", "工作内容", "质量约定", "争议焦点"],
        "service_injury": ["受伤时间", "就医情况", "事故发生经过", "劳务关系"],
        "service_breach": ["委托方主体", "合同约定", "解除经过", "损失情况"],
    }[classification["dispute_type"]]
    evidence_gaps = {
        "labor_confirmation": ["工资或转账记录", "工作安排聊天记录", "工牌工服等用工证明"],
        "labor_contract": ["劳动合同", "实际用工记录", "工资流水", "考勤记录"],
        "labor_termination": ["解除通知", "聊天记录", "劳动合同", "工资流水"],
        "labor_benefits": ["社保缴费记录", "考勤或排班记录", "工资流水"],
        "labor_pay": ["工资或转账记录", "聊天记录", "劳动合同或其他用工证明"],
        "labor_other": ["聊天记录", "合同", "工资记录", "其他事实材料"],
        "service_pay": ["结算单", "聊天记录", "转账记录", "工作成果"],
        "service_quality": ["劳务合同", "工作成果记录", "验收或返工沟通记录"],
        "service_injury": ["就医材料", "事故经过记录", "劳务关系证明"],
        "service_breach": ["劳务合同", "解除沟通记录", "结算凭证"],
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
