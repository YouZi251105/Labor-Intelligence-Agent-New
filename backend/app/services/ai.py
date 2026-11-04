import asyncio
import json
import logging
import re
from collections.abc import AsyncIterator
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

import httpx

from app.core.config import Settings, get_settings
from app.models.case import Case, Message
from app.services.dictionary import DISPUTE_KEYWORDS, DISPUTE_LABELS

logger = logging.getLogger(__name__)


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
    follow_up_options: list["FollowUpOption"]
    intervention_recommendation: "InterventionRecommendation"
    references: list["ReferenceItem"] = field(default_factory=list)


@dataclass(frozen=True)
class FollowUpOption:
    id: str
    label: str
    message: str
    kind: Literal["send", "fill", "lawyer_request", "filing_review"]


@dataclass(frozen=True)
class InterventionRecommendation:
    recommended: bool
    level: Literal["none", "suggested", "urgent"]
    reasons: list[str]
    action: Literal["lawyer_request", "filing_review"]


@dataclass(frozen=True)
class FollowUpProgress:
    """State used to keep suggested next questions aligned with the case."""

    stage: str = "intake"
    has_evidence: bool = False
    has_documents: bool = False
    lawyer_assigned: bool = False
    lawyer_request_status: str = ""
    case_review_status: str = ""

    @property
    def lawyer_engaged(self) -> bool:
        return self.lawyer_assigned or self.lawyer_request_status in {
            "pending",
            "accepted",
            "in_session",
            "completed",
        }

    @property
    def review_requested(self) -> bool:
        return self.case_review_status in {"pending", "reviewed"}


@dataclass(frozen=True)
class ReferenceItem:
    type: Literal["law", "case"]
    id: str
    title: str
    excerpt: str = ""
    source_name: str = ""
    source_url: str = ""
    review_status: str = "published"
    case_no: str = ""
    court: str = ""
    year: int | None = None


FOLLOW_UP_PATTERN = re.compile(
    r"\s*<FOLLOW_UPS>\s*(\[.*?\])\s*</FOLLOW_UPS>\s*",
    re.DOTALL,
)


def parse_qwen_follow_ups(content: str) -> tuple[str, list[str]]:
    """Remove the model-only follow-up block and return validated questions."""
    match = FOLLOW_UP_PATTERN.search(content)
    if match is None:
        return content.strip(), []
    try:
        raw_options = json.loads(match.group(1))
    except (TypeError, json.JSONDecodeError):
        raw_options = []
    options = [
        value.strip()
        for value in raw_options
        if isinstance(value, str) and value.strip()
    ][:4]
    clean = FOLLOW_UP_PATTERN.sub("", content).strip()
    return clean, options


def extract_qwen_stream_text(line: str) -> str | None:
    """Return a Qwen content delta from one OpenAI-compatible SSE line."""
    stripped = line.strip()
    if not stripped.startswith("data:"):
        return None
    payload = stripped.removeprefix("data:").strip()
    if not payload or payload == "[DONE]":
        return None
    try:
        body = json.loads(payload)
        choices = body.get("choices") or []
        delta = choices[0].get("delta") or {}
        content = delta.get("content")
    except (IndexError, TypeError, json.JSONDecodeError):
        return None
    return content if isinstance(content, str) and content else None


def _reply_requirements(dispute_type: str) -> tuple[str, list[str], list[str]]:
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
    }.get(dispute_type, "补充对方主体信息、事情经过和现有材料。")
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
    }.get(dispute_type, ["对方主体", "事情经过", "当前诉求", "现有材料"])
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
    }.get(dispute_type, ["聊天记录", "合同", "工资记录", "其他事实材料"])
    return next_step, required_information, evidence_gaps


