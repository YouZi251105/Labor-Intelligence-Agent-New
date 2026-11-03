from __future__ import annotations

from io import BytesIO
from typing import Any

from docx import Document
from docx.document import Document as DocxDocument
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from docx.table import Table


def export_rule_package_review_docx(content: dict[str, Any]) -> bytes:
    document = Document()
    _configure_document(document)
    document.add_heading("劳务通规则包复核稿", level=0)

    stage_labels = {
        str(stage.get("key", "")): str(stage.get("label") or stage.get("key", ""))
        for stage in content.get("stages", [])
    }
    node_labels = _node_labels(content, stage_labels)

    _add_metadata_table(document, content, stage_labels, node_labels)

    document.add_heading("一、配置概览", level=1)
    document.add_paragraph(
        f"本规则包包含 {len(content.get('stages', []))} 个阶段、"
        f"{len(content.get('nodes', {}))} 个流程节点、"
        f"{_option_count(content)} 条处理路径。"
    )
    disclaimer = str(content.get("disclaimer") or "").strip()
    if disclaimer:
        document.add_paragraph(f"免责声明：{disclaimer}")

    document.add_heading("二、案件阶段", level=1)
    stage_table = document.add_table(rows=1, cols=3)
    _set_table_header(stage_table, ["序号", "阶段名称", "阶段说明"])
    for index, stage in enumerate(content.get("stages", []), start=1):
        row = stage_table.add_row().cells
        row[0].text = str(index)
        row[1].text = str(stage.get("label") or stage.get("key", ""))
        row[2].text = str(stage.get("description") or "")

    document.add_heading("三、流程节点与处理路径", level=1)
    for node_id, node in content.get("nodes", {}).items():
        document.add_heading(
            str(node.get("label") or node_labels.get(str(node_id), "流程节点")),
            level=2,
        )
        document.add_paragraph(
            f"所属阶段：{stage_labels.get(str(node.get('stage', '')), node.get('stage', ''))}"
        )
        options = node.get("options", [])
        if not options:
            document.add_paragraph("该节点为流程结束节点，没有后续处理选项。")
            continue
        option_table = document.add_table(rows=1, cols=5)
        _set_table_header(
            option_table,
            ["处理选项", "选项说明", "去向节点", "选择结果", "下一步操作"],
        )
        for option in options:
            row = option_table.add_row().cells
            row[0].text = str(option.get("label") or "")
            row[1].text = str(option.get("description") or "")
            row[2].text = node_labels.get(
                str(option.get("target_node", "")),
                str(option.get("target_node", "")),
            )
            row[3].text = str(option.get("outcome") or "")
            row[4].text = str(option.get("next_step") or "")
            requirements = option.get("requirements", [])
            if requirements:
                document.add_paragraph(
                    "前置条件："
                    + "；".join(
                        _requirement_label(item) for item in requirements
                    )
                )
            for deadline in option.get("deadlines", []):
                document.add_paragraph(
                    "期限复核："
                    f"{deadline.get('title', '')}；"
                    f"{deadline.get('description', '')}；"
                    f"起算事件：{deadline.get('start_event', '') or '待确认'}；"
                    f"法律依据：{deadline.get('basis', '') or '待确认'}"
                )

    document.add_heading("四、法学复核意见", level=1)
    document.add_paragraph("复核结论：□ 通过  □ 需修改  □ 不通过")
    document.add_paragraph("复核意见：")
    for _ in range(5):
        document.add_paragraph("_" * 72)
    document.add_paragraph("复核人：________________    复核日期：________________")
    document.add_paragraph(
        "说明：本复核稿由系统依据规则包内容自动生成，仅用于法学内容复核、"
        "版本比对和归档，不构成正式法律意见。"
    )

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _configure_document(document: DocxDocument) -> None:
    for section in document.sections:
        section.top_margin = Cm(2.2)
        section.bottom_margin = Cm(2.2)
        section.left_margin = Cm(2.4)
        section.right_margin = Cm(2.4)
    normal = document.styles["Normal"]
    normal.font.name = "宋体"
    normal.font.size = Pt(10.5)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    for style_name in ["Title", "Heading 1", "Heading 2"]:
        style = document.styles[style_name]
        style.font.name = "宋体"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")


def _add_metadata_table(
    document: DocxDocument,
    content: dict[str, Any],
    stage_labels: dict[str, str],
    node_labels: dict[str, str],
) -> None:
    table = document.add_table(rows=1, cols=2)
    _set_table_header(table, ["项目", "内容"])
    metadata = [
        ("规则版本", content.get("version", "")),
        ("适用地区", content.get("jurisdiction", "")),
        ("复核状态", _review_status_label(content.get("review_status", ""))),
        (
            "起始节点",
            node_labels.get(str(content.get("start_node", "")), content.get("start_node", "")),
        ),
        (
            "阶段",
            "、".join(
                stage_labels.get(str(stage.get("key", "")), str(stage.get("key", "")))
                for stage in content.get("stages", [])
            ),
        ),
    ]
    for label, value in metadata:
        row = table.add_row().cells
        row[0].text = label
        row[1].text = str(value or "")


def _set_table_header(table: Table, values: list[str]) -> None:
    for index, value in enumerate(values):
        table.rows[0].cells[index].text = value


def _option_count(content: dict[str, Any]) -> int:
    return sum(
        len(node.get("options", []))
        for node in content.get("nodes", {}).values()
    )


def _requirement_label(requirement: dict[str, Any]) -> str:
    labels = {
        "always": "始终可用",
        "evidence_ready": "证据已满足",
        "lawyer_assigned": "律师已分配",
    }
    label = labels.get(str(requirement.get("type", "")), str(requirement.get("type", "")))
    message = str(requirement.get("message") or "").strip()
    return f"{label}（{message}）" if message else label


def _node_labels(
    content: dict[str, Any],
    stage_labels: dict[str, str],
) -> dict[str, str]:
    nodes = content.get("nodes", {})
    totals: dict[str, int] = {}
    for node in nodes.values():
        stage = str(node.get("stage", ""))
        totals[stage] = totals.get(stage, 0) + 1
    result: dict[str, str] = {}
    counts: dict[str, int] = {}
    for index, (node_id, node) in enumerate(nodes.items(), start=1):
        label = str(node.get("label") or "").strip()
        if not label:
            stage = str(node.get("stage", ""))
            counts[stage] = counts.get(stage, 0) + 1
            stage_label = stage_labels.get(stage, "流程")
            label = (
                stage_label
                if totals.get(stage, 0) == 1
                else f"{stage_label}节点{counts[stage]}"
            )
        result[str(node_id)] = label or f"流程节点 {index}"
    return result


def _review_status_label(status: Any) -> str:
    labels = {
        "draft": "草稿",
        "pending_review": "待复核",
        "approved": "已批准",
        "rejected": "已驳回",
        "published": "已发布",
        "retired": "已停用",
    }
    return labels.get(str(status), str(status))
