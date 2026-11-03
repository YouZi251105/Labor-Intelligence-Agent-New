from contextlib import suppress
from html import escape
from io import BytesIO

from docx import Document as DocxDocument
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.models.case import Case
from app.models.evidence import Evidence

DOC_TITLES = {
    "arbitration": "劳动仲裁申请书",
    "complaint": "民事起诉状",
    "settlement": "协商和解协议",
}

CLAIMS = {
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

# 旧纠纷枚举 -> 新纠纷枚举，保证迁移前生成的案件继续可生成文书。
LEGACY_DISPUTE_TYPES = {
    "general": "labor_other",
    "wage": "labor_pay",
    "overtime": "labor_pay",
    "injury": "labor_pay",
    "insurance": "labor_benefits",
    "contract": "labor_contract",
    "termination": "labor_termination",
}


def generate_document(
    case: Case,
    evidence_items: list[Evidence],
    doc_type: str,
) -> tuple[str, str]:
    title = DOC_TITLES[doc_type]
    claim_key = LEGACY_DISPUTE_TYPES.get(case.dispute_type, case.dispute_type)
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
            f"二、协商事项\n{CLAIMS.get(claim_key, CLAIMS['labor_other'])}\n\n"
            "三、履行方式\n双方应明确支付金额、支付时间和违约责任。\n\n"
            "四、确认\n本协议为系统生成的演示草稿，签署前应由双方及律师确认。\n"
        )
    else:
        content = (
            f"{title}\n\n"
            "申请人：待确认\n"
            "被申请人：待确认\n\n"
            "请求事项\n"
            f"{CLAIMS.get(claim_key, CLAIMS['labor_other'])}\n\n"
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


def render_document_docx(title: str, content: str) -> bytes:
    document = DocxDocument()
    document.add_heading(title, level=1)
    for line in content.splitlines():
        if line.strip():
            document.add_paragraph(line)
        else:
            document.add_paragraph("")
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def render_document_pdf(content: str) -> bytes:
    buffer = BytesIO()
    with suppress(KeyError, ValueError):
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

    style = ParagraphStyle(
        "LegalDocument",
        fontName="STSong-Light",
        fontSize=11,
        leading=18,
        spaceAfter=5,
        wordWrap="CJK",
    )
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="劳务通法律文书草稿",
    )
    flowables = []
    for line in content.splitlines():
        if line.strip():
            flowables.append(Paragraph(escape(line), style))
        else:
            flowables.append(Spacer(1, 6))
    document.build(flowables)
    return buffer.getvalue()
