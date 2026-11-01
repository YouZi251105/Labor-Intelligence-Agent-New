import sqlite3
from io import BytesIO
from pathlib import Path

from docx import Document as DocxDocument
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from app.main import app

TEST_DB = Path(__file__).resolve().parents[1] / "data" / "test.db"


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login_demo(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "demo", "password": "Demo123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def create_case(client: TestClient, token: str, title: str) -> int:
    response = client.post(
        "/api/v1/cases",
        headers=auth_headers(token),
        json={
            "title": title,
            "dispute_type": "wage",
            "location": "上海市",
            "facts": "公司拖欠工资，双方签订过劳动合同。",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def make_docx(text: str) -> bytes:
    document = DocxDocument()
    document.add_paragraph(text)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def make_text_pdf(text: str) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(72, 720, text)
    pdf.save()
    return buffer.getvalue()


def test_docx_evidence_upload_exposes_extraction_contract() -> None:
    with TestClient(app) as client:
        token = login_demo(client)
        case_id = create_case(client, token, "DOCX 文本提取")

        response = client.post(
            f"/api/v1/cases/{case_id}/evidence",
            headers=auth_headers(token),
            files={
                "file": (
                    "劳动合同.docx",
                    make_docx("劳动合同约定月工资5000元。"),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["extraction_status"] == "extracted"
    assert "劳动合同约定月工资5000元" in payload["text_preview"]


def test_pdf_evidence_upload_extracts_selectable_text() -> None:
    with TestClient(app) as client:
        token = login_demo(client)
        case_id = create_case(client, token, "PDF 文本提取")

        response = client.post(
            f"/api/v1/cases/{case_id}/evidence",
            headers=auth_headers(token),
            files={
                "file": (
                    "工资说明.pdf",
                    make_text_pdf("September wage 5000 RMB"),
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["extraction_status"] == "extracted"
    assert "September wage" in payload["text_preview"]


def test_image_evidence_without_ocr_is_accepted_with_explicit_status() -> None:
    png = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\rIDAT\x08\xd7c\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff"
        b"\x89\x99=\x1d\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    with TestClient(app) as client:
        token = login_demo(client)
        case_id = create_case(client, token, "图片证据")

        response = client.post(
            f"/api/v1/cases/{case_id}/evidence",
            headers=auth_headers(token),
            files={"file": ("聊天截图.png", png, "image/png")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["extraction_status"] == "ocr_required"
    assert payload["screening_status"] == "needs_review"


def test_evidence_extraction_can_be_retried() -> None:
    with TestClient(app) as client:
        token = login_demo(client)
        case_id = create_case(client, token, "提取重试")
        uploaded = client.post(
            f"/api/v1/cases/{case_id}/evidence",
            headers=auth_headers(token),
            files={
                "file": (
                    "补充说明.txt",
                    "工资尚未支付。".encode(),
                    "text/plain",
                )
            },
        )
        evidence_id = uploaded.json()["id"]

        response = client.post(
            f"/api/v1/cases/{case_id}/evidence/{evidence_id}/extract",
            headers=auth_headers(token),
        )

    assert response.status_code == 200
    assert response.json()["extraction_status"] == "extracted"
    assert "工资尚未支付" in response.json()["extracted_text"]


def test_evidence_download_is_case_scoped_and_audited() -> None:
    with TestClient(app) as client:
        token = login_demo(client)
        case_id = create_case(client, token, "材料下载权限")
        uploaded = client.post(
            f"/api/v1/cases/{case_id}/evidence",
            headers=auth_headers(token),
            files={
                "file": (
                    "工资记录.txt",
                    "工资记录正文".encode(),
                    "text/plain",
                )
            },
        )
        evidence_id = uploaded.json()["id"]
        downloaded = client.get(
            f"/api/v1/cases/{case_id}/evidence/{evidence_id}/download",
            headers=auth_headers(token),
        )

        registered = client.post(
            "/api/v1/auth/register",
            json={
                "username": "other-evidence-user",
                "password": "OtherUser123!",
                "display_name": "其他用户",
            },
        )
        other_token = registered.json()["access_token"]
        forbidden = client.get(
            f"/api/v1/cases/{case_id}/evidence/{evidence_id}/download",
            headers=auth_headers(other_token),
        )

    assert downloaded.status_code == 200
    assert downloaded.content == "工资记录正文".encode()
    assert forbidden.status_code == 404

    with sqlite3.connect(TEST_DB) as connection:
        action = connection.execute(
            """
            SELECT action
            FROM audit_logs
            WHERE object_type = 'evidence' AND object_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (evidence_id,),
        ).fetchone()
    assert action == ("evidence.downloaded",)


def test_contract_file_review_extracts_and_reviews_docx() -> None:
    with TestClient(app) as client:
        token = login_demo(client)
        case_id = create_case(client, token, "合同文件审查")

        response = client.post(
            f"/api/v1/cases/{case_id}/contract-review/file",
            headers=auth_headers(token),
            files={
                "file": (
                    "劳动合同.docx",
                    make_docx("甲方可以随时解除合同，乙方自愿放弃社会保险。"),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["extraction_status"] == "extracted"
    assert payload["review"]["risk_level"] == "high"


def test_document_contains_evidence_snapshot_and_can_be_revised() -> None:
    with TestClient(app) as client:
        token = login_demo(client)
        case_id = create_case(client, token, "文书版本")
        evidence = client.post(
            f"/api/v1/cases/{case_id}/evidence",
            headers=auth_headers(token),
            files={
                "file": (
                    "工资流水.txt",
                    "9月工资5000元，尚未支付。".encode(),
                    "text/plain",
                )
            },
        )
        assert evidence.status_code == 201

        created = client.post(
            f"/api/v1/cases/{case_id}/documents",
            headers=auth_headers(token),
            json={"doc_type": "arbitration"},
        )
        assert created.status_code == 201
        document = created.json()

        revised = client.post(
            f"/api/v1/cases/{case_id}/documents/{document['id']}/revisions",
            headers=auth_headers(token),
            json={
                "title": document["title"],
                "content": f"{document['content']}\n补充请求事项。",
                "status": "draft",
            },
        )

    assert document["evidence"][0]["filename"] == "工资流水.txt"
    assert revised.status_code == 201
    assert revised.json()["version"] == document["version"] + 1
    assert revised.json()["evidence"] == document["evidence"]


def test_document_export_supports_docx_and_pdf_and_writes_audit() -> None:
    with TestClient(app) as client:
        token = login_demo(client)
        case_id = create_case(client, token, "文书导出")
        created = client.post(
            f"/api/v1/cases/{case_id}/documents",
            headers=auth_headers(token),
            json={"doc_type": "settlement"},
        )
        document_id = created.json()["id"]

        docx_response = client.get(
            f"/api/v1/cases/{case_id}/documents/{document_id}/export?format=docx",
            headers=auth_headers(token),
        )
        pdf_response = client.get(
            f"/api/v1/cases/{case_id}/documents/{document_id}/export?format=pdf",
            headers=auth_headers(token),
        )

    assert docx_response.status_code == 200
    assert docx_response.content.startswith(b"PK")
    assert "wordprocessingml.document" in docx_response.headers["content-type"]
    assert pdf_response.status_code == 200
    assert pdf_response.content.startswith(b"%PDF")

    with sqlite3.connect(TEST_DB) as connection:
        actions = {
            row[0]
            for row in connection.execute(
                "SELECT action FROM audit_logs WHERE object_id = ?",
                (document_id,),
            )
        }
    assert "document.exported" in actions
