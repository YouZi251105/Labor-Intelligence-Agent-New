"""证据四性评估接口（开发 B 定义并实现）。"""

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.evidence import Evidence
from app.routes.cases import get_accessible_case
from app.schemas.evidence_rules import EvidenceAssessmentResponse
from app.services.evidence_rules import assess_evidence_rules

router = APIRouter(prefix="/cases", tags=["evidence"])


@router.get(
    "/{case_id}/evidence-assessment",
    response_model=EvidenceAssessmentResponse,
)
async def get_evidence_assessment(
    case_id: int,
    session: DbSession,
    user: CurrentUser,
) -> EvidenceAssessmentResponse:
    case = await get_accessible_case(case_id, session, user)
    items = list(
        await session.scalars(select(Evidence).where(Evidence.case_id == case_id))
    )
    structured_items = [
        {
            "category": item.category,
            "screening_status": item.screening_status,
            "filename": item.filename,
            "content_type": item.content_type,
            "file_size": item.file_size,
        }
        for item in items
    ]
    result = assess_evidence_rules(case.dispute_type, structured_items)
    return EvidenceAssessmentResponse(
        case_id=case.id,
        dispute_type=case.dispute_type,
        legality=result["legality"],
        relevance=result["relevance"],
        sufficiency=result["sufficiency"],
        completeness=result["completeness"],
        disclaimer=result["disclaimer"],
    )
