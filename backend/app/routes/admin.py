from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select

from app.api.deps import DbSession, require_roles
from app.core.security import hash_password
from app.models.audit import AuditLog
from app.models.case import Case
from app.models.collaboration import RuleConfig, UserProfile
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.lawyer import LawyerProfile
from app.models.user import User
from app.schemas.admin import (
    AdminUserUpdate,
    AuditLogRead,
    CaseAssignmentRequest,
    LawyerStatusUpdate,
    LawyerSummary,
    MaterialSummary,
    PasswordResetRequest,
    RuleConfigRead,
    RuleReviewUpdate,
    VerificationStatusUpdate,
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


@router.patch("/users/{user_id}/status", response_model=UserRead)
async def update_user_status(
    user_id: int,
    payload: AdminUserUpdate,
    session: DbSession,
    admin: AdminRequired,
) -> User:
    target = await session.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if payload.is_active is None:
        raise HTTPException(status_code=400, detail="请提供账号状态")
    if payload.role is not None and payload.role != target.role:
        raise HTTPException(status_code=400, detail="角色调整需通过独立流程处理")
    if target.id == admin.id and not payload.is_active:
        raise HTTPException(status_code=400, detail="不能停用当前管理员账号")
    if target.role == "admin" and not payload.is_active:
        raise HTTPException(status_code=400, detail="管理员账号需完成交接后停用")

    target.is_active = payload.is_active
    session.add(
        AuditLog(
            actor_id=admin.id,
            action="admin.user_status_changed",
            object_type="user",
            object_id=target.id,
            metadata_json={"is_active": target.is_active},
        )
    )
    await session.commit()
    await session.refresh(target)
    return target


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


@router.get("/materials", response_model=list[MaterialSummary])
async def materials(
    session: DbSession,
    _: AdminRequired,
) -> list[MaterialSummary]:
    rows = list(
        await session.scalars(select(Evidence).order_by(Evidence.created_at.desc()))
    )
    return [
        MaterialSummary(
            id=item.id,
            case_id=item.case_id,
            filename=item.filename,
            content_type=item.content_type,
            file_size=item.file_size,
            category=item.category,
            screening_status=item.screening_status,
            extraction_status=item.extraction_status,
            created_at=item.created_at,
        )
        for item in rows
    ]


@router.get("/audit-logs", response_model=list[AuditLogRead])
async def audit_logs(
    session: DbSession,
    _: AdminRequired,
    action: str | None = Query(default=None),
    object_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[AuditLog]:
    query = select(AuditLog)
    if action:
        query = query.where(AuditLog.action == action)
    if object_type:
        query = query.where(AuditLog.object_type == object_type)
    results = await session.scalars(
        query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    )
    return list(results)


@router.get("/rules", response_model=list[RuleConfigRead])
async def rules(session: DbSession, _: AdminRequired) -> list[RuleConfig]:
    results = await session.scalars(
        select(RuleConfig).order_by(RuleConfig.dispute_type, RuleConfig.version.desc())
    )
    return list(results)


@router.patch("/rules/{rule_id}", response_model=RuleConfigRead)
async def review_rule(
    rule_id: int,
    payload: RuleReviewUpdate,
    session: DbSession,
    admin: AdminRequired,
) -> RuleConfig:
    rule = await session.get(RuleConfig, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="规则不存在")
    previous = rule.review_status
    rule.review_status = payload.review_status
    rule.source_note = payload.source_note
    session.add(
        AuditLog(
            actor_id=admin.id,
            action="admin.rule_reviewed",
            object_type="rule_config",
            object_id=rule.id,
            metadata_json={"from": previous, "to": payload.review_status},
        )
    )
    await session.commit()
    await session.refresh(rule)
    return rule


@router.patch("/lawyers/{user_id}/status", response_model=LawyerSummary)
async def update_lawyer_status(
    user_id: int,
    payload: LawyerStatusUpdate,
    session: DbSession,
    admin: AdminRequired,
) -> LawyerSummary:
    lawyer = await session.get(User, user_id)
    profile = await session.scalar(
        select(LawyerProfile).where(LawyerProfile.user_id == user_id)
    )
    if lawyer is None or lawyer.role != "lawyer" or profile is None:
        raise HTTPException(status_code=404, detail="律师不存在")
    profile.status = payload.status
    lawyer.is_active = payload.status != "suspended"
    session.add(
        AuditLog(
            actor_id=admin.id,
            action="admin.lawyer_status_changed",
            object_type="user",
            object_id=lawyer.id,
            metadata_json={"status": payload.status},
        )
    )
    await session.commit()
    return LawyerSummary(
        id=lawyer.id,
        username=lawyer.username,
        display_name=lawyer.display_name,
        license_no=profile.license_no,
        specialties=profile.specialties,
        status=profile.status,
    )


@router.patch("/users/{user_id}/verification")
async def update_verification(
    user_id: int,
    payload: VerificationStatusUpdate,
    session: DbSession,
    admin: AdminRequired,
) -> dict[str, str]:
    profile = await session.scalar(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="个人资料不存在")
    profile.verification_status = payload.verification_status
    session.add(
        AuditLog(
            actor_id=admin.id,
            action="admin.verification_status_changed",
            object_type="user_profile",
            object_id=user_id,
            metadata_json={"status": payload.verification_status},
        )
    )
    await session.commit()
    return {"verification_status": payload.verification_status}
