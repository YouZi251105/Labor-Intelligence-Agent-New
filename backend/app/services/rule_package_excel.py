from __future__ import annotations

import re
from io import BytesIO
from math import floor
from typing import Any
from zipfile import BadZipFile

from openpyxl import Workbook, load_workbook
from openpyxl.cell.cell import Cell
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side
from openpyxl.utils import get_column_letter
from openpyxl.utils.exceptions import InvalidFileException
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.properties import PageSetupProperties
from openpyxl.worksheet.worksheet import Worksheet

from app.schemas.workflow_rules import WORKFLOW_ID_PATTERN

SHEET_GUIDE = "填写说明"
SHEET_BASE = "基础信息"
SHEET_STAGES = "案件阶段"
SHEET_NODES = "流程节点"
SHEET_PATHS = "处理路径"
SHEET_REQUIREMENTS = "前置条件"
SHEET_DEADLINES = "期限规则"
SHEET_SYSTEM = "系统信息"
SHEET_DICTIONARY = "数据字典"

SHEET_ORDER = [
    SHEET_GUIDE,
    SHEET_BASE,
    SHEET_STAGES,
    SHEET_NODES,
    SHEET_PATHS,
    SHEET_REQUIREMENTS,
    SHEET_DEADLINES,
    SHEET_SYSTEM,
    SHEET_DICTIONARY,
]

DATA_SHEETS = [
    SHEET_BASE,
    SHEET_STAGES,
    SHEET_NODES,
    SHEET_PATHS,
    SHEET_REQUIREMENTS,
    SHEET_DEADLINES,
    SHEET_SYSTEM,
]

HEADERS: dict[str, list[str]] = {
    SHEET_BASE: ["填写项目", "填写内容", "填写说明"],
    SHEET_STAGES: ["阶段名称", "阶段说明"],
    SHEET_NODES: ["节点名称", "所属阶段", "节点类型", "横坐标", "纵坐标"],
    SHEET_PATHS: [
        "起始节点",
        "顺序",
        "处理选项名称",
        "选项说明",
        "去向节点",
        "选择结果",
        "下一步操作",
    ],
    SHEET_REQUIREMENTS: ["起始节点", "处理选项名称", "条件类型", "提示文案"],
    SHEET_DEADLINES: [
        "起始节点",
        "处理选项名称",
        "期限标题",
        "期限说明",
        "法律依据",
        "起算事件",
        "计算方式",
        "复核状态",
    ],
    SHEET_SYSTEM: ["配置项", "值"],
}

BASE_FIELDS = [
    ("规则版本", "version", "例如：2026.11.1"),
    ("适用地区", "jurisdiction", "例如：中国"),
    ("起始节点名称", "start_node_name", "必须与流程节点中的某一节点名称一致"),
    ("免责声明", "disclaimer", "向用户展示的免责声明"),
]

BLOCK_TYPE_OPTIONS = {
    "阶段": "stage",
    "选择": "decision",
    "证据条件": "evidence_gate",
    "律师条件": "lawyer_gate",
    "结束": "end",
}
REQUIREMENT_OPTIONS = {
    "始终可用": "always",
    "证据已满足": "evidence_ready",
    "律师已分配": "lawyer_assigned",
}
CALCULATION_OPTIONS = {
    "人工复核": "manual_review_required",
}
REVIEW_STATUS_OPTIONS = {
    "草稿": "draft",
    "待复核": "pending_review",
    "已批准": "approved",
    "已发布": "published",
    "已停用": "retired",
}

MAX_DATA_ROWS = 2_000
MAX_SHEETS = 12
PREFORMATTED_ROWS = 100

HEADER_FILL = PatternFill("solid", fgColor="9E1B32")
HEADER_FONT = Font(name="Arial", size=11, bold=True, color="FFFFFF")
BODY_FONT = Font(name="Arial", size=11, color="222222")
INPUT_FILL = PatternFill("solid", fgColor="FFF2F2")
NOTE_FILL = PatternFill("solid", fgColor="F7F7F7")
THIN_BORDER = Border(bottom=Side(style="thin", color="D9D9D9"))


class RulePackageExcelError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