def _build_qwen_prompt(
    case: Case,
    text: str,
    history: list[Message],
    *,
    request_follow_ups: bool,
) -> str:
    history_context = "\n".join(
        f"{item.role}: {item.content}" for item in history[-8:]
    )
    follow_up_instruction = (
        "回答后另起一行输出 2 至 4 个用户可以继续点击追问的问题，格式必须是："
        '<FOLLOW_UPS>["问题1","问题2","问题3"]</FOLLOW_UPS>。'
        "问题要简短、具体，不重复用户原问题。"
        if request_follow_ups
        else ""
    )
    return (
        "你是劳务通的法律咨询助手。请先识别问题类别，再给出简洁建议。"
        "不得保证结果，不得编造法条。"
        "平台设有律师端，并由平台驻场律师和合作律师提供咨询、材料复核、"
        "正式流程前审查等协助；具体代理关系和服务范围由律师评估后与用户确认。"
        "涉及律师、代理、立案或复杂争议时，应引导用户使用平台的律师协助入口，"
        "不得回答平台不提供律师服务、不推荐律师或不对接律师。"
        f"{follow_up_instruction}"
        f"案件事实：{case.facts}\n历史对话：{history_context}\n用户新消息：{text}"
    )


def _result_from_reply(
    *,
    case: Case,
    text: str,
    reply: str,
    classification: dict[str, Any],
    recommendation: InterventionRecommendation,
    next_step: str,
    required_information: list[str],
    evidence_gaps: list[str],
    demo_mode: bool,
    history: list[Message],
    progress: FollowUpProgress | None = None,
    model_suggestions: list[str] | None = None,
) -> AIResult:
    return AIResult(
        reply=reply,
        classification=classification,
        suggested_next_step=next_step,
        demo_mode=demo_mode,
        required_information=required_information,
        evidence_gaps=evidence_gaps,
        risk_flags=["注意仲裁时效和材料完整性，关键判断建议人工复核。"],
        citations=[],
        summary=(
            f"初步判断为{classification['dispute_label']}，需要补充信息和材料后继续处理。"
            if demo_mode
            else reply[:180]
        ),
        follow_up_options=build_follow_up_options(
            f"{case.facts}\n{text}",
            required_information,
            next_step,
            recommendation,
            history=history,
            progress=progress,
            model_suggestions=model_suggestions,
        ),
        intervention_recommendation=recommendation,
    )


def _normalize_follow_up_text(text: str) -> str:
    return " ".join(text.strip().rstrip("。！？!?").split())


