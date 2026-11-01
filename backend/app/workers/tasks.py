import asyncio
import base64

from app.db.session import get_session_factory
from app.models.audit import AuditLog
from app.models.document import Document
from app.models.evidence import Evidence
from app.services.documents import render_document_docx, render_document_pdf
from app.services.evidence import read_stored_content
from app.services.extraction import extract_text_from_bytes
from app.workers.celery_app import celery_app


async def _extract_evidence(evidence_id: int) -> dict[str, str]:
    async with get_session_factory()() as session:
        evidence = await session.get(Evidence, evidence_id)
        if evidence is None:
            return {"status": "not_found"}
        try:
            content = read_stored_content(evidence.stored_path)
        except (FileNotFoundError, ValueError):
            return {"status": "file_not_found"}
        result = extract_text_from_bytes(
            evidence.filename,
            content,
            evidence.content_type,
        )
        evidence.text_content = result.text
        evidence.screening_status = (
            "accepted" if result.status == "extracted" else "needs_review"
        )
        assessment = dict(evidence.assessment or {})
        assessment["extraction"] = result.as_assessment()
        evidence.assessment = assessment
        session.add(
            AuditLog(
                actor_id=None,
                action="evidence.extracted_async",
                object_type="evidence",
                object_id=evidence.id,
                metadata_json={
                    "status": result.status,
                    "provider": result.provider,
                },
            )
        )
        await session.commit()
        return {"status": result.status, "message": result.message}


async def _export_document(
    document_id: int,
    file_format: str,
) -> dict[str, str]:
    async with get_session_factory()() as session:
        document = await session.get(Document, document_id)
        if document is None:
            return {"status": "not_found"}
        if file_format == "pdf":
            content = render_document_pdf(document.content)
        elif file_format == "docx":
            content = render_document_docx(document.title, document.content)
        else:
            return {"status": "invalid_format"}
        return {
            "status": "completed",
            "content_base64": base64.b64encode(content).decode("ascii"),
        }


@celery_app.task(name="evidence.extract")  # type: ignore[misc]
def extract_evidence_task(evidence_id: int) -> dict[str, str]:
    return asyncio.run(_extract_evidence(evidence_id))


@celery_app.task(name="document.export")  # type: ignore[misc]
def export_document_task(document_id: int, file_format: str) -> dict[str, str]:
    return asyncio.run(_export_document(document_id, file_format))
