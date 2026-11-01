import re

ROLE_LABELS = {
    "boss": "单位负责人",
    "hr": "人事",
    "arbitrator": "仲裁员",
    "judge": "法官",
    "lawyer": "律师",
}

EVIDENCE_WORDS = ("工资", "流水", "聊天", "合同", "考勤", "录音", "证据")
LEGAL_WORDS = ("仲裁", "法律", "书面", "协商", "申请", "权利", "赔偿", "支付")
AGGRESSIVE_WORDS = ("威胁", "曝光", "闹事", "报复")


def score_simulation_message(content: str) -> dict[str, object]:
    text = content.strip()
    sentences = [part for part in re.split(r"[。！？!?；;]", text) if part.strip()]
    evidence_hits = sum(1 for word in EVIDENCE_WORDS if word in text)
    legal_hits = sum(1 for word in LEGAL_WORDS if word in text)
    aggressive_hits = sum(1 for word in AGGRESSIVE_WORDS if word in text)

    clarity = min(10, 4 + min(len(sentences), 3) + (1 if len(text) >= 20 else 0))
    evidence_awareness = min(10, 3 + evidence_hits * 2)
    legal_appropriateness = min(
        10,
        max(1, 5 + legal_hits - aggressive_hits * 3),
    )
    overall = round((clarity + evidence_awareness + legal_appropriateness) / 3)

    suggestions: list[str] = []
    if len(text) < 20:
        suggestions.append("补充具体时间、金额和诉求。")
    if evidence_hits == 0:
        suggestions.append("说明你已掌握哪些工资、合同或聊天材料。")
    if legal_hits == 0:
        suggestions.append("明确提出书面确认、支付期限或仲裁等后续路径。")
    if aggressive_hits:
        suggestions.append("避免威胁性表达，保持事实和诉求清晰。")
    if not suggestions:
        suggestions.append("表达较完整，可继续要求对方给出明确时间和书面答复。")

    return {
        "clarity": clarity,
        "evidence_awareness": evidence_awareness,
        "legal_appropriateness": legal_appropriateness,
        "overall": overall,
        "suggestions": suggestions,
    }


def generate_simulation_reply(
    role_type: str,
    scenario: str,
    content: str,
    turn_count: int,
) -> str:
    label = ROLE_LABELS[role_type]
    if role_type == "boss":
        return (
            f"【{label}模拟】我理解你提到“{content[:36]}”，但公司还需要核对账目。"
            "你可以说明具体月份、金额和希望确认的支付时间，我会记录后答复。"
        )
    if role_type == "hr":
        return (
            f"【{label}模拟】请先说明“{scenario}”涉及的时间范围，并提交工资记录、"
            "考勤或沟通材料。我们会按流程核对，不先作事实认定。"
        )
    if role_type == "arbitrator":
        return (
            f"【{label}模拟】第 {turn_count} 轮沟通中，请注意把请求事项、金额、"
            "事实时间和证据来源分开陈述，避免只作情绪性表达。"
        )
    if role_type == "judge":
        return (
            f"【{label}模拟】请围绕“{scenario}”说明事实经过、争议焦点和证据。"
            "当前为沟通训练，不评价真实案件裁判结果。"
        )
    return (
        f"【{label}模拟】你的表达已经进入主题。建议继续补充证据来源、"
        "具体金额和可执行的下一步，并为对方答复保留书面记录。"
    )
