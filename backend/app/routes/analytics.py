from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.models.case import Case
from app.schemas.analytics import (
    HistoryCaseSummary,
    HistoryResponse,
    TopicsResponse,
    TopicSummary,
)
from app.services.ai import DISPUTE_LABELS

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/topics", response_model=TopicsResponse)
async def topic_summary(session: DbSession, _: CurrentUser) -> TopicsResponse:
    rows = (
        await session.execute(
            select(Case.dispute_type, func.count(Case.id))
            .group_by(Case.dispute_type)
            .order_by(func.count(Case.id).desc())
        )
    ).all()
    topics = [
        TopicSummary(
            dispute_type=dispute_type,
            label=DISPUTE_LABELS.get(dispute_type, dispute_type),
            count=count,
        )
        for dispute_type, count in rows
    ]
    return TopicsResponse(topics=topics, total=sum(item.count for item in topics))


@router.get("/history", response_model=HistoryResponse)
async def user_history(session: DbSession, user: CurrentUser) -> HistoryResponse:
    if user.role == "admin":
        query = select(Case)
    elif user.role == "lawyer":
        query = select(Case).where(Case.assigned_lawyer_id == user.id)
    else:
        query = select(Case).where(Case.owner_id == user.id)
    cases = list(
        await session.scalars(query.order_by(Case.updated_at.desc()).limit(50))
    )
    return HistoryResponse(
        cases=[
            HistoryCaseSummary(
                case_id=item.id,
                title=item.title,
                dispute_type=item.dispute_type,
                stage=item.stage,
                summary=item.summary,
                updated_at=item.updated_at,
            )
            for item in cases
        ]
    )