def export_rule_package_excel(content: dict[str, Any]) -> bytes:
    workbook = Workbook()
    workbook.remove(workbook.active)
    workbook.properties.title = "劳务通规则包配置"
    workbook.properties.subject = "面向非技术人员的案件流程配置"
    workbook.properties.creator = "Labor Intelligence Agent"

    guide = workbook.create_sheet(SHEET_GUIDE)
    _write_guide(guide)

    stage_names = _stage_name_map(content)
    node_names = _node_name_map(content, stage_names)

    base = workbook.create_sheet(SHEET_BASE)
    _write_base(base, content, node_names)
    _style_table(base, len(HEADERS[SHEET_BASE]), input_columns={2})

    stages = workbook.create_sheet(SHEET_STAGES)
    _write_table(
        stages,
        HEADERS[SHEET_STAGES],
        [
            [
                stage.get("label") or stage_names[stage.get("key", "")],
                stage.get("description", ""),
            ]
            for stage in content.get("stages", [])
        ],
    )
    _style_table(stages, len(HEADERS[SHEET_STAGES]), input_columns={1, 2})

    nodes = workbook.create_sheet(SHEET_NODES)
    designer_blocks = (content.get("designer") or {}).get("blocks") or {}
    node_rows: list[list[Any]] = []
    for index, (node_id, node) in enumerate(content.get("nodes", {}).items()):
        block = designer_blocks.get(node_id) or {}
        position = block.get("position") or _default_position(index)
        block_type = block.get("block_type") or _infer_block_type(node)
        node_rows.append(
            [
                node_names[node_id],
                stage_names.get(node.get("stage", ""), node.get("stage", "")),
                _display_enum(block_type, BLOCK_TYPE_OPTIONS),
                position.get("x", ""),
                position.get("y", ""),
            ]
        )
    _write_table(nodes, HEADERS[SHEET_NODES], node_rows)
    _style_table(nodes, len(HEADERS[SHEET_NODES]), input_columns=set(range(1, 6)))
    _add_list_validation(nodes, "C", BLOCK_TYPE_OPTIONS)

    path_rows: list[list[Any]] = []
    requirement_rows: list[list[Any]] = []
    deadline_rows: list[list[Any]] = []
    for node_id, node in content.get("nodes", {}).items():
        source_name = node_names[node_id]
        option_names = _option_name_map(node)
        for order, option in enumerate(node.get("options", []), start=1):
            option_name = option_names[option.get("id", "")]
            path_rows.append(
                [
                    source_name,
                    order,
                    option_name,
                    option.get("description", ""),
                    node_names.get(option.get("target_node", ""), ""),
                    option.get("outcome", ""),
                    option.get("next_step", ""),
                ]
            )
            for requirement in option.get("requirements", []):
                requirement_rows.append(
                    [
                        source_name,
                        option_name,
                        _display_enum(requirement.get("type"), REQUIREMENT_OPTIONS),
                        requirement.get("message", ""),
                    ]
                )
            for deadline in option.get("deadlines", []):
                deadline_rows.append(
                    [
                        source_name,
                        option_name,
                        deadline.get("title", ""),
                        deadline.get("description", ""),
                        deadline.get("basis", ""),
                        deadline.get("start_event", ""),
                        _display_enum(
                            deadline.get("calculation"),
                            CALCULATION_OPTIONS,
                        ),
                        _display_enum(
                            deadline.get("review_status"),
                            REVIEW_STATUS_OPTIONS,
                        ),
                    ]
                )

    paths = workbook.create_sheet(SHEET_PATHS)
    _write_table(paths, HEADERS[SHEET_PATHS], path_rows)
    _style_table(paths, len(HEADERS[SHEET_PATHS]), input_columns=set(range(1, 8)))

    requirements = workbook.create_sheet(SHEET_REQUIREMENTS)
    _write_table(requirements, HEADERS[SHEET_REQUIREMENTS], requirement_rows)
    _style_table(
        requirements,
        len(HEADERS[SHEET_REQUIREMENTS]),
        input_columns={1, 2, 3, 4},
    )
    _add_list_validation(requirements, "C", REQUIREMENT_OPTIONS)

    deadlines = workbook.create_sheet(SHEET_DEADLINES)
    _write_table(deadlines, HEADERS[SHEET_DEADLINES], deadline_rows)
    _style_table(
        deadlines,
        len(HEADERS[SHEET_DEADLINES]),
        input_columns=set(range(1, 9)),
    )
    _add_list_validation(deadlines, "G", CALCULATION_OPTIONS)
    _add_list_validation(deadlines, "H", REVIEW_STATUS_OPTIONS)

    system = workbook.create_sheet(SHEET_SYSTEM)
    _write_table(
        system,
        HEADERS[SHEET_SYSTEM],
        [
            ["规则包标识", content.get("package_id", "cn-labor-workflow")],
            ["结构版本", content.get("schema_version", 1)],
            [
                "复核状态",
                _display_enum(
                    content.get("review_status", "draft"),
                    REVIEW_STATUS_OPTIONS,
                ),
            ],
        ],
    )
    _style_table(system, 2, input_columns=set())
    system.sheet_state = "hidden"

    dictionary = workbook.create_sheet(SHEET_DICTIONARY)
    dictionary_rows = [
        ["节点类型", "阶段"],
        ["节点类型", "选择"],
        ["节点类型", "证据条件"],
        ["节点类型", "律师条件"],
        ["节点类型", "结束"],
        ["条件类型", "始终可用"],
        ["条件类型", "证据已满足"],
        ["条件类型", "律师已分配"],
        ["计算方式", "人工复核"],
        ["复核状态", "草稿"],
        ["复核状态", "待复核"],
        ["复核状态", "已批准"],
        ["复核状态", "已发布"],
        ["复核状态", "已停用"],
    ]
    _write_table(dictionary, ["字段组", "可填写值"], dictionary_rows)
    _style_table(dictionary, 2, input_columns=set())
    dictionary.sheet_state = "hidden"

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def import_rule_package_excel(data: bytes) -> dict[str, Any]:
    try:
        workbook = load_workbook(BytesIO(data), data_only=False)
    except (BadZipFile, InvalidFileException, KeyError, OSError) as error:
        raise RulePackageExcelError(["工作簿无法读取，请重新下载最新版 .xlsx 模板"]) from error

    errors: list[str] = []
    if len(workbook.sheetnames) > MAX_SHEETS:
        raise RulePackageExcelError([f"工作簿包含过多工作表（最多 {MAX_SHEETS} 个）"])

    errors.extend(
        f"未允许的工作表：{name}"
        for name in workbook.sheetnames
        if name not in SHEET_ORDER
    )
    missing_sheets = [name for name in SHEET_ORDER if name not in workbook.sheetnames]
    if missing_sheets:
        raise RulePackageExcelError([f"缺少工作表：{name}" for name in missing_sheets])

    for sheet_name in DATA_SHEETS:
        sheet = workbook[sheet_name]
        if sheet.max_row - 1 > MAX_DATA_ROWS:
            errors.append(f"{sheet_name}：有效数据不能超过 {MAX_DATA_ROWS} 行")
        errors.extend(
            f"{sheet_name}!{merged_range}：不允许使用合并单元格"
            for merged_range in sheet.merged_cells.ranges
        )
        _validate_headers(sheet, HEADERS[sheet_name], errors)
    if errors:
        raise RulePackageExcelError(errors)

    base_records = _read_records(workbook[SHEET_BASE], errors)
    system_records = _read_records(workbook[SHEET_SYSTEM], errors)
    stage_records = _read_records(workbook[SHEET_STAGES], errors)
    node_records = _read_records(workbook[SHEET_NODES], errors)
    path_records = _read_records(workbook[SHEET_PATHS], errors)
    requirement_records = _read_records(workbook[SHEET_REQUIREMENTS], errors)
    deadline_records = _read_records(workbook[SHEET_DEADLINES], errors)

    base = _build_base(base_records, errors)
    system = _build_system(system_records, errors)
    stages, stage_name_to_key = _build_stages(stage_records, errors)
    nodes, node_name_to_id, block_inputs = _build_nodes(
        node_records,
        stage_name_to_key,
        errors,
    )
    option_lookup = _build_paths(
        path_records,
        node_name_to_id,
        nodes,
        errors,
    )
    _attach_requirements(requirement_records, option_lookup, errors)
    _attach_deadlines(deadline_records, option_lookup, errors)
    _fill_default_requirements(option_lookup)

    if errors:
        raise RulePackageExcelError(errors)

    designer_blocks: dict[str, dict[str, Any]] = {}
    for index, (node_id, node) in enumerate(nodes.items()):
        block_type, position = block_inputs[node_id]
        designer_blocks[node_id] = {
            "id": node_id,
            "block_type": block_type or _infer_block_type(node),
            "position": position or _default_position(index),
        }

    return {
        "schema_version": system["schema_version"],
        "package_id": system["package_id"],
        "version": base["version"],
        "jurisdiction": base["jurisdiction"],
        "review_status": system["review_status"],
        "disclaimer": base["disclaimer"],
        "start_node": node_name_to_id[base["start_node_name"]],
        "stages": stages,
        "nodes": nodes,
        "designer": {"version": 1, "blocks": designer_blocks},
    }


