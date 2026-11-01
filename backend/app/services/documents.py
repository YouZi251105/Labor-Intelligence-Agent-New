from app.models.case import Case
from app.models.evidence import Evidence

DOC_TITLES = {
    "arbitration": "劳动仲裁申请书",
    "complaint": "民事起诉状",
    "settlement": "协商和解协议",
}

CLAIMS = {
    "wage": "请求裁决被申请人支付拖欠的劳动报酬。",
    "termination": "请求裁决被申请人支付违法解除劳动合同赔偿金。",
    "contract": "请求裁决被申请人支付未签订书面劳动合同期间的二倍工资差额。",
    "overtime": "请求裁决被申请人支付加班费。",
    "injury": "请求依法确认工伤待遇并支付相关费用。",
    "insurance": "请求依法处理社会保险补缴或损失赔偿事项。",
    "service_pay": "请求判令被告支付拖欠的劳务报酬。",
    "general": "请求依法处理双方劳动纠纷。",
}


def generate_document(
    case: Case,
    evidence_items: list[Evidence],
    doc_type: str,
) -> tuple[str, str]:
    title = DOC_TITLES[doc_type]
    evidence_lines = "\n".join(
        f"{index + 1}. {item.filename}（{item.category}）"
        for index, item in enumerate(evidence_items)
    ) or "1. 暂无已上传证据"

    if doc_type == "settlement":
        content = (
            f"{title}\n\n"
            "甲方：待确认\n"
            "乙方：待确认\n\n"
            f"一、纠纷概况\n{case.facts or case.summary}\n\n"
            f"二、协商事项\n{CLAIMS.get(case.dispute_type, CLAIMS['general'])}\n\n"
            "三、履行方式\n双方应明确支付金额、支付时间和违约责任。\n\n"
            "四、确认\n本协议为系统生成的演示草稿，签署前应由双方及律师确认。\n"
        )
    else:
        content = (
            f"{title}\n\n"
            "申请人：待确认\n"
            "被申请人：待确认\n\n"
            "请求事项\n"
            f"{CLAIMS.get(case.dispute_type, CLAIMS['general'])}\n\n"
            "事实与理由\n"
            f"{case.facts or case.summary}\n"
            f"案件地点：{case.location or '待确认'}\n\n"
            "证据目录\n"
            f"{evidence_lines}\n\n"
            "风险提示\n"
            "本文书由系统根据用户填写内容生成，属于待确认草稿。"
            "提交前应核对主体、金额、请求事项、管辖和事实表述，并建议由律师复核。\n"
        )
    return title, content
