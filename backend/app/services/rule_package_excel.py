from __future__ import annotations

import re
from io import BytesIO
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
SHEET_STAGES = "阶段"
SHEET_NODES = "节点"
SHEET_PATHS = "路径"
SHEET_REQUIREMENTS = "前置条件"
SHEET_DEADLINES = "期限规则"
SHEET_DICTIONARY = "数据字典"

SHEET_ORDER = [
    SHEET_GUIDE,
    SHEET_BASE,
    SHEET_STAGES,
    SHEET_NODES,
    SHEET_PATHS,
    SHEET_REQUIREMENTS,
    SHEET_DEADLINES,
    SHEET_DICTIONARY,
]

HEADERS: dict[str, list[str]] = {
    SHEET_BASE: ["字段", "值", "说明"],
    SHEET_STAGES: ["阶段ID", "显示名称", "说明"],
    SHEET_NODES: [
        "节点ID",
        "所属阶段",
        "节点名称",
        "积木类型",
        "横坐标",
        "纵坐标",
    ],
    SHEET_PATHS: [
        "路径ID",
        "来源节点ID",
        "顺序",
        "选项名称",
        "选项说明",
        "目标节点ID",
        "目标阶段",
        "结果说明",
        "下一步",
    ],
    SHEET_REQUIREMENTS: ["路径ID", "条件类型", "提示文案"],
    SHEET_DEADLINES: [
        "路径ID",
        "期限ID",
        "标题",
        "说明",
        "法律依据",
        "起算事件",
        "计算方式",
        "复核状态",
    ],
}

