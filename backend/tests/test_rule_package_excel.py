from io import BytesIO

import pytest
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from app.schemas.workflow_rules import WorkflowRulePackage
from app.services.rule_package_excel import (
    RulePackageExcelError,
    export_rule_package_excel,
    import_rule_package_excel,
)
from app.services.rule_packages import load_default_workflow_package

SHEETS = [
    "填写说明",
    "基础信息",
    "案件阶段",
    "流程节点",
    "处理路径",
    "前置条件",
    "期限规则",
    "系统信息",
    "数据字典",
]


def _source_content() -> dict:
    return load_default_workflow_package().model_dump(mode="json")


def _header_column(sheet, header: str) -> int:
    for cell in sheet[1]:
        if cell.value == header:
            return cell.column
    raise AssertionError(f"missing header: {header}")


def _field_row(sheet, value: str) -> int:
    for row in range(2, sheet.max_row + 1):
        if sheet.cell(row, 1).value == value:
            return row
    raise AssertionError(f"missing field: {value}")


def _workbook_data(**changes) -> bytes:
    workbook = load_workbook(BytesIO(export_rule_package_excel(_source_content())))
    for sheet_name, cell, value in changes.get("cells", []):
        workbook[sheet_name][cell] = value
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_rule_package_excel_has_nontechnical_sheets() -> None:
    workbook = load_workbook(
        BytesIO(export_rule_package_excel(_source_content())),
        read_only=True,
    )

    assert workbook.sheetnames == SHEETS
    assert workbook["系统信息"].sheet_state == "hidden"
    assert workbook["数据字典"].sheet_state == "hidden"

    visible_sheets = [
        "基础信息",
        "案件阶段",
        "流程节点",
        "处理路径",
        "前置条件",
        "期限规则",
    ]
    for sheet_name in visible_sheets:
        headers = [cell.value for cell in workbook[sheet_name][1]]
        assert all("ID" not in str(header) and "id" not in str(header) for header in headers)


def test_rule_package_excel_round_trip_preserves_business_content() -> None:
    source = _source_content()

    imported = import_rule_package_excel(export_rule_package_excel(source))
    package = WorkflowRulePackage.model_validate(imported)

    assert package.package_id == source["package_id"]
    assert package.start_node in package.nodes
    assert [stage.label for stage in package.stages] == [
        stage["label"] for stage in source["stages"]
    ]
    assert sum(len(node.options) for node in package.nodes.values()) == sum(
        len(node["options"]) for node in source["nodes"].values()
    )
    assert package.designer is not None
    assert len(package.designer.blocks) == len(package.nodes)


def test_excel_import_reports_target_node_row_without_ids() -> None:
    workbook = load_workbook(BytesIO(export_rule_package_excel(_source_content())))
    sheet = workbook["处理路径"]
    target_column = _header_column(sheet, "去向节点")
    sheet.cell(row=2, column=target_column, value="不存在的节点")
    buffer = BytesIO()
    workbook.save(buffer)

    with pytest.raises(RulePackageExcelError) as error:
        import_rule_package_excel(buffer.getvalue())

    coordinate = f"{get_column_letter(target_column)}2"
    assert f"处理路径!{coordinate}" in str(error.value)
    assert "不存在的节点" in str(error.value)


def test_excel_import_rejects_formula_cells() -> None:
    data = _workbook_data(cells=[("案件阶段", "A2", '="识别问题"')])

    with pytest.raises(RulePackageExcelError) as error:
        import_rule_package_excel(data)

    assert "案件阶段!A2" in str(error.value)
    assert "公式" in str(error.value)


def test_excel_import_reports_required_path_field_row() -> None:
    data = _workbook_data(cells=[("处理路径", "C2", "")])

    with pytest.raises(RulePackageExcelError) as error:
        import_rule_package_excel(data)

    assert "处理路径!C2" in str(error.value)
    assert "处理选项名称不能为空" in str(error.value)


def test_excel_import_rejects_extra_sheet_and_merged_cells() -> None:
    workbook = load_workbook(BytesIO(export_rule_package_excel(_source_content())))
    workbook.create_sheet("自行新增")
    workbook["案件阶段"].merge_cells("A2:B2")
    buffer = BytesIO()
    workbook.save(buffer)

    with pytest.raises(RulePackageExcelError) as error:
        import_rule_package_excel(buffer.getvalue())

    message = str(error.value)
    assert "未允许的工作表" in message
    assert "案件阶段!A2:B2" in message
    assert "合并单元格" in message


def test_excel_import_rejects_rows_over_limit() -> None:
    workbook = load_workbook(BytesIO(export_rule_package_excel(_source_content())))
    workbook["案件阶段"].cell(row=2_003, column=1, value="超限阶段")
    buffer = BytesIO()
    workbook.save(buffer)

    with pytest.raises(RulePackageExcelError) as error:
        import_rule_package_excel(buffer.getvalue())

    assert "案件阶段" in str(error.value)
    assert "2000" in str(error.value)


def test_excel_import_rejects_duplicate_chinese_node_name() -> None:
    workbook = load_workbook(BytesIO(export_rule_package_excel(_source_content())))
    sheet = workbook["流程节点"]
    sheet["A3"] = sheet["A2"].value
    buffer = BytesIO()
    workbook.save(buffer)

    with pytest.raises(RulePackageExcelError) as error:
        import_rule_package_excel(buffer.getvalue())

    assert "流程节点!A3" in str(error.value)
    assert "节点名称" in str(error.value)
    assert "重复" in str(error.value)


def test_excel_import_preserves_designer_layout() -> None:
    source = _source_content()
    source["designer"] = {
        "version": 1,
        "blocks": {
            node_id: {
                "id": node_id,
                "block_type": block_type,
                "position": {"x": index * 20, "y": index * 30},
            }
            for index, (node_id, block_type) in enumerate(
                [
                    ("intake", "decision"),
                    ("evidence", "evidence_gate"),
                    ("procedure", "decision"),
                    ("document", "lawyer_gate"),
                    ("lawyer_help", "stage"),
                    ("closed", "end"),
                ]
            )
        },
    }

    imported = import_rule_package_excel(export_rule_package_excel(source))
    package = WorkflowRulePackage.model_validate(imported)

    assert package.designer is not None
    positions = sorted(
        (block.position.x, block.position.y)
        for block in package.designer.blocks.values()
    )
    assert positions == [(0, 0), (20, 30), (40, 60), (60, 90), (80, 120), (100, 150)]
    assert {block.block_type for block in package.designer.blocks.values()} == {
        "decision",
        "evidence_gate",
        "lawyer_gate",
        "stage",
        "end",
    }