def build_follow_up_options(
    context: str,
    required_information: list[str],
    next_step: str,
    recommendation: InterventionRecommendation,
    *,
    history: list[Message] | None = None,
    progress: FollowUpProgress | None = None,
    model_suggestions: list[str] | None = None,
) -> list[FollowUpOption]:
    """Build questions that reflect current gaps, actions and case progress."""
    history = history or []
    progress = progress or FollowUpProgress()
    options: list[FollowUpOption] = []
    seen_messages: set[str] = set()
    previous_user_messages = {
        _normalize_follow_up_text(item.content)
        for item in history
        if item.role == "user" and item.content.strip()
    }

    def add_option(
        *,
        option_id: str,
        label: str,
        message: str,
        kind: Literal["send", "fill", "lawyer_request", "filing_review"],
    ) -> None:
        if len(options) >= 4:
            return
        message_key = _normalize_follow_up_text(message)
        label_key = _normalize_follow_up_text(label)
        if (
            not message_key
            or not label_key
            or message_key in seen_messages
            or message_key in previous_user_messages
            or label_key in {_normalize_follow_up_text(item.label) for item in options}
        ):
            return
        options.append(
            FollowUpOption(
                id=option_id,
                label=label,
                message=message,
                kind=kind,
            )
        )
        seen_messages.add(message_key)

    missing = [
        item
        for item in required_information
        if not _information_present(item, context)
    ]
    if missing:
        fill_target = missing[0]
        add_option(
            option_id="missing-info-1",
            label=f"补充：{fill_target}",
            message=f"关于{fill_target}，我的情况是：",
            kind="fill",
        )

    if progress.review_requested:
        add_option(
            option_id="review-focus",
            label="了解复核重点",
            message="平台律师复核时重点会看哪些材料？",
            kind="send",
        )
        add_option(
            option_id="review-next",
            label="复核后怎么继续",
            message="复核结论出来后，我还需要做什么？",
            kind="send",
        )
    elif progress.lawyer_engaged:
        add_option(
            option_id="lawyer-materials",
            label="补充律师所需材料",
            message="律师介入后，我还需要补充哪些材料？",
            kind="send",
        )
        add_option(
            option_id="lawyer-context",
            label="准备律师沟通",
            message="和律师沟通时，我应该先说明哪些关键事实？",
            kind="send",
        )
        if recommendation.recommended and recommendation.action == "filing_review":
            add_option(
                option_id="recommended-filing_review",
                label="申请正式流程前复核",
                message="申请正式流程前复核",
                kind="filing_review",
            )
    elif recommendation.recommended:
        action_label = (
            "申请律师介入"
            if recommendation.action == "lawyer_request"
            else "申请正式流程前复核"
        )
        action_message = (
            "申请律师介入"
            if recommendation.action == "lawyer_request"
            else "申请正式流程前复核"
        )
        add_option(
            option_id=f"recommended-{recommendation.action}",
            label=action_label,
            message=action_message,
            kind=recommendation.action,
        )

    stage_questions: list[tuple[str, str]] = []
    if progress.stage in {"intake", "evidence"}:
        if progress.has_evidence:
            stage_questions.append(
                ("检查现有材料", "请帮我检查现有材料还缺什么。")
            )
        else:
            stage_questions.append(
                ("先上传哪些材料", "我应该先上传哪些最有用的材料？")
            )
        stage_questions.append(
            ("准备到什么程度", "证据准备到什么程度可以进入下一步？")
        )
    elif progress.stage == "procedure":
        stage_questions.extend(
            [
                ("选择办理路径", "根据我的情况，应该先协商、投诉还是申请仲裁？"),
                ("核对关键期限", "选择办理路径前需要核对哪些期限？"),
            ]
        )
    elif progress.stage == "document":
        stage_questions.extend(
            [
                ("核对文书内容", "请帮我核对文书中的主体、金额、请求事项和证据编号。"),
                ("检查证据目录", "当前证据目录还缺哪些材料？"),
            ]
        )
    elif progress.stage == "lawyer_help":
        stage_questions.append(
            ("准备律师复核", "律师复核前，我还需要准备哪些说明和材料？")
        )
    elif progress.stage == "closed":
        stage_questions.append(
            ("归档与后续", "这个案件应如何归档，后续出现新情况怎么继续？")
        )

    stage_questions.append(
        (
            "下一步先做什么",
            f"围绕“{next_step}”，我现在最先做什么？",
        )
    )
    for index, (label, message) in enumerate(stage_questions, start=1):
        add_option(
            option_id=f"progress-{index}",
            label=label,
            message=message,
            kind="send",
        )

    suggestions = model_suggestions or []
    for index, suggestion in enumerate(suggestions, start=1):
        normalized = suggestion.strip()
        if not normalized:
            continue
        if progress.review_requested and "复核" in normalized:
            continue
        if (
            progress.lawyer_engaged
            and "律师" in normalized
            and any(term in normalized for term in ("申请", "预约", "介入"))
        ):
            continue
        add_option(
            option_id=f"suggestion-{index}",
            label=_follow_up_label(normalized, index, progress),
            message=normalized,
            kind="send",
        )

    if len(options) < 2:
        add_option(
            option_id="fallback-facts",
            label="补充关键事实",
            message="我还需要补充哪些关键事实？",
            kind="send",
        )
        add_option(
            option_id="fallback-next",
            label="下一步怎么做",
            message="根据当前材料和进度，我下一步应该做什么？",
            kind="send",
        )
    return options