def _write_guide(sheet: Worksheet) -> None:
    sheet.sheet_view.showGridLines = False
    sheet.column_dimensions["A"].width = 24
    sheet.column_dimensions["B"].width = 78
    sheet["A1"] = "劳务通规则包填写说明"
    sheet["A1"].font = Font(name="Arial", size=18, bold=True, color="9E1B32")
    sheet.merge_cells("A1:B1")
    sheet["A3"] = "填写步骤"
    sheet["A3"].font = Font(name="Arial", size=12, bold=True)
    steps = [
        "先填写“基础信息”，所有内容都用中文名称表达。",
        "在“案件阶段”填写阶段名称和说明，例如“识别问题 / 整理证据”。",
        "在“流程节点”填写节点名称、所属阶段、节点类型和画布位置。",
        "在“处理路径”填写从哪个节点出发、用户看到什么选项、下一步去哪个节点。",
        "需要条件或期限时，在对应工作表中选择“起始节点”和“处理选项名称”进行关联。",
        "保存为 .xlsx 后导入。系统会自动生成内部编号，不需要填写任何 ID。",
    ]
    for index, text in enumerate(steps, start=4):
        sheet.cell(index, 1, f"步骤 {index - 3}")
        sheet.cell(index, 2, text)

    sheet["A12"] = "颜色规则"
    sheet["A12"].font = Font(name="Arial", size=12, bold=True)
    sheet["A13"] = "浅红色单元格"
    sheet["A13"].fill = INPUT_FILL
    sheet["B13"] = "需要填写或修改的内容。"
    sheet["A14"] = "深红色表头"
    sheet["A14"].fill = HEADER_FILL
    sheet["A14"].font = HEADER_FONT
    sheet["B14"] = "字段名称固定，请勿修改列名或列顺序。"

    sheet["A16"] = "填写示例"
    sheet["A16"].font = Font(name="Arial", size=12, bold=True)
    examples = [
        ["起始节点名称", "识别问题"],
        ["阶段名称", "识别问题"],
        ["节点名称", "识别问题"],
        ["处理选项名称", "先整理证据"],
        ["去向节点", "整理证据"],
    ]
    for index, (label, value) in enumerate(examples, start=17):
        sheet.cell(index, 1, label)
        sheet.cell(index, 2, value)

    sheet["A23"] = (
        "注意：普通填写区域不包含 ID、英文枚举或系统编号。"
        "公式、宏、外部链接、合并单元格和自行新增字段不会被导入。"
    )
    sheet["A23"].alignment = Alignment(wrap_text=True)
    sheet["A23"].fill = NOTE_FILL
    sheet.merge_cells("A23:B23")
    sheet.protection.sheet = True
    _configure_print_layout(sheet, "A1:B23")


