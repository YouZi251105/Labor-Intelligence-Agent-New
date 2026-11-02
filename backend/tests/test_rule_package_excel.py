from io import BytesIO

import pytest
from openpyxl import load_workbook

from app.schemas.workflow_rules import WorkflowRulePackage
from app.services.rule_package_excel import (
    RulePackageExcelError,
    export_rule_package_excel,
    import_rule_package_excel,
)
from app.services.rule_packages import load_default_workflow_package


def _source_content() -> dict:
    return load_default_workflow_package().model_dump(mode="json")


def _header_column(sheet, header: str) -> int:
    for cell in sheet[1]:
        if cell.value == header:
            return cell.column
    raise AssertionError(f"missing header: {header}")


def test_rule_package_excel_has_expected_sheets() -> None:
    data = export_rule_package_excel(_source_content())
    workbook = load_workbook(BytesIO(data), read_only=True)

    assert workbook.sheetnames == [
        "填写说明",
        "基础信息",
        "阶段",
        "节点",
        "路径",
        "前置条件",
        "期限规则",
        "数据字典",
    ]
    assert workbook["数据字典"].sheet_state == "hidden"


def test_rule_package_excel_round_trip() -> None:
    source = _source_content()

    imported = import_rule_package_excel(export_rule_package_excel(source))
    package = WorkflowRulePackage.model_validate(imported)

    assert package.package_id == source["package_id"]
    assert package.start_node == source["start_node"]
    assert len(package.stages) == len(source["stages"])
    assert len(package.nodes) == len(source["nodes"])
    assert sum(len(node.options) for node in package.nodes.values()) == sum(
        len(node["options"]) for node in source["nodes"].values()
    )


def test_excel_import_reports_sheet_and_row() -> None:
    workbook = load_workbook(BytesIO(export_rule_package_excel(_source_content())))
    sheet = workbook["路径"]
    target_column = _header_column(sheet, "目标节点ID")
    sheet.cell(row=2, column=target_column, value="missing-node")
    buffer = BytesIO()
    workbook.save(buffer)

    with pytest.raises(RulePackageExcelError) as error:
        import_rule_package_excel(buffer.getvalue())

    assert "路径!F2" in str(error.value)
    assert "missing-node" in str(error.value)


def test_excel_import_rejects_formula_cells() -> None:
    workbook = load_workbook(BytesIO(export_rule_package_excel(_source_content())))
    sheet = workbook["阶段"]
    label_column = _header_column(sheet, "显示名称")
    sheet.cell(row=2, column=label_column, value='="识别问题"')
    buffer = BytesIO()
    workbook.save(buffer)

    with pytest.raises(RulePackageExcelError) as error:
        import_rule_package_excel(buffer.getvalue())

    assert "阶段!B2" in str(error.value)
    assert "公式" in str(error.value)


def test_excel_import_reports_required_path_field_row() -> None:
    workbook = load_workbook(BytesIO(export_rule_package_excel(_source_content())))
    workbook["路径"]["D2"] = ""
    buffer = BytesIO()
    workbook.save(buffer)

    with pytest.raises(RulePackageExcelError) as error:
        import_rule_package_excel(buffer.getvalue())

    assert "路径!D2" in str(error.value)
    assert "选项名称不能为空" in str(error.value)


def test_excel_import_rejects_extra_sheet_and_merged_cells() -> None:
    workbook = load_workbook(BytesIO(export_rule_package_excel(_source_content())))
    workbook.create_sheet("自行新增")
    workbook["阶段"].merge_cells("B2:C2")
    buffer = BytesIO()
    workbook.save(buffer)

    with pytest.raises(RulePackageExcelError) as error:
        import_rule_package_excel(buffer.getvalue())

    message = str(error.value)
    assert "未允许的工作表" in message
    assert "阶段!B2:C2" in message
    assert "合并单元格" in message


def test_excel_import_rejects_rows_over_limit() -> None:
    workbook = load_workbook(BytesIO(export_rule_package_excel(_source_content())))
    workbook["阶段"].cell(row=2_003, column=1, value="overflow")
    buffer = BytesIO()
    workbook.save(buffer)

    with pytest.raises(RulePackageExcelError) as error:
        import_rule_package_excel(buffer.getvalue())

    assert "阶段" in str(error.value)
    assert "2000" in str(error.value)


def test_excel_import_preserves_designer_blocks() -> None:
    source = _source_content()
    source["designer"] = {
        "version": 1,
        "blocks": {
            "intake": {
                "id": "intake",
                "block_type": "decision",
                "position": {"x": 10, "y": 20},
            },
            "evidence": {
                "id": "evidence",
                "block_type": "evidence_gate",
                "position": {"x": 30, "y": 40},
            },
            "procedure": {
                "id": "procedure",
                "block_type": "decision",
                "position": {"x": 50, "y": 60},
            },
            "document": {
                "id": "document",
                "block_type": "lawyer_gate",
                "position": {"x": 70, "y": 80},
            },
            "lawyer_help": {
                "id": "lawyer_help",
                "block_type": "stage",
                "position": {"x": 90, "y": 100},
            },
            "closed": {
                "id": "closed",
                "block_type": "end",
                "position": {"x": 110, "y": 120},
            },
        },
    }

    imported = import_rule_package_excel(export_rule_package_excel(source))
    package = WorkflowRulePackage.model_validate(imported)

    assert package.designer is not None
    assert package.designer.blocks["evidence"].block_type == "evidence_gate"
    assert package.designer.blocks["closed"].position.x == 110


def test_excel_import_reports_invalid_identifier_row() -> None:
    workbook = load_workbook(BytesIO(export_rule_package_excel(_source_content())))
    workbook["节点"]["A2"] = "invalid node id"
    buffer = BytesIO()
    workbook.save(buffer)

    with pytest.raises(RulePackageExcelError) as error:
        import_rule_package_excel(buffer.getvalue())

    assert "节点!A2" in str(error.value)
    assert "ID 只能使用" in str(error.value)