def assess_intervention_recommendation(
    text: str,
    classification: dict[str, Any],
) -> InterventionRecommendation:
    """Recommend a lawyer workflow without assigning one automatically."""
    filing_terms = ("仲裁", "起诉", "法院", "立案", "开庭", "申请书")
    urgent_terms = ("工伤", "时效", "马上", "紧急", "尽快", "期限", "今天", "明天")
    complex_terms = (
        "复杂",
        "不承认",
        "没签合同",
        "包工头",
        "多个",
        "证据不足",
        "不知道",
    )
    reasons: list[str] = []
    action: Literal["lawyer_request", "filing_review"] = "lawyer_request"
    if any(term in text for term in filing_terms):
        action = "filing_review"
        reasons.append("用户提到仲裁、起诉或正式立案流程")
    if any(term in text for term in urgent_terms):
        reasons.append("问题涉及工伤、期限或紧急处理")
    if any(term in text for term in complex_terms):
        reasons.append("当前事实或责任关系需要人工判断")
    if classification["dispute_type"] in {"labor_confirmation", "service_injury"}:
        reasons.append("该纠纷类型涉及关系认定或人身损害，风险较高")

    level: Literal["none", "suggested", "urgent"]
    if any(term in text for term in urgent_terms) or classification[
        "dispute_type"
    ] == "service_injury":
        level = "urgent"
    elif reasons:
        level = "suggested"
    else:
        level = "none"
    return InterventionRecommendation(
        recommended=bool(reasons),
        level=level,
        reasons=list(dict.fromkeys(reasons)),
        action=action,
    )


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
    dispute_type = classification["dispute_type"]
    relationship = "劳务关系" if classification["legal_relationship"] == "service" else "劳动关系"
    # 自定义分类可能没有内置提示文案，回落到兜底分类的表述。
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
    }.get(
        dispute_type, "聊天记录、合同、工资记录和能够说明事情经过的材料"
    )

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
        f"下一步建议：先整理{evidence_hint}，再判断是否需要协商、仲裁，"
        "或通过案件页申请平台律师协助复核。\n\n"
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
        "references": [asdict(item) for item in result.references],
        "demo_mode": result.demo_mode,
        "follow_up_options": [asdict(item) for item in result.follow_up_options],
        "intervention_recommendation": asdict(result.intervention_recommendation),
    }


async def generate_ai_reply(
    case: Case,
    text: str,
    history: list[Message],
    *,
    progress: FollowUpProgress | None = None,
) -> AIResult:
    settings = get_settings()
    classification = classify_message(text)
    recommendation = assess_intervention_recommendation(text, classification)
    dispute_type = classification["dispute_type"]
    next_step, required_information, evidence_gaps = _reply_requirements(
        dispute_type
    )

    if settings.qianwen_api_key:
        try:
            prompt = _build_qwen_prompt(
                case,
                text,
                history,
                request_follow_ups=True,
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
            clean_content, model_suggestions = parse_qwen_follow_ups(content)
            if not clean_content:
                raise ValueError("Qwen returned an empty reply")
            return _result_from_reply(
                case=case,
                text=text,
                reply=clean_content,
                classification=classification,
                recommendation=recommendation,
                next_step=next_step,
                required_information=required_information,
                evidence_gaps=evidence_gaps,
                demo_mode=False,
                history=history,
                progress=progress,
                model_suggestions=model_suggestions,
            )
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            logger.warning("Qwen API request failed (%s), falling back to demo: %s", type(exc).__name__, exc)

    return _result_from_reply(
        case=case,
        text=text,
        reply=build_demo_reply(case, text, classification, history),
        classification=classification,
        recommendation=recommendation,
        next_step=next_step,
        required_information=required_information,
        evidence_gaps=evidence_gaps,
        demo_mode=True,
        history=history,
        progress=progress,
    )


async def _stream_qwen_content(
    *,
    prompt: str,
    text: str,
    settings: Settings,
) -> AsyncIterator[str]:
    async with (
        httpx.AsyncClient(timeout=60) as client,
        client.stream(
            "POST",
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.qianwen_api_key}"},
            json={
                "model": settings.qianwen_model,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text},
                ],
                "temperature": 0.3,
                "stream": True,
            },
        ) as response,
    ):
        response.raise_for_status()
        async for line in response.aiter_lines():
            content = extract_qwen_stream_text(line)
            if content:
                yield content