def _write_base(
    sheet: Worksheet,
    content: dict[str, Any],
    node_names: dict[str, str],
) -> None:
    values = {
        "version": content.get("version", ""),
        "jurisdiction": content.get("jurisdiction", ""),
        "start_node_name": node_names.get(content.get("start_node", ""), ""),
        "disclaimer": content.get("disclaimer", ""),
    }
    _write_table(
        sheet,
        HEADERS[SHEET_BASE],
        [[label, values[key], description] for label, key, description in BASE_FIELDS],
    )


def _write_table(sheet: Worksheet, headers: list[str], rows: list[list[Any]]) -> None:
    sheet.append(headers)
    for row in rows:
        sheet.append(row)


def _style_table(sheet: Worksheet, column_count: int, *, input_columns: set[int]) -> None:
    sheet.freeze_panes = "A2"
    sheet.sheet_view.showGridLines = False
    for column in range(1, column_count + 1):
        cell = sheet.cell(1, column)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER
        sheet.column_dimensions[get_column_letter(column)].width = _column_width(column)
    sheet.row_dimensions[1].height = 26

    populated_rows = sheet.max_row
    style_rows = min(MAX_DATA_ROWS, max(populated_rows, PREFORMATTED_ROWS))
    for row in sheet.iter_rows(min_row=2, max_row=style_rows, max_col=column_count):
        for cell in row:
            cell.font = BODY_FONT
            cell.border = THIN_BORDER
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.protection = Protection(locked=cell.column not in input_columns)
            if cell.row <= max(populated_rows, 2) and cell.column in input_columns:
                cell.fill = INPUT_FILL
    if populated_rows > 1:
        sheet.auto_filter.ref = f"A1:{get_column_letter(column_count)}{populated_rows}"
    sheet.protection.sheet = True
    _configure_print_layout(
        sheet,
        f"A1:{get_column_letter(column_count)}{max(populated_rows, 1)}",
    )


