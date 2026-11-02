from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.audit import AuditLog
from app.models.evidence import Evidence
from app.routes.cases import get_accessible_case, get_worker_owned_case
from app.schemas.workflow import TransitionRequest, WorkflowResponse
from app.services.workflow import build_workflow

router = APIRouter(prefix="/cases", tags=["workflow"])


async def _workflow_for_case(
    case_id: int,
    session: DbSession,
    user: CurrentUser,
) -> WorkflowResponse:
    case = await get_accessible_case(case_id, session, user)
    evidence_items = list(
        await session.scalars(select(Evidence).where(Evidence.case_id == case_id))
    )
    return build_workflow(case, evidence_items)


@router.get("/{case_id}/workflow", response_model=WorkflowResponse)
async def get_case_workflow(
    case_id: int,
    session: DbSession,
    user: CurrentUser,
) -> WorkflowResponse:
    return await _workflow_for_case(case_id, session, user)


@router.post("/{case_id}/transitions", response_model=WorkflowResponse)
async def transition_case(
    case_id: int,
    payload: TransitionRequest,
    session: DbSession,
    user: CurrentUser,
) -> WorkflowResponse:
    case = await get_worker_owned_case(case_id, session, user)
    evidence_items = list(
        await session.scalars(select(Evidence).where(Evidence.case_id == case_id))
    )
    workflow = build_workflow(case, evidence_items)
    option = next(
        (
            item
            for item in workflow.options
            if item.target_stage == payload.target_stage
        ),
        None,
    )
    if option is None:
        raise HTTPException(
            status_code=400,
            detail=f"不允许从 {workflow.current_stage} 进入 {payload.target_stage}",
        )
    if not option.enabled:
        reasons = "、".join(option.blocked_reasons) or "前置条件未满足"
        raise HTTPException(status_code=400, detail=f"无法推进：{reasons}")

    previous_stage = case.stage
    case.stage = payload.target_stage
    session.add(
        AuditLog(
            actor_id=user.id,
            action="case.transitioned",
            object_type="case",
            object_id=case.id,
            metadata_json={
                "from_stage": previous_stage,
                "to_stage": payload.target_stage,
                "note": payload.note,
            },
        )
    )
    await session.commit()
    await session.refresh(case)
    return build_workflow(case, evidence_items)
