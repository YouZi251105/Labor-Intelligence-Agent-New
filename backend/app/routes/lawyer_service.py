from datetime import UTC, datetime, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select

from app.api.deps import CompleteWorkerProfile, CurrentUser, DbSession, require_roles
from app.models.audit import AuditLog
from app.models.case import Case
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.lawyer_service import (
    CaseReview,
    ConsultationMessage,
    ConsultationSession,
    LawyerRequest,
)
from app.models.user import User
from app.schemas.case import CaseRead
from app.schemas.document import DocumentRead
from app.schemas.evidence import EvidenceRead
from app.schemas.lawyer_service import (
    SLOT_LABELS,
    CaseReviewDecision,
    CaseReviewRead,
    CaseReviewSubmit,
    ConsultationMessageCreate,
    ConsultationMessageRead,
    ConsultationSessionRead,
    LawyerRequestAction,
    LawyerRequestCreate,
    LawyerRequestRead,
)
from app.services.evidence import assess_case_evidence

router = APIRouter(prefix="/lawyer-service", tags=["lawyer-service"])

LawyerUser = require_roles("lawyer")
LawyerRequired = Annotated[User, Depends(LawyerUser)]

ACTIVE_REQUEST_STATUSES = {"pending", "accepted"}
SLOT_ORDER = {"morning": 0, "afternoon": 1, "evening": 2}
LOCAL_TZ = ZoneInfo("Asia/Shanghai")


def _audit(
    actor_id: int,
    action: str,
    object_id: int,
    metadata: dict[str, object] | None = None,
) -> AuditLog:
    return AuditLog(
        actor_id=actor_id,
        action=action,
        object_type="lawyer_service",
        object_id=object_id,
        metadata_json=metadata or {},
    )


async def _owned_case(case_id: int, session: DbSession, user: User) -> Case:
    case = await session.get(Case, case_id)
    if case is None or case.owner_id != user.id:
        raise HTTPException(status_code=404, detail="案件不存在")
    return case


async def _get_request(request_id: int, session: DbSession) -> LawyerRequest:
    request = await session.get(LawyerRequest, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="预约不存在")
    return request


async def _get_session(session_id: int, session: DbSession) -> ConsultationSession:
    item = await session.get(ConsultationSession, session_id)
    if item is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return item


@router.post("/requests", response_model=LawyerRequestRead, status_code=201)
async def create_request(
    payload: LawyerRequestCreate,
    session: DbSession,
    user: CompleteWorkerProfile,
) -> LawyerRequest:
    case = await _owned_case(payload.case_id, session, user)
    active = await session.scalar(
        select(LawyerRequest.id)
        .where(
            LawyerRequest.case_id == case.id,
            LawyerRequest.status.in_(ACTIVE_REQUEST_STATUSES),
        )
        .limit(1)
    )
    if active is not None:
        raise HTTPException(status_code=409, detail="该案件已有进行中的律师服务预约")

    preferred_time = payload.preferred_time
    if payload.preferred_date is not None:
        today = datetime.now(LOCAL_TZ).date()
        if payload.preferred_date < today:
            raise HTTPException(status_code=400, detail="预约日期不能早于今天")
        if payload.preferred_date > today + timedelta(days=14):
            raise HTTPException(status_code=400, detail="预约日期最多提前 14 天")
        if payload.preferred_slot is not None:
            preferred_time = (
                f"{payload.preferred_date.month}月{payload.preferred_date.day}日 "
                f"{SLOT_LABELS[payload.preferred_slot]}"
            )

    request = LawyerRequest(
        case_id=case.id,
        user_id=user.id,
        reason=payload.reason,
        preferred_time=preferred_time,
        preferred_date=payload.preferred_date,
        preferred_slot=payload.preferred_slot,
        priority=payload.priority,
    )
    session.add(request)
    await session.flush()
    session.add(_audit(user.id, "lawyer_request.created", request.id))
    await session.commit()
    await session.refresh(request)
    return request


@router.get("/requests", response_model=list[LawyerRequestRead])
async def list_requests(session: DbSession, user: CurrentUser) -> list[LawyerRequest]:
    query = select(LawyerRequest).order_by(LawyerRequest.created_at.desc())
    if user.role == "user":
        query = query.where(LawyerRequest.user_id == user.id)
    elif user.role == "lawyer":
        query = query.where(
            or_(
                LawyerRequest.lawyer_id == user.id,
                LawyerRequest.lawyer_id.is_(None),
            )
        )
    results = await session.scalars(query)
    return list(results)


@router.patch("/requests/{request_id}", response_model=LawyerRequestRead)
async def act_request(
    request_id: int,
    payload: LawyerRequestAction,
    session: DbSession,
    user: LawyerRequired,
) -> LawyerRequest:
    request = await _get_request(request_id, session)
    if request.status != "pending":
        raise HTTPException(status_code=409, detail="该预约已处理，无法重复操作")

    if payload.accept:
        request.status = "accepted"
        request.lawyer_id = user.id
        request.accepted_at = datetime.now(UTC)
        case = await session.get(Case, request.case_id)
        if case is not None and case.assigned_lawyer_id is None:
            case.assigned_lawyer_id = user.id
        session.add(
            ConsultationSession(
                request_id=request.id,
                case_id=request.case_id,
                user_id=request.user_id,
                lawyer_id=user.id,
            )
        )
        session.add(_audit(user.id, "lawyer_request.accepted", request.id))
    else:
        request.status = "rejected"
        request.lawyer_id = user.id
        request.reject_reason = payload.reject_reason.strip()
        session.add(_audit(user.id, "lawyer_request.rejected", request.id))

    await session.commit()
    await session.refresh(request)
    return request


