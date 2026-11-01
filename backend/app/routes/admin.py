from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, require_roles
from app.core.security import hash_password
from app.models.audit import AuditLog
from app.models.case import Case
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.lawyer import LawyerProfile
from app.models.user import User
from app.schemas.admin import (
    CaseAssignmentRequest,
    LawyerSummary,
    PasswordResetRequest,
)
from app.schemas.auth import UserRead
from app.schemas.case import CaseRead

router = APIRouter(prefix="/admin", tags=["admin"])
AdminUser = require_roles("admin")
AdminRequired = Annotated[User, Depends(AdminUser)]


@router.get("/stats")
async def stats(session: DbSession, _: AdminRequired) -> dict[str, int]:
    user_count = await session.scalar(select(func.count()).select_from(User))
    case_count = await session.scalar(select(func.count()).select_from(Case))
    evidence_count = await session.scalar(select(func.count()).select_from(Evidence))
    document_count = await session.scalar(select(func.count()).select_from(Document))
    return {
        "users": user_count or 0,
        "cases": case_count or 0,
        "evidence": evidence_count or 0,
        "documents": document_count or 0,
    }


@router.get("/users", response_model=list[UserRead])
async def users(session: DbSession, _: AdminRequired) -> list[User]:
    results = await session.scalars(select(User).order_by(User.created_at.desc()))
    return list(results)


@router.post("/users/{user_id}/reset-password")
async def reset_password(
    user_id: int,
    payload: PasswordResetRequest,
    session: DbSession,
    admin: AdminRequired,
) -> dict[str, bool]:
    target = await session.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    target.password_hash = hash_password(payload.new_password)
    session.add(
        AuditLog(
            actor_id=admin.id,
            action="user.password_reset",
            object_type="user",
            object_id=target.id,
        )
    )
    await session.commit()
    return {"success": True}


@router.get("/lawyers", response_model=list[LawyerSummary])
async def lawyers(session: DbSession, _: AdminRequired) -> list[LawyerSummary]:
    rows = (
        await session.execute(
            select(User, LawyerProfile)
            .join(LawyerProfile, LawyerProfile.user_id == User.id)
            .where(User.role == "lawyer")
            .order_by(User.display_name.asc())
        )
    ).all()
    return [
        LawyerSummary(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            license_no=profile.license_no,
            specialties=profile.specialties,
            status=profile.status,
        )
        for user, profile in rows
    ]


@router.get("/cases", response_model=list[CaseRead])
async def cases(session: DbSession, _: AdminRequired) -> list[Case]:
    results = await session.scalars(select(Case).order_by(Case.updated_at.desc()))
    return list(results)


@router.post("/cases/{case_id}/assign", response_model=CaseRead)
async def assign_case(
    case_id: int,
    payload: CaseAssignmentRequest,
    session: DbSession,
    admin: AdminRequired,
) -> Case:
    case = await session.get(Case, case_id)
    lawyer = await session.get(User, payload.lawyer_id)
    if case is None:
        raise HTTPException(status_code=404, detail="案件不存在")
    if lawyer is None or lawyer.role != "lawyer" or not lawyer.is_active:
        raise HTTPException(status_code=400, detail="律师不存在或不可用")

    case.assigned_lawyer_id = lawyer.id
    case.stage = "lawyer_help"
    session.add(
        AuditLog(
            actor_id=admin.id,
            action="case.assigned",
            object_type="case",
            object_id=case.id,
            metadata_json={"lawyer_id": lawyer.id},
        )
    )
    await session.commit()
    await session.refresh(case)
    return case