def _add_list_validation(
    sheet: Worksheet,
    column: str,
    values: dict[str, str],
    *,
    start_row: int = 2,
    end_row: int = MAX_DATA_ROWS,
) -> None:
    validation = DataValidation(
        type="list",
        formula1='"' + ",".join(values) + '"',
        allow_blank=True,
    )
    validation.error = "请从下拉列表中选择允许的值"
    validation.errorTitle = "输入值不在允许范围"
    validation.prompt = "请选择表格提供的值"
    validation.promptTitle = "受约束字段"
    validation.showErrorMessage = True
    validation.showInputMessage = True
    sheet.add_data_validation(validation)
    validation.add(f"{column}{start_row}:{column}{end_row}")


def _validate_headers(sheet: Worksheet, expected: list[str], errors: list[str]) -> None:
    actual = [
        str(sheet.cell(1, index).value or "").strip()
        for index in range(1, len(expected) + 1)
    ]
    if actual != expected:
        errors.append(
            f"{sheet.title}!A1：表头不一致，请重新下载最新模板。"
            f"应为 {', '.join(expected)}"
        )


def _read_records(sheet: Worksheet, errors: list[str]) -> list[dict[str, Any]]:
    headers = HEADERS.get(sheet.title)
    if headers is None:
        return []
    records: list[dict[str, Any]] = []
    for row_index, row in enumerate(
        sheet.iter_rows(min_row=2, max_row=min(sheet.max_row, MAX_DATA_ROWS + 1)),
        start=2,
    ):
        values: dict[str, str] = {}
        for column_index, header in enumerate(headers, start=1):
            cell = row[column_index - 1]
            if _cell_has_formula(cell):
                coordinate = f"{get_column_letter(column_index)}{row_index}"
                errors.append(f"{sheet.title}!{coordinate}：不允许使用公式")
                values[header] = ""
                continue
            values[header] = _cell_text(cell)
        if any(values.values()):
            records.append({"row": row_index, "value": values})
    return records


def _build_base(
    records: list[dict[str, Any]],
    errors: list[str],
) -> dict[str, str]:
    values = {record["value"]["填写项目"]: record for record in records}
    result: dict[str, str] = {}
    for label, key, _ in BASE_FIELDS:
        record = values.get(label)
        if record is None:
            errors.append(f"基础信息!A2：缺少“{label}”")
            continue
        value = record["value"]["填写内容"]
        if not value:
            errors.append(f"基础信息!B{record['row']}：{label}不能为空")
        result[key] = value
    return result