@router.post("/requests/{request_id}/cancel", response_model=LawyerRequestRead)
async def cancel_request(
    request_id: int,
    session: DbSession,
    user: CurrentUser,
) -> LawyerRequest:
    request = await _get_request(request_id, session)
    if user.role == "user" and request.user_id != user.id:
        raise HTTPException(status_code=404, detail="预约不存在")
    if request.status not in ACTIVE_REQUEST_STATUSES:
        raise HTTPException(status_code=409, detail="当前状态不可取消")

    request.status = "cancelled"
    if request.lawyer_id:
        _session = await session.scalar(
            select(ConsultationSession).where(
                ConsultationSession.request_id == request.id
            )
        )
        if _session and _session.status == "active":
            _session.status = "closed"
            _session.closed_at = datetime.now(UTC)
    session.add(_audit(user.id, "lawyer_request.cancelled", request.id))
    await session.commit()
    await session.refresh(request)
    return request


@router.get("/sessions", response_model=list[ConsultationSessionRead])
async def list_sessions(session: DbSession, user: CurrentUser) -> list[ConsultationSession]:
    query = select(ConsultationSession).order_by(ConsultationSession.created_at.desc())
    if user.role == "user":
        query = query.where(ConsultationSession.user_id == user.id)
    elif user.role == "lawyer":
        query = query.where(ConsultationSession.lawyer_id == user.id)
    results = await session.scalars(query)
    return list(results)


@router.get("/sessions/{session_id}/messages", response_model=list[ConsultationMessageRead])
async def list_messages(
    session_id: int,
    session: DbSession,
    user: CurrentUser,
) -> list[ConsultationMessage]:
    item = await _get_session(session_id, session)
    if item.user_id != user.id and item.lawyer_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")

    results = await session.scalars(
        select(ConsultationMessage)
        .where(ConsultationMessage.session_id == item.id)
        .order_by(ConsultationMessage.created_at.asc(), ConsultationMessage.id.asc())
    )
    return list(results)


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ConsultationMessageRead,
    status_code=201,
)
async def send_message(
    session_id: int,
    payload: ConsultationMessageCreate,
    session: DbSession,
    user: CurrentUser,
) -> ConsultationMessage:
    item = await _get_session(session_id, session)
    if item.status != "active":
        raise HTTPException(status_code=409, detail="会话已结束，无法继续发送消息")
    sender_role: str | None = None
    if user.role == "user" and item.user_id == user.id:
        sender_role = "user"
    elif user.role == "lawyer" and item.lawyer_id == user.id:
        sender_role = "lawyer"
    else:
        raise HTTPException(status_code=404, detail="会话不存在")

    message = ConsultationMessage(
        session_id=item.id,
        sender_role=sender_role,
        content=payload.content,
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


@router.post("/sessions/{session_id}/close", response_model=ConsultationSessionRead)
async def close_session(
    session_id: int,
    session: DbSession,
    user: CurrentUser,
) -> ConsultationSession:
    item = await _get_session(session_id, session)
    if item.user_id != user.id and item.lawyer_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    if item.status != "active":
        raise HTTPException(status_code=409, detail="会话已结束")

    item.status = "closed"
    item.closed_at = datetime.now(UTC)
    if item.request_id:
        request = await session.get(LawyerRequest, item.request_id)
        if request and request.status == "accepted":
            request.status = "completed"
            request.completed_at = datetime.now(UTC)
    session.add(_audit(user.id, "consultation.session.closed", item.id))
    await session.commit()
    await session.refresh(item)
    return item


@router.post("/cases/{case_id}/review", response_model=CaseReviewRead, status_code=201)
async def request_review(
    case_id: int,
    session: DbSession,
    user: CompleteWorkerProfile,
) -> CaseReview:
    case = await _owned_case(case_id, session, user)
    existing = await session.scalar(
        select(CaseReview).where(CaseReview.case_id == case.id)
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="该案件已有复核任务")

    review = CaseReview(case_id=case.id)
    session.add(review)
    await session.flush()
    session.add(_audit(user.id, "case.review.requested", review.id))
    await session.commit()
    await session.refresh(review)
    return review


@router.get("/cases/{case_id}/review", response_model=CaseReviewRead)
async def get_review(
    case_id: int,
    session: DbSession,
    user: CurrentUser,
) -> CaseReview:
    case = await session.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="案件不存在")
    allowed = case.owner_id == user.id or case.assigned_lawyer_id == user.id or user.role == "admin"
    if not allowed:
        raise HTTPException(status_code=404, detail="案件不存在")

    review = await session.scalar(select(CaseReview).where(CaseReview.case_id == case_id))
    if review is None:
        raise HTTPException(status_code=404, detail="尚无复核任务")
    return review