async def generate_ai_reply_stream(
    case: Case,
    text: str,
    history: list[Message],
    *,
    progress: FollowUpProgress | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Yield safe UI events while reading real Qwen content tokens."""
    settings = get_settings()
    classification = classify_message(text)
    recommendation = assess_intervention_recommendation(text, classification)
    next_step, required_information, evidence_gaps = _reply_requirements(
        classification["dispute_type"]
    )

    yield {
        "type": "status",
        "stage": "thinking",
        "label": "正在理解你的问题…",
    }

    generating_sent = False
    if settings.qianwen_api_key:
        try:
            prompt = _build_qwen_prompt(
                case,
                text,
                history,
                request_follow_ups=False,
            )
            parts: list[str] = []
            async for content in _stream_qwen_content(
                prompt=prompt,
                text=text,
                settings=settings,
            ):
                if not generating_sent:
                    generating_sent = True
                    yield {
                        "type": "status",
                        "stage": "generating",
                        "label": "正在生成回复…",
                    }
                parts.append(content)
                yield {"type": "delta", "text": content}
            reply = "".join(parts).strip()
            if not reply:
                raise ValueError("Qwen stream returned an empty reply")
            yield {
                "type": "complete",
                "result": _result_from_reply(
                    case=case,
                    text=text,
                    reply=reply,
                    classification=classification,
                    recommendation=recommendation,
                    next_step=next_step,
                    required_information=required_information,
                    evidence_gaps=evidence_gaps,
                    demo_mode=False,
                    history=history,
                    progress=progress,
                ),
            }
            return
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            logger.warning("Qwen stream request failed (%s), falling back to demo: %s", type(exc).__name__, exc)
            if generating_sent:
                raise

    if not generating_sent:
        yield {
            "type": "status",
            "stage": "generating",
            "label": "正在生成回复…",
        }
    reply = build_demo_reply(case, text, classification, history)
    for start in range(0, len(reply), 24):
        chunk = reply[start : start + 24]
        yield {"type": "delta", "text": chunk}
        await asyncio.sleep(0.02)
    yield {
        "type": "complete",
        "result": _result_from_reply(
            case=case,
            text=text,
            reply=reply,
            classification=classification,
            recommendation=recommendation,
            next_step=next_step,
            required_information=required_information,
            evidence_gaps=evidence_gaps,
            demo_mode=True,
            history=history,
            progress=progress,
        ),
    }


def _information_present(label: str, context: str) -> bool:
    if label in context:
        return True
    if any(keyword in label for keyword in ("金额", "工资标准", "欠款", "损失")):
        return bool(re.search(r"\d+(?:\.\d+)?\s*(?:元|万|千|块)", context))
    if any(
        keyword in label
        for keyword in ("时间", "起止", "入职", "解除", "受伤")
    ):
        return bool(
            re.search(
                r"(?:\d{4}年|\d{1,2}月|\d+\s*(?:天|个月|年)|"
                r"今天|昨天|上周|去年|上个月)",
                context,
            )
        )
    if any(keyword in label for keyword in ("主体", "委托方")):
        return bool(re.search(r"公司|老板|单位|包工头|雇主|委托方", context))
    return False


def _follow_up_label(
    message: str,
    index: int,
    progress: FollowUpProgress,
) -> str:
    labels = {
        "复核": "了解复核重点" if progress.review_requested else "申请人工复核",
        "律师": "补充律师所需信息" if progress.lawyer_engaged else "申请律师协助",
        "协商": "选择办理路径",
        "投诉": "选择办理路径",
        "仲裁": "核对仲裁准备",
        "材料": "检查材料缺口",
        "期限": "核对关键期限",
        "文书": "核对文书内容",
    }
    for keyword, label in labels.items():
        if keyword in message:
            return label
    return f"继续追问 {index}"
