from collections.abc import Sequence
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select

from app.api.deps import CompleteWorkerProfile, CurrentUser, DbSession
from app.models.audit import AuditLog
from app.models.document import Document, DocumentEvidence
from app.models.evidence import Evidence
from app.routes.cases import get_accessible_case, get_worker_owned_case
from app.schemas.document import (
    DocumentCreate,
    DocumentEvidenceRead,
    DocumentRead,
    DocumentRevisionCreate,
)
from app.services.documents import (
    generate_document,
    render_document_docx,
    render_document_pdf,
)

router = APIRouter(prefix="/cases", tags=["documents"])


async def get_case_document(
    case_id: int,
    document_id: int,
    session: DbSession,
    user: CurrentUser,
) -> Document:
    await get_accessible_case(case_id, session, user)
    document = await session.get(Document, document_id)
    if document is None or document.case_id != case_id:
        raise HTTPException(status_code=404, detail="文书不存在")
    return document


async def get_document_evidence(
    document_id: int,
    session: DbSession,
) -> list[DocumentEvidenceRead]:
    rows = list(
        await session.scalars(
            select(DocumentEvidence)
            .where(DocumentEvidence.document_id == document_id)
            .order_by(DocumentEvidence.position, DocumentEvidence.id)
        )
    )
    return [
        DocumentEvidenceRead(
            evidence_id=row.evidence_id,
            filename=row.filename,
            category=row.category,
            sha256=row.sha256,
        )
        for row in rows
    ]


async def to_document_read(document: Document, session: DbSession) -> DocumentRead:
    data = DocumentRead.model_validate(document)
    return data.model_copy(
        update={"evidence": await get_document_evidence(document.id, session)}
    )


def add_evidence_snapshot(
    document_id: int,
    evidence_items: Sequence[Evidence | DocumentEvidence],
) -> list[DocumentEvidence]:
    records: list[DocumentEvidence] = []
    for position, item in enumerate(evidence_items):
        if isinstance(item, DocumentEvidence):
            evidence_id = item.evidence_id
            filename = item.filename
            category = item.category
            sha256 = item.sha256
        else:
            evidence_id = item.id
            filename = item.filename
            category = item.category
            sha256 = item.sha256
        records.append(
            DocumentEvidence(
                document_id=document_id,
                evidence_id=evidence_id,
                filename=filename,
                category=category,
                sha256=sha256,
                position=position,
            )
        )
    return records


@router.get("/{case_id}/documents", response_model=list[DocumentRead])
async def list_documents(
    case_id: int,
    session: DbSession,
    user: CurrentUser,
) -> list[DocumentRead]:
    await get_accessible_case(case_id, session, user)
    results = await session.scalars(
        select(Document)
        .where(Document.case_id == case_id)
        .order_by(Document.created_at.desc())
    )
    return [await to_document_read(document, session) for document in results]


@router.post(
    "/{case_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    case_id: int,
    payload: DocumentCreate,
    session: DbSession,
    user: CompleteWorkerProfile,
) -> DocumentRead:
    case = await get_worker_owned_case(case_id, session, user)
    evidence_items = list(
        await session.scalars(select(Evidence).where(Evidence.case_id == case_id))
    )
    title, content = generate_document(case, evidence_items, payload.doc_type)
    previous_documents = list(
        await session.scalars(
            select(Document).where(
                Document.case_id == case_id,
                Document.doc_type == payload.doc_type,
            )
        )
    )
    previous_count = max(
        (document.version for document in previous_documents),
        default=0,
    )
    document = Document(
        case_id=case_id,
        doc_type=payload.doc_type,
        title=title,
        content=content,
        version=previous_count + 1,
    )
    session.add(document)
    await session.flush()
    snapshots = add_evidence_snapshot(document.id, evidence_items)
    session.add_all(snapshots)
    session.add(
        AuditLog(
            actor_id=user.id,
            action="document.generated",
            object_type="document",
            object_id=document.id,
            metadata_json={"doc_type": payload.doc_type},
        )
    )
    await session.commit()
    await session.refresh(document)
    return await to_document_read(document, session)


@router.post(
    "/{case_id}/documents/{document_id}/revisions",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_document_revision(
    case_id: int,
    document_id: int,
    payload: DocumentRevisionCreate,
    session: DbSession,
    user: CompleteWorkerProfile,
) -> DocumentRead:
    await get_worker_owned_case(case_id, session, user)
    original = await get_case_document(case_id, document_id, session, user)
    original_snapshot = list(
        await session.scalars(
            select(DocumentEvidence)
            .where(DocumentEvidence.document_id == original.id)
            .order_by(DocumentEvidence.position, DocumentEvidence.id)
        )
    )
    if not original_snapshot:
        case_evidence = list(
            await session.scalars(select(Evidence).where(Evidence.case_id == case_id))
        )
        snapshot_source: Sequence[Evidence | DocumentEvidence] = case_evidence
    else:
        snapshot_source = original_snapshot

    revision = Document(
        case_id=case_id,
        doc_type=original.doc_type,
        title=payload.title,
        content=payload.content,
        status=payload.status,
        version=original.version + 1,
    )
    session.add(revision)
    await session.flush()
    session.add_all(add_evidence_snapshot(revision.id, snapshot_source))
    session.add(
        AuditLog(
            actor_id=user.id,
            action="document.revision_created",
            object_type="document",
            object_id=revision.id,
            metadata_json={
                "source_document_id": original.id,
                "version": revision.version,
            },
        )
    )
    await session.commit()
    await session.refresh(revision)
    return await to_document_read(revision, session)


@router.get("/{case_id}/documents/{document_id}/export")
async def export_document(
    case_id: int,
    document_id: int,
    session: DbSession,
    user: CurrentUser,
    file_format: Literal["docx", "pdf"] = Query(alias="format"),
) -> Response:
    document = await get_case_document(case_id, document_id, session, user)
    if file_format == "docx":
        content = render_document_docx(document.title, document.content)
        media_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        extension = "docx"
    else:
        content = render_document_pdf(document.content)
        media_type = "application/pdf"
        extension = "pdf"

    session.add(
        AuditLog(
            actor_id=user.id,
            action="document.exported",
            object_type="document",
            object_id=document.id,
            metadata_json={"format": extension},
        )
    )
    await session.commit()
    encoded_name = quote(f"{document.title}.{extension}")
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"document-{document.id}.{extension}\"; "
                f"filename*=UTF-8''{encoded_name}"
            )
        },
    )


@router.get("/{case_id}/documents/{document_id}/download", response_class=PlainTextResponse)
async def download_document(
    case_id: int,
    document_id: int,
    session: DbSession,
    user: CurrentUser,
) -> PlainTextResponse:
    document = await get_case_document(case_id, document_id, session, user)
    session.add(
        AuditLog(
            actor_id=user.id,
            action="document.downloaded",
            object_type="document",
            object_id=document.id,
            metadata_json={"format": "txt"},
        )
    )
    await session.commit()
    return PlainTextResponse(
        document.content,
        headers={
            "Content-Disposition": f'attachment; filename="document-{document.id}.txt"'
        },
    )
