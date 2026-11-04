import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, select

from app.api.deps import CompleteWorkerProfile, CurrentUser, DbSession
from app.db.session import get_session_factory
from app.models.audit import AuditLog
from app.models.case import Case, Conversation, Message
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.lawyer_service import CaseReview, ConsultationSession, LawyerRequest
from app.schemas.case import (
    CaseArchiveUpdate,
    CaseCreate,
    CaseRead,
    ConsultationResponse,
    MessageCreate,
    MessageRead,
)
from app.services.ai import (
    AIResult,
    generate_ai_reply,
    generate_ai_reply_stream,
    structured_result,
)

router = APIRouter(prefix="/cases", tags=["cases"])


def _sse_event(event: str, payload: dict[str, Any]) -> str:
    return (
        f"event: {event}\n"
        f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
    )


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


@router.post("/consult", response_model=ConsultationResponse, status_code=status.HTTP_201_CREATED)
async def consult_auto_create(
    payload: MessageCreate,
    session: DbSession,
    user: CompleteWorkerProfile,
) -> ConsultationResponse:
    """新开会话：先发咨询再自动建案，AI 分类结果回填到案件。

    供未创建案件的用户直接咨询使用；已建案件继续走
    ``POST /cases/{case_id}/consultations`` 在既有案件中对话。
    """
    title = payload.message.strip()[:30] or "新的劳动纠纷咨询"
    case = Case(
        owner_id=user.id,
        title=title,
        dispute_type="labor_other",  # AI 分类完成后立即回填
        stage="intake",
        status="active",
        facts=payload.message,
        summary=payload.message[:160],
    )
    session.add(case)
    await session.flush()

    conversation = Conversation(case_id=case.id)
    session.add(conversation)
    await session.flush()

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=payload.message,
    )
    session.add(user_message)
    await session.flush()

    ai_result = await generate_ai_reply(case, payload.message, history=[])

    case.dispute_type = ai_result.classification["dispute_type"]
    case.legal_relationship = ai_result.classification["legal_relationship"]
    case.classification = ai_result.classification
    case.stage = "evidence" if case.stage == "intake" else case.stage
    case.summary = payload.message[:180]
    conversation.summary = case.summary

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

    session.add(
        AuditLog(
            actor_id=user.id,
            action="case.auto_created_consultation",
            object_type="case",
            object_id=case.id,
            metadata_json={
                "title": title,
                "dispute_type": case.dispute_type,
                "demo_mode": ai_result.demo_mode,
            },
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
    has_lawyer_request = await session.scalar(
        select(LawyerRequest.id).where(LawyerRequest.case_id == case_id).limit(1)
    )
    has_case_review = await session.scalar(
        select(CaseReview.id).where(CaseReview.case_id == case_id).limit(1)
    )
    has_consultation_session = await session.scalar(
        select(ConsultationSession.id)
        .where(ConsultationSession.case_id == case_id)
        .limit(1)
    )
    if (
        has_messages
        or has_evidence
        or has_documents
        or has_lawyer_request
        or has_case_review
        or has_consultation_session
    ):
        raise HTTPException(
            status_code=409,
            detail="该案件已包含咨询、证据、文书或律师服务记录，只能归档不能删除",
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


async def _run_consult_stream(
    case: Case,
    conversation: Conversation,
    user_message: Message,
    history: list[Message],
    payload: MessageCreate,
    user: CompleteWorkerProfile,
    *,
    initial_case_payload: dict[str, Any],
    user_message_payload: dict[str, Any],
    action: str,
) -> AsyncIterator[str]:
    ai_result: AIResult | None = None
    streamed_parts: list[str] = []
    first_status = True
    try:
        async for event in generate_ai_reply_stream(case, payload.message, history):
            event_type = event["type"]
            if event_type == "status":
                data = dict(event)
                if first_status:
                    first_status = False
                    data["case"] = initial_case_payload
                    data["user_message"] = user_message_payload
                yield _sse_event("status", data)
            elif event_type == "delta":
                text = str(event.get("text") or "")
                if text:
                    streamed_parts.append(text)
                    yield _sse_event("delta", {"text": text})
            elif event_type == "complete":
                ai_result = event["result"]

        if ai_result is None:
            raise RuntimeError("AI stream finished without a complete result")
        streamed_reply = "".join(streamed_parts)
        if streamed_reply != ai_result.reply:
            ai_result = AIResult(
                reply=streamed_reply,
                classification=ai_result.classification,
                suggested_next_step=ai_result.suggested_next_step,
                demo_mode=ai_result.demo_mode,
                required_information=ai_result.required_information,
                evidence_gaps=ai_result.evidence_gaps,
                risk_flags=ai_result.risk_flags,
                citations=ai_result.citations,
                summary=ai_result.summary,
                follow_up_options=ai_result.follow_up_options,
                intervention_recommendation=ai_result.intervention_recommendation,
                references=ai_result.references,
            )

        structured = structured_result(ai_result)
        async with get_session_factory()() as write_session:
            persisted_case = await write_session.get(Case, case.id)
            persisted_conversation = await write_session.scalar(
                select(Conversation).where(Conversation.case_id == case.id)
            )
            if persisted_case is None or persisted_conversation is None:
                raise RuntimeError("Case context disappeared during streaming")
            assistant_message = Message(
                conversation_id=persisted_conversation.id,
                role="assistant",
                content=ai_result.reply,
                metadata_json={
                    "classification": ai_result.classification,
                    "structured": structured,
                    "suggested_next_step": ai_result.suggested_next_step,
                    "demo_mode": ai_result.demo_mode,
                },
            )
            write_session.add(assistant_message)
            persisted_case.dispute_type = ai_result.classification["dispute_type"]
            persisted_case.legal_relationship = ai_result.classification[
                "legal_relationship"
            ]
            persisted_case.classification = ai_result.classification
            if persisted_case.stage == "intake":
                persisted_case.stage = "evidence"
            if action == "case.auto_created_consultation":
                persisted_case.title = payload.message.strip()[:30] or persisted_case.title
                persisted_case.facts = payload.message
                persisted_case.summary = payload.message[:180]
            else:
                persisted_case.facts = (
                    f"{persisted_case.facts}\n{payload.message}".strip()
                )
                persisted_case.summary = persisted_case.facts[:180]
            persisted_conversation.summary = persisted_case.summary
            write_session.add(
                AuditLog(
                    actor_id=user.id,
                    action=action,
                    object_type="case",
                    object_id=persisted_case.id,
                    metadata_json={
                        "demo_mode": ai_result.demo_mode,
                        "streamed": True,
                    },
                )
            )
            await write_session.commit()
            await write_session.refresh(persisted_case)
            await write_session.refresh(assistant_message)
            case_payload = CaseRead.model_validate(
                persisted_case
            ).model_dump(mode="json")
            assistant_payload = MessageRead.model_validate(
                assistant_message
            ).model_dump(mode="json")

        if ai_result.references:
            yield _sse_event(
                "references",
                {
                    "items": [item.__dict__ for item in ai_result.references]
                },
            )
        yield _sse_event(
            "done",
            {
                "case": case_payload,
                "user_message": user_message_payload,
                "assistant_message": assistant_payload,
                "classification": ai_result.classification,
                "structured": structured,
                "suggested_next_step": ai_result.suggested_next_step,
                "demo_mode": ai_result.demo_mode,
            },
        )
    except Exception:
        yield _sse_event(
            "error",
            {"detail": "回复生成失败，请稍后重试。"},
        )


@router.post("/{case_id}/consultations/stream")
async def consult_case_stream(
    case_id: int,
    payload: MessageCreate,
    session: DbSession,
    user: CompleteWorkerProfile,
) -> StreamingResponse:
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
    await session.commit()
    await session.refresh(user_message)
    initial_case_payload = CaseRead.model_validate(case).model_dump(mode="json")
    user_message_payload = MessageRead.model_validate(user_message).model_dump(
        mode="json"
    )

    async def event_stream() -> AsyncIterator[str]:
        async for chunk in _run_consult_stream(
            case,
            conversation,
            user_message,
            history,
            payload,
            user,
            initial_case_payload=initial_case_payload,
            user_message_payload=user_message_payload,
            action="case.consultation",
        ):
            yield chunk

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/consult/stream")
async def consult_auto_create_stream(
    payload: MessageCreate,
    session: DbSession,
    user: CompleteWorkerProfile,
) -> StreamingResponse:
    """自动建案 + 流式回复，供未创建案件的用户直接打开首页即咨询。"""
    title = payload.message.strip()[:30] or "新的劳动纠纷咨询"
    case = Case(
        owner_id=user.id,
        title=title,
        dispute_type="labor_other",
        stage="intake",
        status="active",
        facts=payload.message,
        summary=payload.message[:180],
    )
    session.add(case)
    await session.flush()

    conversation = Conversation(case_id=case.id)
    session.add(conversation)
    await session.flush()

    history: list[Message] = []
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=payload.message,
    )
    session.add(user_message)
    await session.commit()
    await session.refresh(user_message)

    initial_case_payload = CaseRead.model_validate(case).model_dump(mode="json")
    user_message_payload = MessageRead.model_validate(user_message).model_dump(
        mode="json"
    )

    async def event_stream() -> AsyncIterator[str]:
        async for chunk in _run_consult_stream(
            case,
            conversation,
            user_message,
            history,
            payload,
            user,
            initial_case_payload=initial_case_payload,
            user_message_payload=user_message_payload,
            action="case.auto_created_consultation",
        ):
            yield chunk

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