def _build_system(
    records: list[dict[str, Any]],
    errors: list[str],
) -> dict[str, Any]:
    values = {record["value"]["配置项"]: record for record in records}
    package = values.get("规则包标识")
    schema = values.get("结构版本")
    review = values.get("复核状态")
    if package is None:
        errors.append("系统信息!A2：缺少规则包标识，请重新下载模板")
    if schema is None:
        errors.append("系统信息!A3：缺少结构版本，请重新下载模板")
    if review is None:
        errors.append("系统信息!A4：缺少复核状态，请重新下载模板")

    package_id = package["value"]["值"] if package else ""
    if package_id and re.fullmatch(WORKFLOW_ID_PATTERN, package_id) is None:
        errors.append("系统信息!B2：规则包标识格式无效，请重新下载模板")
    try:
        schema_version = int(schema["value"]["值"]) if schema else 0
    except ValueError:
        schema_version = 0
    review_status = (
        _normalize_enum(
            review["value"]["值"],
            REVIEW_STATUS_OPTIONS,
            f"系统信息!B{review['row']}",
            errors,
        )
        if review
        else "draft"
    )
    return {
        "package_id": package_id,
        "schema_version": schema_version,
        "review_status": review_status,
    }


def _build_stages(
    records: list[dict[str, Any]],
    errors: list[str],
) -> tuple[list[dict[str, str]], dict[str, str]]:
    stages: list[dict[str, str]] = []
    name_to_key: dict[str, str] = {}
    for index, record in enumerate(records, start=1):
        value = record["value"]
        name = value["阶段名称"]
        if not name:
            errors.append(f"案件阶段!A{record['row']}：阶段名称不能为空")
            continue
        if name in name_to_key:
            errors.append(f"案件阶段!A{record['row']}：阶段名称“{name}”重复")
            continue
        key = f"stage-{index}"
        name_to_key[name] = key
        stages.append(
            {
                "key": key,
                "label": name,
                "description": value["阶段说明"],
            }
        )
    if not stages:
        errors.append("案件阶段!A2：至少需要填写一个阶段")
    return stages, name_to_key


def _build_nodes(
    records: list[dict[str, Any]],
    stage_name_to_key: dict[str, str],
    errors: list[str],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, str],
    dict[str, tuple[str, dict[str, float] | None]],
]:
    nodes: dict[str, dict[str, Any]] = {}
    name_to_id: dict[str, str] = {}
    block_inputs: dict[str, tuple[str, dict[str, float] | None]] = {}
    for index, record in enumerate(records, start=1):
        value = record["value"]
        name = value["节点名称"]
        if not name:
            errors.append(f"流程节点!A{record['row']}：节点名称不能为空")
            continue
        if name in name_to_id:
            errors.append(f"流程节点!A{record['row']}：节点名称“{name}”重复")
            continue
        stage_name = value["所属阶段"]
        if stage_name not in stage_name_to_key:
            errors.append(f"流程节点!B{record['row']}：所属阶段“{stage_name}”不存在")
            continue
        node_id = f"node-{index}"
        name_to_id[name] = node_id
        nodes[node_id] = {
            "stage": stage_name_to_key[stage_name],
            "label": name,
            "options": [],
        }
        block_type = _normalize_enum(
            value["节点类型"],
            BLOCK_TYPE_OPTIONS,
            f"流程节点!C{record['row']}",
            errors,
        )
        position = _parse_position(value, record["row"], errors)
        block_inputs[node_id] = (block_type, position)
    if not nodes:
        errors.append("流程节点!A2：至少需要填写一个节点")
    return nodes, name_to_id, block_inputs


