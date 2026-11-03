from copy import deepcopy
from io import BytesIO
from uuid import uuid4

from docx import Document as DocxDocument
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.main import app
from app.routes import admin_rule_packages as rule_package_routes
from app.services.rule_packages import load_default_workflow_package


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return auth_headers(response.json()["access_token"])


def excel_cell(workbook, sheet_name: str, value: str, target_column: str) -> str:
    sheet = workbook[sheet_name]
    for row in range(2, sheet.max_row + 1):
        if sheet.cell(row, 1).value == value:
            return f"{target_column}{row}"
    raise AssertionError(f"missing value in workbook: {value}")


def excel_header_cell(workbook, sheet_name: str, header: str, row: int) -> str:
    sheet = workbook[sheet_name]
    for cell in sheet[1]:
        if cell.value == header:
            return f"{cell.column_letter}{row}"
    raise AssertionError(f"missing header in workbook: {header}")


def test_admin_rule_package_lifecycle_and_runtime_publication() -> None:
    version = f"test-admin-{uuid4().hex[:8]}"
    with TestClient(app) as client:
        admin_headers = login(client, "admin", "Admin123!")
        template = client.get(
            "/api/v1/admin/rule-packages/template",
            headers=admin_headers,
        )
        assert template.status_code == 200
        content = deepcopy(template.json())
        content["version"] = version
        content["nodes"]["intake"]["options"][0]["label"] = "管理端发布路径"

        validation = client.post(
            "/api/v1/admin/rule-packages/validate",
            headers=admin_headers,
            json={"content": content},
        )
        assert validation.status_code == 200
        assert validation.json()["valid"] is True
        assert validation.json()["summary"]["option_count"] >= 2

        imported = client.post(
            "/api/v1/admin/rule-packages/import",
            headers=admin_headers,
            json={"content": content},
        )
        assert imported.status_code == 201
        package = imported.json()
        package_id = package["id"]
        assert package["version"] == version
        assert package["status"] == "draft"

        submitted = client.post(
            f"/api/v1/admin/rule-packages/{package_id}/submit",
            headers=admin_headers,
        )
        assert submitted.status_code == 200
        assert submitted.json()["status"] == "pending_review"

        approved = client.post(
            f"/api/v1/admin/rule-packages/{package_id}/review",
            headers=admin_headers,
            json={"decision": "approved", "note": "测试审核通过"},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"

        published = client.post(
            f"/api/v1/admin/rule-packages/{package_id}/publish",
            headers=admin_headers,
        )
        assert published.status_code == 200
        assert published.json()["status"] == "published"

        worker_headers = login(client, "demo", "Demo123!")
        workflow = client.get(
            "/api/v1/cases/1/workflow",
            headers=worker_headers,
        )
        assert workflow.status_code == 200
        assert workflow.json()["rule_package"]["version"] == version

        retired = client.post(
            f"/api/v1/admin/rule-packages/{package_id}/retire",
            headers=admin_headers,
        )
        assert retired.status_code == 200
        assert retired.json()["status"] == "retired"

        fallback = client.get(
            "/api/v1/cases/1/workflow",
            headers=worker_headers,
        )
        assert fallback.status_code == 200
        assert fallback.json()["rule_package"]["version"] != version


def test_invalid_rule_package_is_rejected_and_permissions_enforced() -> None:
    with TestClient(app) as client:
        admin_headers = login(client, "admin", "Admin123!")
        worker_headers = login(client, "demo", "Demo123!")
        template = client.get(
            "/api/v1/admin/rule-packages/template",
            headers=admin_headers,
        ).json()
        invalid = deepcopy(template)
        invalid["version"] = f"invalid-{uuid4().hex[:8]}"
        invalid["nodes"]["intake"]["options"][0]["target_node"] = "missing-node"

        validation = client.post(
            "/api/v1/admin/rule-packages/validate",
            headers=admin_headers,
            json={"content": invalid},
        )
        assert validation.status_code == 200
        assert validation.json()["valid"] is False
        assert validation.json()["errors"]

        imported = client.post(
            "/api/v1/admin/rule-packages/import",
            headers=admin_headers,
            json={"content": invalid},
        )
        assert imported.status_code == 422

        forbidden = client.get(
            "/api/v1/admin/rule-packages",
            headers=worker_headers,
        )
        assert forbidden.status_code == 403


def test_draft_cannot_be_published_without_review() -> None:
    with TestClient(app) as client:
        headers = login(client, "admin", "Admin123!")
        content = client.get(
            "/api/v1/admin/rule-packages/template",
            headers=headers,
        ).json()
        content["version"] = f"draft-only-{uuid4().hex[:8]}"
        imported = client.post(
            "/api/v1/admin/rule-packages/import",
            headers=headers,
            json={"content": content},
        )
        package_id = imported.json()["id"]

        published = client.post(
            f"/api/v1/admin/rule-packages/{package_id}/publish",
            headers=headers,
        )

    assert published.status_code == 409


def test_admin_can_download_and_import_excel_rule_package() -> None:
    version = f"excel-{uuid4().hex[:8]}"
    with TestClient(app) as client:
        headers = login(client, "admin", "Admin123!")
        template = client.get(
            "/api/v1/admin/rule-packages/template.xlsx",
            headers=headers,
        )

        assert template.status_code == 200
        assert template.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        workbook = load_workbook(BytesIO(template.content))
        workbook["基础信息"][excel_cell(workbook, "基础信息", "规则版本", "B")] = version
        buffer = BytesIO()
        workbook.save(buffer)

        imported = client.post(
            "/api/v1/admin/rule-packages/import-excel",
            headers=headers,
            files={
                "file": (
                    "rules.xlsx",
                    buffer.getvalue(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

    assert imported.status_code == 201
    assert imported.json()["version"] == version
    assert imported.json()["status"] == "draft"


def test_admin_can_export_rule_package_excel() -> None:
    with TestClient(app) as client:
        headers = login(client, "admin", "Admin123!")
        packages = client.get(
            "/api/v1/admin/rule-packages",
            headers=headers,
        ).json()
        exported = client.get(
            f"/api/v1/admin/rule-packages/{packages[0]['id']}/export.xlsx",
            headers=headers,
        )

    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "处理路径" in load_workbook(
        BytesIO(exported.content),
        read_only=True,
    ).sheetnames


def test_admin_can_export_word_review_document() -> None:
    with TestClient(app) as client:
        headers = login(client, "admin", "Admin123!")
        packages = client.get(
            "/api/v1/admin/rule-packages",
            headers=headers,
        ).json()
        exported = client.get(
            f"/api/v1/admin/rule-packages/{packages[0]['id']}/export.docx",
            headers=headers,
        )

    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    document = DocxDocument(BytesIO(exported.content))
    paragraph_text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    table_text = "\n".join(
        cell.text
        for table in document.tables
        for row in table.rows
        for cell in row.cells
    )
    text = paragraph_text + "\n" + table_text
    assert "劳务通规则包复核稿" in paragraph_text
    assert "人工复核意见" in paragraph_text
    assert "cn-labor-workflow" not in text
    assert "pending_review" not in text
    assert "待复核" in text
    assert "识别问题" in text


def test_admin_can_generate_ai_rule_package_draft(monkeypatch) -> None:
    version = f"ai-{uuid4().hex[:8]}"

    async def fake_generate(instruction: str):
        assert "增加工伤咨询分支" in instruction
        return load_default_workflow_package().model_copy(
            update={
                "version": version,
                "review_status": "draft",
            }
        )

    monkeypatch.setattr(
        rule_package_routes,
        "generate_rule_package_draft",
        fake_generate,
    )

    with TestClient(app) as client:
        headers = login(client, "admin", "Admin123!")
        response = client.post(
            "/api/v1/admin/rule-packages/ai-draft",
            headers=headers,
            json={"instruction": "增加工伤咨询分支，并保留人工律师复核入口"},
        )

    assert response.status_code == 201
    assert response.json()["version"] == version
    assert response.json()["status"] == "draft"


def test_worker_cannot_use_excel_rule_package_endpoints() -> None:
    with TestClient(app) as client:
        headers = login(client, "demo", "Demo123!")
        template = client.get(
            "/api/v1/admin/rule-packages/template.xlsx",
            headers=headers,
        )
        imported = client.post(
            "/api/v1/admin/rule-packages/import-excel",
            headers=headers,
            files={"file": ("rules.xlsx", b"not-an-xlsx")},
        )

    assert template.status_code == 403
    assert imported.status_code == 403


def test_excel_import_rejects_invalid_file_type() -> None:
    with TestClient(app) as client:
        headers = login(client, "admin", "Admin123!")
        response = client.post(
            "/api/v1/admin/rule-packages/import-excel",
            headers=headers,
            files={"file": ("rules.xlsm", b"not-an-xlsx")},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "仅支持 .xlsx 文件"
