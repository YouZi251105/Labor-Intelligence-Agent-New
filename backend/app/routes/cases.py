from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select

from app.api.deps import CompleteWorkerProfile, CurrentUser, DbSession
from app.models.audit import AuditLog
from app.models.case import Case, Conversation, Message
from app.models.document import Document
from app.models.evidence import Evidence
from app.schemas.case import (
    CaseArchiveUpdate,
    CaseCreate,
    CaseRead,
    ConsultationResponse,
    MessageCreate,
    MessageRead,
)
from app.services.ai import generate_ai_reply, structured_result

router = APIRouter(prefix="/cases", tags=["cases"])


async def get_accessible_case(
    case_id: int,
    session: DbSession,
    user: CurrentUser,
) -> Case:
    case = await session.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="案件不存在")
    allowed = (
        case.owner_id == user.id
        or case.assigned_lawyer_id == user.id
        or user.role == "admin"
    )
    if not allowed:
        raise HTTPException(status_code=404, detail="案件不存在")
    return case


async def get_worker_owned_case(
    case_id: int,
    session: DbSession,
    user: CurrentUser,
) -> Case:
    case = await get_accessible_case(case_id, session, user)
    if user.role != "user":
        raise HTTPException(status_code=403, detail="仅劳动者本人可执行此操作")
    if case.owner_id != user.id:
        raise HTTPException(status_code=404, detail="案件不存在")
    return case


@router.post("", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
async def create_case(
    payload: CaseCreate,
    session: DbSession,
    user: CompleteWorkerProfile,
) -> Case:
    case = Case(
        owner_id=user.id,
        title=payload.title,
        dispute_type=payload.dispute_type,
        location=payload.location,
        facts=payload.facts,
        summary=payload.facts[:160],
    )
    session.add(case)
    await session.flush()
    session.add(
        AuditLog(
            actor_id=user.id,
            action="case.created",
            object_type="case",
            object_id=case.id,
        )
    )
    await session.commit()
    await session.refresh(case)
    return case


@router.get("", response_model=list[CaseRead])
async def list_cases(
    session: DbSession,
    user: CurrentUser,
    status: str = Query(default="active", pattern="^(active|archived|all)$"),
    dispute_type: str | None = None,
    q: str | None = None,
) -> list[Case]:
    query = select(Case).order_by(Case.updated_at.desc())
    if user.role == "user":
        query = query.where(Case.owner_id == user.id)
    elif user.role == "lawyer":
        query = query.where(Case.assigned_lawyer_id == user.id)

    if status == "active":
        query = query.where(Case.archived == False)  # noqa: E712
    elif status == "archived":
        query = query.where(Case.archived == True)  # noqa: E712

    if dispute_type:
        query = query.where(Case.dispute_type == dispute_type)
    if q:
        pattern = f"%{q}%"
        query = query.where(
            or_(
                Case.title.ilike(pattern),
                Case.summary.ilike(pattern),
                Case.facts.ilike(pattern),
            )
        )

    results = await session.scalars(query)
    return list(results)


@router.get("/{case_id}", response_model=CaseRead)
async def get_case(
    case_id: int,
    session: DbSession,
    user: CurrentUser,
) -> Case:
    return await get_accessible_case(case_id, session, user)


@router.patch("/{case_id}/archive", response_model=CaseRead)
async def archive_case(
    case_id: int,
    payload: CaseArchiveUpdate,
    session: DbSession,
    user: CurrentUser,
) -> Case:
    case = await get_worker_owned_case(case_id, session, user)
    case.archived = payload.archived
    session.add(
        AuditLog(
            actor_id=user.id,
            action="case.archived" if payload.archived else "case.unarchived",
            object_type="case",
            object_id=case.id,
        )
    )
    await session.commit()
    await session.refresh(case)
    return case


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: int,
    session: DbSession,
    user: CurrentUser,
) -> None:
    case = await get_worker_owned_case(case_id, session, user)

    has_messages = await session.scalar(
        select(Message.id)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.case_id == case_id)
        .limit(1)
    )
    has_evidence = await session.scalar(
        select(Evidence.id).where(Evidence.case_id == case_id).limit(1)
    )
    has_documents = await session.scalar(
        select(Document.id).where(Document.case_id == case_id).limit(1)
    )
    if has_messages or has_evidence or has_documents:
        raise HTTPException(
            status_code=409,
            detail="该案件已包含咨询、证据或文书，只能归档不能删除",
        )

    session.add(
        AuditLog(
            actor_id=user.id,
            action="case.deleted",
            object_type="case",
            object_id=case.id,
        )
    )
    await session.delete(case)
    await session.commit()


@router.get("/{case_id}/messages", response_model=list[MessageRead])
async def list_messages(
    case_id: int,
    session: DbSession,
    user: CurrentUser,
) -> list[Message]:
    await get_accessible_case(case_id, session, user)
    conversation = await session.scalar(
        select(Conversation).where(Conversation.case_id == case_id)
    )
    if conversation is None:
        return []
    results = await session.scalars(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc(), Message.id.asc())
    )
    return list(results)


@router.post("/{case_id}/consultations", response_model=ConsultationResponse)
async def consult_case(
    case_id: int,
    payload: MessageCreate,
    session: DbSession,
    user: CompleteWorkerProfile,
) -> ConsultationResponse:
    case = await get_worker_owned_case(case_id, session, user)
    conversation = await session.scalar(
        select(Conversation).where(Conversation.case_id == case_id)
    )
    if conversation is None:
        conversation = Conversation(case_id=case_id)
        session.add(conversation)
        await session.flush()

    history_results = await session.scalars(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(8)
    )
    history = list(reversed(list(history_results)))

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=payload.message,
    )
    session.add(user_message)
    await session.flush()

    ai_result = await generate_ai_reply(case, payload.message, history)
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=ai_result.reply,
        metadata_json={
            "classification": ai_result.classification,
            "structured": structured_result(ai_result),
            "suggested_next_step": ai_result.suggested_next_step,
            "demo_mode": ai_result.demo_mode,
        },
    )
    session.add(assistant_message)

    case.dispute_type = ai_result.classification["dispute_type"]
    case.legal_relationship = ai_result.classification["legal_relationship"]
    case.classification = ai_result.classification
    if case.stage == "intake":
        case.stage = "evidence"
    case.facts = f"{case.facts}\n{payload.message}".strip()
    case.summary = case.facts[:180]
    conversation.summary = case.summary

    session.add(
        AuditLog(
            actor_id=user.id,
            action="case.consultation",
            object_type="case",
            object_id=case.id,
            metadata_json={"demo_mode": ai_result.demo_mode},
        )
    )
    await session.commit()
    await session.refresh(case)
    await session.refresh(user_message)
    await session.refresh(assistant_message)

    return ConsultationResponse(
        case=CaseRead.model_validate(case),
        user_message=MessageRead.model_validate(user_message),
        assistant_message=MessageRead.model_validate(assistant_message),
        classification=ai_result.classification,
        structured=structured_result(ai_result),
        suggested_next_step=ai_result.suggested_next_step,
        demo_mode=ai_result.demo_mode,
    )