def _build_paths(
    records: list[dict[str, Any]],
    node_name_to_id: dict[str, str],
    nodes: dict[str, dict[str, Any]],
    errors: list[str],
) -> dict[tuple[str, str], tuple[str, str, dict[str, Any]]]:
    option_lookup: dict[tuple[str, str], tuple[str, str, dict[str, Any]]] = {}
    orders: dict[str, set[int]] = {}
    indexed: list[tuple[str, int, dict[str, Any]]] = []
    for index, record in enumerate(records, start=1):
        value = record["value"]
        row = record["row"]
        required_fields = {
            "起始节点": ("A", "起始节点"),
            "顺序": ("B", "顺序"),
            "处理选项名称": ("C", "处理选项名称"),
            "选项说明": ("D", "选项说明"),
            "去向节点": ("E", "去向节点"),
            "选择结果": ("F", "选择结果"),
            "下一步操作": ("G", "下一步操作"),
        }
        for field, (column, label) in required_fields.items():
            if not value[field]:
                errors.append(f"处理路径!{column}{row}：{label}不能为空")

        source_name = value["起始节点"]
        target_name = value["去向节点"]
        source_id = node_name_to_id.get(source_name)
        target_id = node_name_to_id.get(target_name)
        if source_id is None:
            errors.append(f"处理路径!A{row}：起始节点“{source_name}”不存在")
        if target_id is None:
            errors.append(f"处理路径!E{row}：去向节点“{target_name}”不存在")
        try:
            order = int(value["顺序"])
            if order < 1:
                raise ValueError
        except ValueError:
            errors.append(f"处理路径!B{row}：顺序必须是正整数")
            continue
        if source_name and order in orders.setdefault(source_name, set()):
            errors.append(f"处理路径!B{row}：节点“{source_name}”下的顺序 {order} 重复")
        orders.setdefault(source_name, set()).add(order)

        key = (source_name, value["处理选项名称"])
        if key in option_lookup:
            errors.append(
                f"处理路径!C{row}：节点“{source_name}”下的处理选项名称重复"
            )
            continue

        if source_id is None or target_id is None:
            continue
        option = {
            "id": f"path-{index}",
            "label": value["处理选项名称"],
            "description": value["选项说明"],
            "target_stage": nodes[target_id]["stage"],
            "target_node": target_id,
            "outcome": value["选择结果"],
            "next_step": value["下一步操作"],
            "requirements": [],
            "deadlines": [],
        }
        option_lookup[key] = (source_id, option["id"], option)
        indexed.append((source_id, order, option))

    for source_id, _, option in sorted(indexed, key=lambda item: (item[0], item[1])):
        nodes[source_id]["options"].append(option)
    return option_lookup


def _attach_requirements(
    records: list[dict[str, Any]],
    option_lookup: dict[tuple[str, str], tuple[str, str, dict[str, Any]]],
    errors: list[str],
) -> None:
    for record in records:
        value = record["value"]
        key = (value["起始节点"], value["处理选项名称"])
        entry = option_lookup.get(key)
        if entry is None:
            errors.append(
                f"前置条件!A{record['row']}：找不到对应的节点和处理选项"
            )
            continue
        requirement_type = _normalize_enum(
            value["条件类型"],
            REQUIREMENT_OPTIONS,
            f"前置条件!C{record['row']}",
            errors,
        )
        requirement = {"type": requirement_type}
        if value["提示文案"]:
            requirement["message"] = value["提示文案"]
        entry[2]["requirements"].append(requirement)


def _attach_deadlines(
    records: list[dict[str, Any]],
    option_lookup: dict[tuple[str, str], tuple[str, str, dict[str, Any]]],
    errors: list[str],
) -> None:
    for index, record in enumerate(records, start=1):
        value = record["value"]
        key = (value["起始节点"], value["处理选项名称"])
        entry = option_lookup.get(key)
        if entry is None:
            errors.append(
                f"期限规则!A{record['row']}：找不到对应的节点和处理选项"
            )
            continue
        required_fields = {
            "期限标题": "C",
            "期限说明": "D",
            "计算方式": "G",
            "复核状态": "H",
        }
        for field, column in required_fields.items():
            if not value[field]:
                errors.append(f"期限规则!{column}{record['row']}：{field}不能为空")
        entry[2]["deadlines"].append(
            {
                "id": f"deadline-{index}",
                "title": value["期限标题"],
                "description": value["期限说明"],
                "basis": value["法律依据"],
                "start_event": value["起算事件"],
                "calculation": _normalize_enum(
                    value["计算方式"],
                    CALCULATION_OPTIONS,
                    f"期限规则!G{record['row']}",
                    errors,
                ),
                "review_status": _normalize_enum(
                    value["复核状态"],
                    REVIEW_STATUS_OPTIONS,
                    f"期限规则!H{record['row']}",
                    errors,
                ),
            }
        )


