from fastapi import APIRouter, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.audit import AuditLog
from app.models.document import Document
from app.models.evidence import Evidence
from app.routes.cases import get_accessible_case
from app.schemas.document import DocumentCreate, DocumentRead
from app.services.documents import generate_document

router = APIRouter(prefix="/cases", tags=["documents"])


@router.get("/{case_id}/documents", response_model=list[DocumentRead])
async def list_documents(
    case_id: int,
    session: DbSession,
    user: CurrentUser,
) -> list[Document]:
    await get_accessible_case(case_id, session, user)
    results = await session.scalars(
        select(Document)
        .where(Document.case_id == case_id)
        .order_by(Document.created_at.desc())
    )
    return list(results)


@router.post(
    "/{case_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    case_id: int,
    payload: DocumentCreate,
    session: DbSession,
    user: CurrentUser,
) -> Document:
    case = await get_accessible_case(case_id, session, user)
    evidence_items = list(
        await session.scalars(select(Evidence).where(Evidence.case_id == case_id))
    )
    title, content = generate_document(case, evidence_items, payload.doc_type)
    previous_count = len(
        list(
            await session.scalars(
                select(Document).where(
                    Document.case_id == case_id,
                    Document.doc_type == payload.doc_type,
                )
            )
        )
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
    return document


@router.get("/{case_id}/documents/{document_id}/download", response_class=PlainTextResponse)
async def download_document(
    case_id: int,
    document_id: int,
    session: DbSession,
    user: CurrentUser,
) -> PlainTextResponse:
    await get_accessible_case(case_id, session, user)
    document = await session.get(Document, document_id)
    if document is None or document.case_id != case_id:
        raise HTTPException(status_code=404, detail="文书不存在")
    return PlainTextResponse(
        document.content,
        headers={
            "Content-Disposition": f'attachment; filename="document-{document.id}.txt"'
        },
    )