BASE_FIELDS = [
    ("schema_version", "结构版本，固定填写 1"),
    ("package_id", "规则包唯一标识"),
    ("version", "本次规则版本号，例如 2026.11.1"),
    ("jurisdiction", "适用地区，例如 CN"),
    ("review_status", "当前内容复核状态"),
    ("disclaimer", "面向用户的免责声明"),
    ("start_node", "流程起始节点ID"),
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
THIN_BORDER = Border(
    bottom=Side(style="thin", color="D9D9D9"),
)


class RulePackageExcelError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


def export_rule_package_excel(content: dict[str, Any]) -> bytes:
    workbook = Workbook()
    workbook.remove(workbook.active)
    workbook.properties.title = "劳务通规则包填写模板"
    workbook.properties.subject = "版本化案件流程规则"
    workbook.properties.creator = "Labor Intelligence Agent"

    guide = workbook.create_sheet(SHEET_GUIDE)
    _write_guide(guide)

    base = workbook.create_sheet(SHEET_BASE)
    _write_base(base, content)
    _style_table(base, len(HEADERS[SHEET_BASE]), input_columns={2})

    stages = workbook.create_sheet(SHEET_STAGES)
    _write_table(
        stages,
        HEADERS[SHEET_STAGES],
        [
            [stage.get("key", ""), stage.get("label", ""), stage.get("description", "")]
            for stage in content.get("stages", [])
        ],
    )
    _style_table(stages, len(HEADERS[SHEET_STAGES]), input_columns={1, 2, 3})

    nodes = workbook.create_sheet(SHEET_NODES)
    designer_blocks = (content.get("designer") or {}).get("blocks") or {}
    node_rows: list[list[Any]] = []
    for node_id, node in content.get("nodes", {}).items():
        block = designer_blocks.get(node_id, {})
        position = block.get("position") or {}
        node_rows.append(
            [
                node_id,
                node.get("stage", ""),
                node.get("label", ""),
                _display_enum(block.get("block_type"), BLOCK_TYPE_OPTIONS),
                position.get("x", ""),
                position.get("y", ""),
            ]
        )
    _write_table(nodes, HEADERS[SHEET_NODES], node_rows)
    _style_table(nodes, len(HEADERS[SHEET_NODES]), input_columns=set(range(1, 7)))
    _add_list_validation(nodes, "D", BLOCK_TYPE_OPTIONS)

    paths = workbook.create_sheet(SHEET_PATHS)
    path_rows: list[list[Any]] = []
    requirement_rows: list[list[Any]] = []
    deadline_rows: list[list[Any]] = []
    for node_id, node in content.get("nodes", {}).items():
        for order, option in enumerate(node.get("options", []), start=1):
            path_rows.append(
                [
                    option.get("id", ""),
                    node_id,
                    order,
                    option.get("label", ""),
                    option.get("description", ""),
                    option.get("target_node", ""),
                    option.get("target_stage", ""),
                    option.get("outcome", ""),
                    option.get("next_step", ""),
                ]
            )
            for requirement in option.get("requirements", []):
                requirement_rows.append(
                    [
                        option.get("id", ""),
                        _display_enum(requirement.get("type"), REQUIREMENT_OPTIONS),
                        requirement.get("message", ""),
                    ]
                )
            for deadline in option.get("deadlines", []):
                deadline_rows.append(
                    [
                        option.get("id", ""),
                        deadline.get("id", ""),
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
    _write_table(paths, HEADERS[SHEET_PATHS], path_rows)
    _style_table(paths, len(HEADERS[SHEET_PATHS]), input_columns=set(range(1, 10)))

    requirements = workbook.create_sheet(SHEET_REQUIREMENTS)
    _write_table(requirements, HEADERS[SHEET_REQUIREMENTS], requirement_rows)
    _style_table(
        requirements,
        len(HEADERS[SHEET_REQUIREMENTS]),
        input_columns={1, 2, 3},
    )
    _add_list_validation(requirements, "B", REQUIREMENT_OPTIONS)

    deadlines = workbook.create_sheet(SHEET_DEADLINES)
    _write_table(deadlines, HEADERS[SHEET_DEADLINES], deadline_rows)
    _style_table(
        deadlines,
        len(HEADERS[SHEET_DEADLINES]),
        input_columns=set(range(1, 9)),
    )
    _add_list_validation(deadlines, "G", CALCULATION_OPTIONS)
    _add_list_validation(deadlines, "H", REVIEW_STATUS_OPTIONS)

    dictionary = workbook.create_sheet(SHEET_DICTIONARY)
    dictionary_rows = [
        ["积木类型", "阶段", "stage"],
        ["积木类型", "选择", "decision"],
        ["积木类型", "证据条件", "evidence_gate"],
        ["积木类型", "律师条件", "lawyer_gate"],
        ["积木类型", "结束", "end"],
        ["条件类型", "始终可用", "always"],
        ["条件类型", "证据已满足", "evidence_ready"],
        ["条件类型", "律师已分配", "lawyer_assigned"],
        ["计算方式", "人工复核", "manual_review_required"],
        ["复核状态", "草稿", "draft"],
        ["复核状态", "待复核", "pending_review"],
        ["复核状态", "已批准", "approved"],
        ["复核状态", "已发布", "published"],
        ["复核状态", "已停用", "retired"],
    ]
    _write_table(dictionary, ["字段组", "可填写值", "系统值"], dictionary_rows)
    _style_table(dictionary, 3, input_columns=set())
    dictionary.sheet_state = "hidden"

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def import_rule_package_excel(data: bytes) -> dict[str, Any]:
    try:
        workbook = load_workbook(BytesIO(data), data_only=False)
    except (BadZipFile, InvalidFileException, KeyError, OSError) as error:
        raise RulePackageExcelError(["工作簿无法读取，请重新下载 .xlsx 模板填写"]) from error

    errors: list[str] = []
    if len(workbook.sheetnames) > MAX_SHEETS:
        raise RulePackageExcelError([f"工作簿包含过多工作表（最多 {MAX_SHEETS} 个）"])
    unexpected_sheets = [
        name for name in workbook.sheetnames if name not in SHEET_ORDER
    ]
    errors.extend(
        f"未允许的工作表：{name}" for name in unexpected_sheets
    )
    missing_sheets = [name for name in SHEET_ORDER if name not in workbook.sheetnames]
    if missing_sheets:
        raise RulePackageExcelError(
            [f"缺少工作表：{name}" for name in missing_sheets]
        )

    data_sheet_names = [
        SHEET_BASE,
        SHEET_STAGES,
        SHEET_NODES,
        SHEET_PATHS,
        SHEET_REQUIREMENTS,
        SHEET_DEADLINES,
    ]
    for sheet_name in data_sheet_names:
        sheet = workbook[sheet_name]
        if sheet.max_row - 1 > MAX_DATA_ROWS:
            errors.append(
                f"{sheet_name}：有效数据不能超过 {MAX_DATA_ROWS} 行"
            )
        errors.extend(
            f"{sheet_name}!{merged_range}：不允许使用合并单元格"
            for merged_range in sheet.merged_cells.ranges
        )
        _validate_headers(workbook[sheet_name], HEADERS[sheet_name], errors)
    if errors:
        raise RulePackageExcelError(errors)

    base_records = _read_records(workbook[SHEET_BASE], errors)
    base: dict[str, str] = {}
    for record in base_records:
        field = record["value"]["字段"]
        if field:
            base[field] = record["value"]["值"]

    required_base = {field for field, _ in BASE_FIELDS}
    missing_base = sorted(required_base - set(base))
    errors.extend(f"基础信息!A{record['row']}：缺少字段 {field}" for field in missing_base)
    errors.extend(
        f"基础信息!B{_base_field_row(base_records, field)}：{field}不能为空"
        for field in required_base
        if field in base and not base[field]
    )
    _check_identifier(
        base.get("package_id", ""),
        f"基础信息!B{_base_field_row(base_records, 'package_id')}",
        "包标识",
        errors,
    )
    _check_identifier(
        base.get("start_node", ""),
        f"基础信息!B{_base_field_row(base_records, 'start_node')}",
        "起始节点",
        errors,
    )

    stage_records = _read_records(workbook[SHEET_STAGES], errors)
    node_records = _read_records(workbook[SHEET_NODES], errors)
    path_records = _read_records(workbook[SHEET_PATHS], errors)
    requirement_records = _read_records(workbook[SHEET_REQUIREMENTS], errors)
    deadline_records = _read_records(workbook[SHEET_DEADLINES], errors)

    stages = _build_stages(stage_records, errors)
    nodes, block_metadata = _build_nodes(node_records, errors)
    options_by_node, option_ids = _build_paths(path_records, nodes, errors)
    requirements_by_path = _build_requirements(requirement_records, errors)
    deadlines_by_path = _build_deadlines(deadline_records, errors)

    unknown_requirement_paths = set(requirements_by_path) - option_ids
    unknown_deadline_paths = set(deadlines_by_path) - option_ids
    errors.extend(
        f"前置条件!A{row['row']}：路径ID {row['value']['路径ID']} 不存在"
        for row in requirement_records
        if row["value"]["路径ID"] in unknown_requirement_paths
    )
    errors.extend(
        f"期限规则!A{row['row']}：路径ID {row['value']['路径ID']} 不存在"
        for row in deadline_records
        if row["value"]["路径ID"] in unknown_deadline_paths
    )

    if errors:
        raise RulePackageExcelError(errors)

    for node_id, options in options_by_node.items():
        for option in options:
            option["requirements"] = requirements_by_path.get(option["id"], [])
            option["deadlines"] = deadlines_by_path.get(option["id"], [])
        nodes[node_id]["options"] = options

    try:
        content: dict[str, Any] = {
            "schema_version": int(base["schema_version"]),
            "package_id": base["package_id"],
            "version": base["version"],
            "jurisdiction": base["jurisdiction"],
            "review_status": _normalize_enum(
                base["review_status"],
                REVIEW_STATUS_OPTIONS,
                f"基础信息!B{_base_field_row(base_records, 'review_status')}",
                errors,
            ),
            "disclaimer": base["disclaimer"],
            "start_node": base["start_node"],
            "stages": stages,
            "nodes": nodes,
        }
    except ValueError:
        errors.append("基础信息!B2：结构版本必须是整数 1")
        raise RulePackageExcelError(errors) from None

    if block_metadata:
        content["designer"] = {
            "version": 1,
            "blocks": block_metadata,
        }
    if errors:
        raise RulePackageExcelError(errors)
    return content


def _write_guide(sheet: Worksheet) -> None:
    sheet.sheet_view.showGridLines = False
    sheet.column_dimensions["A"].width = 24
    sheet.column_dimensions["B"].width = 72
    sheet["A1"] = "劳务通规则包 Excel 填写说明"
    sheet["A1"].font = Font(name="Arial", size=18, bold=True, color="9E1B32")
    sheet.merge_cells("A1:B1")
    sheet["A3"] = "填写步骤"
    sheet["A3"].font = Font(name="Arial", size=12, bold=True)
    steps = [
        ("1", "先填写“基础信息”，版本号必须与已发布版本区分。"),
        ("2", "再填写“阶段”和“节点”，确保阶段ID和节点ID不重复。"),
        ("3", "在“路径”中填写每个节点可选择的去向，目标阶段必须与目标节点一致。"),
        ("4", "需要前置条件或期限时，分别写入对应工作表，并用路径ID关联。"),
        ("5", "保存为 .xlsx 后在管理端导入。系统会再次校验，不会直接绕过审核。"),
    ]
    for index, (number, text) in enumerate(steps, start=4):
        sheet.cell(index, 1, f"步骤 {number}")
        sheet.cell(index, 2, text)

    sheet["A10"] = "颜色与输入规则"
    sheet["A10"].font = Font(name="Arial", size=12, bold=True)
    sheet["A11"] = "浅红色单元格"
    sheet["A11"].fill = INPUT_FILL
    sheet["B11"] = "需要填写或修改的内容。"
    sheet["A12"] = "深红色表头"
    sheet["A12"].fill = HEADER_FILL
    sheet["A12"].font = HEADER_FONT
    sheet["B12"] = "字段名称固定，请勿改动列名或列顺序。"

    sheet["A14"] = "示例"
    sheet["A14"].font = Font(name="Arial", size=12, bold=True)
    example_rows = [
        ["示例路径ID", "start-evidence"],
        ["示例来源节点ID", "intake"],
        ["示例选项名称", "先整理证据"],
        ["示例目标节点ID", "evidence"],
        ["示例目标阶段", "evidence"],
    ]
    for index, (label, value) in enumerate(example_rows, start=15):
        sheet.cell(index, 1, label)
        sheet.cell(index, 2, value)

    sheet["A21"] = (
        "注意：公式、宏、外部链接、合并单元格和自行新增字段不会被导入；"
        "错误会定位到具体工作表和行号。"
    )
    sheet["A21"].alignment = Alignment(wrap_text=True)
    sheet["A21"].fill = NOTE_FILL
    sheet.merge_cells("A21:B21")
    sheet.protection.sheet = True
    _configure_print_layout(sheet, "A1:B21")


def _write_base(sheet: Worksheet, content: dict[str, Any]) -> None:
    rows = []
    for field, description in BASE_FIELDS:
        value = content.get(field, "")
        if field == "review_status":
            value = _display_enum(value, REVIEW_STATUS_OPTIONS)
        rows.append([field, value, description])
    _write_table(sheet, HEADERS[SHEET_BASE], rows)
    _add_list_validation(sheet, "B", REVIEW_STATUS_OPTIONS, start_row=5, end_row=5)


def _write_table(
    sheet: Worksheet,
    headers: list[str],
    rows: list[list[Any]],
) -> None:
    sheet.append(headers)
    for row in rows:
        sheet.append(row)


def _style_table(
    sheet: Worksheet,
    column_count: int,
    *,
    input_columns: set[int],
) -> None:
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
            if row[0].row <= max(populated_rows, 2) and cell.column in input_columns:
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


def _validate_headers(
    sheet: Worksheet,
    expected: list[str],
    errors: list[str],
) -> None:
    actual = [
        str(sheet.cell(1, index).value or "").strip()
        for index in range(1, len(expected) + 1)
    ]
    if actual != expected:
        errors.append(
            f"{sheet.title}!A1：表头不一致，应为 {', '.join(expected)}"
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


def _cell_has_formula(cell: Cell) -> bool:
    return cell.data_type == "f" or (
        isinstance(cell.value, str) and cell.value.startswith("=")
    )


def _cell_text(cell: Cell) -> str:
    if cell.value is None:
        return ""
    return str(cell.value).strip()


def _build_stages(
    records: list[dict[str, Any]],
    errors: list[str],
) -> list[dict[str, str]]:
    stages: list[dict[str, str]] = []
    seen: set[str] = set()
    for record in records:
        value = record["value"]
        key = value["阶段ID"]
        if not key:
            errors.append(f"阶段!A{record['row']}：阶段ID不能为空")
            continue
        _check_identifier(key, f"阶段!A{record['row']}", "阶段", errors)
        if not value["显示名称"]:
            errors.append(f"阶段!B{record['row']}：显示名称不能为空")
        if key in seen:
            errors.append(f"阶段!A{record['row']}：阶段ID {key} 重复")
        seen.add(key)
        stages.append(
            {
                "key": key,
                "label": value["显示名称"],
                "description": value["说明"],
            }
        )
    if not stages:
        errors.append("阶段!A2：至少需要填写一个阶段")
    return stages


def _build_nodes(
    records: list[dict[str, Any]],
    errors: list[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    nodes: dict[str, dict[str, Any]] = {}
    designer_rows: dict[str, dict[str, Any]] = {}
    any_designer_value = False
    for record in records:
        value = record["value"]
        node_id = value["节点ID"]
        if not node_id:
            errors.append(f"节点!A{record['row']}：节点ID不能为空")
            continue
        _check_identifier(node_id, f"节点!A{record['row']}", "节点", errors)
        if node_id in nodes:
            errors.append(f"节点!A{record['row']}：节点ID {node_id} 重复")
            continue
        if not value["所属阶段"]:
            errors.append(f"节点!B{record['row']}：所属阶段不能为空")
        node: dict[str, Any] = {
            "stage": value["所属阶段"],
            "options": [],
        }
        if value["节点名称"]:
            node["label"] = value["节点名称"]
        nodes[node_id] = node
        designer_rows[node_id] = {"row": record["row"], "value": value}
        if value["积木类型"] or value["横坐标"] or value["纵坐标"]:
            any_designer_value = True
    if not nodes:
        errors.append("节点!A2：至少需要填写一个节点")

    designer: dict[str, dict[str, Any]] = {}
    if any_designer_value:
        for node_id, record in designer_rows.items():
            value = record["value"]
            row = record["row"]
            missing = [
                header
                for header in ["积木类型", "横坐标", "纵坐标"]
                if not value[header]
            ]
            if missing:
                errors.append(f"节点!D{row}：已填写积木信息时，{', '.join(missing)}不能为空")
                continue
            block_type = _normalize_enum(
                value["积木类型"],
                BLOCK_TYPE_OPTIONS,
                f"节点!D{row}",
                errors,
            )
            try:
                x = float(value["横坐标"])
                y = float(value["纵坐标"])
            except ValueError:
                errors.append(f"节点!E{row}：横坐标和纵坐标必须是数字")
                continue
            designer[node_id] = {
                "id": node_id,
                "block_type": block_type,
                "position": {"x": x, "y": y},
            }
    return nodes, designer


def _build_paths(
    records: list[dict[str, Any]],
    nodes: dict[str, dict[str, Any]],
    errors: list[str],
) -> tuple[dict[str, list[dict[str, Any]]], set[str]]:
    options_by_node: dict[str, list[dict[str, Any]]] = {
        node_id: [] for node_id in nodes
    }
    option_ids: set[str] = set()
    orders: dict[str, set[int]] = {}
    indexed: list[tuple[int, int, dict[str, Any], dict[str, str]]] = []
    for record in records:
        value = record["value"]
        option_id = value["路径ID"]
        source_node = value["来源节点ID"]
        target_node = value["目标节点ID"]
        row = record["row"]
        if not option_id:
            errors.append(f"路径!A{row}：路径ID不能为空")
            continue
        _check_identifier(option_id, f"路径!A{row}", "路径", errors)
        required_path_fields = {
            "来源节点ID": ("B", "来源节点ID"),
            "选项名称": ("D", "选项名称"),
            "选项说明": ("E", "选项说明"),
            "目标节点ID": ("F", "目标节点ID"),
            "目标阶段": ("G", "目标阶段"),
            "结果说明": ("H", "结果说明"),
            "下一步": ("I", "下一步"),
        }
        for field, (column, label) in required_path_fields.items():
            if not value[field]:
                errors.append(f"路径!{column}{row}：{label}不能为空")
        _check_identifier(source_node, f"路径!B{row}", "来源节点", errors)
        _check_identifier(target_node, f"路径!F{row}", "目标节点", errors)
        if option_id in option_ids:
            errors.append(f"路径!A{row}：路径ID {option_id} 重复")
        option_ids.add(option_id)
        if source_node not in nodes:
            errors.append(f"路径!B{row}：来源节点 {source_node} 不存在")
        if target_node not in nodes:
            errors.append(f"路径!F{row}：目标节点 {target_node} 不存在")
        elif value["目标阶段"] != nodes[target_node]["stage"]:
            errors.append(
                f"路径!G{row}：目标阶段 {value['目标阶段']} 与节点 "
                f"{target_node} 的阶段 {nodes[target_node]['stage']} 不一致"
            )
        try:
            order = int(value["顺序"])
            if order < 1:
                raise ValueError
        except ValueError:
            errors.append(f"路径!C{row}：顺序必须是正整数")
            continue
        if source_node and order in orders.setdefault(source_node, set()):
            errors.append(f"路径!C{row}：节点 {source_node} 下的顺序 {order} 重复")
        orders.setdefault(source_node, set()).add(order)
        indexed.append((row, order, record, value))

    for _, _, _, value in sorted(indexed, key=lambda item: (item[3]["来源节点ID"], item[1])):
        source_node = value["来源节点ID"]
        if source_node not in options_by_node:
            continue
        options_by_node[source_node].append(
            {
                "id": value["路径ID"],
                "label": value["选项名称"],
                "description": value["选项说明"],
                "target_stage": value["目标阶段"],
                "target_node": value["目标节点ID"],
                "outcome": value["结果说明"],
                "next_step": value["下一步"],
                "requirements": [],
                "deadlines": [],
            }
        )
    return options_by_node, option_ids


def _build_requirements(
    records: list[dict[str, Any]],
    errors: list[str],
) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for record in records:
        value = record["value"]
        path_id = value["路径ID"]
        requirement_type = _normalize_enum(
            value["条件类型"],
            REQUIREMENT_OPTIONS,
            f"前置条件!B{record['row']}",
            errors,
        )
        requirement = {"type": requirement_type}
        if value["提示文案"]:
            requirement["message"] = value["提示文案"]
        grouped.setdefault(path_id, []).append(requirement)
    return grouped


def _build_deadlines(
    records: list[dict[str, Any]],
    errors: list[str],
) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for record in records:
        value = record["value"]
        required_fields = {
            "期限ID": "B",
            "标题": "C",
            "说明": "D",
            "计算方式": "G",
            "复核状态": "H",
        }
        for field, column in required_fields.items():
            if not value[field]:
                errors.append(
                    f"期限规则!{column}{record['row']}：{field}不能为空"
                )
        _check_identifier(
            value["期限ID"],
            f"期限规则!B{record['row']}",
            "期限",
            errors,
        )
        grouped.setdefault(value["路径ID"], []).append(
            {
                "id": value["期限ID"],
                "title": value["标题"],
                "description": value["说明"],
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
    return grouped


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
    errors.append(f"{location}：值 {value or '(空)'} 不在允许范围内")
    return value


def _display_enum(value: Any, options: dict[str, str]) -> str:
    for label, internal in options.items():
        if value == internal:
            return label
    return str(value or "")


def _check_identifier(
    value: str,
    location: str,
    label: str,
    errors: list[str],
) -> None:
    if value and re.fullmatch(WORKFLOW_ID_PATTERN, value) is None:
        errors.append(
            f"{location}：{label} ID 只能使用字母、数字、下划线、点和短横线"
        )


def _base_field_row(records: list[dict[str, Any]], field: str) -> str:
    for record in records:
        if record["value"]["字段"] == field:
            return str(record["row"])
    return ""


def _column_width(column: int) -> float:
    widths = [22, 22, 24, 24, 32, 30, 28, 34, 34]
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