def _fill_default_requirements(
    option_lookup: dict[tuple[str, str], tuple[str, str, dict[str, Any]]],
) -> None:
    for _, _, option in option_lookup.values():
        if not option["requirements"]:
            option["requirements"] = [{"type": "always"}]


def _parse_position(
    value: dict[str, str],
    row: int,
    errors: list[str],
) -> dict[str, float] | None:
    if not value["横坐标"] and not value["纵坐标"]:
        return None
    try:
        return {
            "x": float(value["横坐标"]),
            "y": float(value["纵坐标"]),
        }
    except ValueError:
        errors.append(f"流程节点!D{row}：横坐标和纵坐标必须是数字")
        return None


def _cell_has_formula(cell: Cell) -> bool:
    return cell.data_type == "f" or (
        isinstance(cell.value, str) and cell.value.startswith("=")
    )


def _cell_text(cell: Cell) -> str:
    if cell.value is None:
        return ""
    return str(cell.value).strip()


def _normalize_enum(
    value: str,
    options: dict[str, str],
    location: str,
    errors: list[str],
) -> str:
    if value in options.values():
        return value
    if value in options:
        return options[value]
    errors.append(f"{location}：值“{value or '(空)'}”不在允许范围内")
    return value


def _display_enum(value: Any, options: dict[str, str]) -> str:
    for label, internal in options.items():
        if value == internal:
            return label
    return str(value or "")


def _stage_name_map(content: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for index, stage in enumerate(content.get("stages", []), start=1):
        key = str(stage.get("key", ""))
        result[key] = str(stage.get("label") or f"阶段 {index}")
    return result


def _node_name_map(
    content: dict[str, Any],
    stage_names: dict[str, str],
) -> dict[str, str]:
    result: dict[str, str] = {}
    used: set[str] = set()
    stage_counts: dict[str, int] = {}
    stage_totals: dict[str, int] = {}
    for node in content.get("nodes", {}).values():
        stage = str(node.get("stage", ""))
        stage_totals[stage] = stage_totals.get(stage, 0) + 1
    for node_id, node in content.get("nodes", {}).items():
        label = str(node.get("label") or "").strip()
        if not label:
            stage = str(node.get("stage", ""))
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
            stage_label = stage_names.get(stage, "流程")
            label = (
                stage_label
                if stage_totals.get(stage, 0) == 1
                else f"{stage_label}节点{stage_counts[stage]}"
            )
        candidate = label
        suffix = 2
        while candidate in used:
            candidate = f"{label}{suffix}"
            suffix += 1
        used.add(candidate)
        result[node_id] = candidate
    return result


def _option_name_map(node: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    used: set[str] = set()
    for index, option in enumerate(node.get("options", []), start=1):
        label = str(option.get("label") or f"处理选项 {index}").strip()
        candidate = label
        suffix = 2
        while candidate in used:
            candidate = f"{label}{suffix}"
            suffix += 1
        used.add(candidate)
        result[str(option.get("id", ""))] = candidate
    return result


def _infer_block_type(node: dict[str, Any]) -> str:
    options = node.get("options", [])
    if not options:
        return "end"
    requirements = [
        requirement.get("type")
        for option in options
        for requirement in option.get("requirements", [])
    ]
    if "evidence_ready" in requirements:
        return "evidence_gate"
    if "lawyer_assigned" in requirements:
        return "lawyer_gate"
    if len(options) > 1:
        return "decision"
    return "stage"


def _default_position(index: int) -> dict[str, float]:
    return {
        "x": float(30 + (index % 2) * 360),
        "y": float(40 + floor(index / 2) * 230),
    }


def _column_width(column: int) -> float:
    widths = [22, 24, 24, 30, 30, 28, 32, 28]
    return widths[column - 1] if column <= len(widths) else 20


def _configure_print_layout(sheet: Worksheet, print_area: str) -> None:
    sheet.print_area = print_area
    sheet.print_title_rows = "1:1"
    if sheet.sheet_properties.pageSetUpPr is None:
        sheet.sheet_properties.pageSetUpPr = PageSetupProperties()
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.page_margins.left = 0.3
    sheet.page_margins.right = 0.3
    sheet.page_margins.top = 0.5
    sheet.page_margins.bottom = 0.5