@router.post("/reviews/{review_id}/decision", response_model=CaseReviewRead)
async def record_review_decision(
    review_id: int,
    payload: CaseReviewDecision,
    session: DbSession,
    user: CompleteWorkerProfile,
) -> CaseReview:
    """复核结论出来后，用户选择后续方式：自行办理或律师协助。允许变更。"""
    review = await session.get(CaseReview, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="复核任务不存在")
    case = await session.get(Case, review.case_id)
    if case is None or case.owner_id != user.id:
        raise HTTPException(status_code=404, detail="复核任务不存在")
    if review.status != "reviewed":
        raise HTTPException(status_code=409, detail="复核完成后才能选择后续方式")

    review.user_decision = payload.decision
    review.user_decision_at = datetime.now(UTC)
    session.add(_audit(user.id, "case.review.decision", review.id))
    await session.commit()
    await session.refresh(review)
    return review


@router.get("/reviews/{review_id}/case-brief")
async def review_case_brief(
    review_id: int,
    session: DbSession,
    user: LawyerRequired,
) -> dict[str, object]:
    """复核案件简报：律师复核时查看案件概要、证据材料与文书清单。

    待分配的复核任务对所有律师开放；已分配的仅限承办律师。
    """
    review = await session.get(CaseReview, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="复核任务不存在")
    if review.lawyer_id is not None and review.lawyer_id != user.id:
        raise HTTPException(status_code=404, detail="复核任务不存在")

    case = await session.get(Case, review.case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="案件不存在")

    evidence_items = list(
        await session.scalars(
            select(Evidence)
            .where(Evidence.case_id == case.id)
            .order_by(Evidence.created_at.desc())
        )
    )
    documents = list(
        await session.scalars(
            select(Document)
            .where(Document.case_id == case.id)
            .order_by(Document.created_at.desc())
        )
    )
    return {
        "case": CaseRead.model_validate(case).model_dump(),
        "evidence": {
            "items": [
                EvidenceRead.model_validate(item).model_dump()
                for item in evidence_items
            ],
            "assessment": assess_case_evidence(case, evidence_items),
        },
        "documents": [
            DocumentRead.model_validate(document).model_dump()
            for document in documents
        ],
    }


@router.post("/reviews/{review_id}/submit", response_model=CaseReviewRead)
async def submit_review(
    review_id: int,
    payload: CaseReviewSubmit,
    session: DbSession,
    user: LawyerRequired,
) -> CaseReview:
    review = await session.get(CaseReview, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="复核任务不存在")
    if review.status != "pending":
        raise HTTPException(status_code=409, detail="该复核已处理")

    review.lawyer_id = user.id
    review.status = "reviewed"
    review.conclusion = payload.conclusion
    review.comment = payload.comment
    review.reviewed_at = datetime.now(UTC)
    case = await session.get(Case, review.case_id)
    if case is not None and case.assigned_lawyer_id is None:
        case.assigned_lawyer_id = user.id
    session.add(_audit(user.id, "case.review.completed", review.id))
    await session.commit()
    await session.refresh(review)
    return review


@router.get("/todos", response_model=dict)
async def lawyer_todos(session: DbSession, user: LawyerRequired) -> dict[str, object]:
    pending_requests = list(
        await session.scalars(
            select(LawyerRequest)
            .where(
                LawyerRequest.status == "pending",
                or_(
                    LawyerRequest.lawyer_id == user.id,
                    LawyerRequest.lawyer_id.is_(None),
                ),
            )
            .order_by(LawyerRequest.created_at.asc())
        )
    )
    pending_reviews = list(
        await session.scalars(
            select(CaseReview)
            .where(
                CaseReview.status == "pending",
                or_(
                    CaseReview.lawyer_id == user.id,
                    CaseReview.lawyer_id.is_(None),
                ),
            )
            .order_by(CaseReview.created_at.asc())
        )
    )
    pending_requests.sort(
        key=lambda r: (
            r.priority != "urgent",
            r.preferred_date is None,
            r.preferred_date or datetime.now(LOCAL_TZ).date(),
            SLOT_ORDER.get(r.preferred_slot or "", 99),
            r.created_at,
        )
    )
    return {
        "requests": [LawyerRequestRead.model_validate(r).model_dump() for r in pending_requests],
        "reviews": [CaseReviewRead.model_validate(r).model_dump() for r in pending_reviews],
        "cases": await _case_summaries(
            session, {r.case_id for r in pending_requests} | {r.case_id for r in pending_reviews}
        ),
    }


async def _case_summaries(
    session: DbSession,
    case_ids: set[int],
) -> dict[str, dict[str, object]]:
    if not case_ids:
        return {}
    rows = await session.execute(
        select(Case.id, Case.title, Case.dispute_type, Case.stage).where(
            Case.id.in_(case_ids)
        )
    )
    return {
        str(row.id): {
            "id": row.id,
            "title": row.title,
            "dispute_type": row.dispute_type,
            "stage": row.stage,
        }
        for row in rows
    }
