from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DbSession, require_roles
from app.models.audit import AuditLog
from app.models.rule_package import RulePackage
from app.models.user import User
from app.schemas.rule_package import (
    RulePackageContentRequest,
    RulePackageDetail,
    RulePackageReviewRequest,
    RulePackageSummary,
    RulePackageValidationResponse,
    RulePackageValidationSummary,
)
from app.services.rule_packages import (
    load_default_workflow_package,
    rule_package_checksum,
    validate_workflow_package,
)

router = APIRouter(prefix="/admin/rule-packages", tags=["admin-rule-packages"])

AdminUser = require_roles("admin")
AdminRequired = Annotated[User, Depends(AdminUser)]


@router.get("", response_model=list[RulePackageSummary])
async def list_rule_packages(
    session: DbSession,
    _: AdminRequired,
) -> list[RulePackage]:
    return list(
        await session.scalars(
            select(RulePackage).order_by(
                RulePackage.package_id,
                RulePackage.created_at.desc(),
            )
        )
    )


@router.get("/template")
async def rule_package_template(_: AdminRequired) -> dict[str, Any]:
    return load_default_workflow_package().model_dump(mode="json")


@router.post("/validate", response_model=RulePackageValidationResponse)
async def validate_rule_package(
    payload: RulePackageContentRequest,
    _: AdminRequired,
) -> RulePackageValidationResponse:
    package, errors = validate_workflow_package(payload.content)
    if package is None:
        return RulePackageValidationResponse(valid=False, errors=errors)
    return RulePackageValidationResponse(
        valid=True,
        summary=RulePackageValidationSummary(
            package_id=package.package_id,
            version=package.version,
            jurisdiction=package.jurisdiction,
            start_node=package.start_node,
            stage_count=len(package.stages),
            node_count=len(package.nodes),
            option_count=sum(len(node.options) for node in package.nodes.values()),
            review_status=package.review_status,
        ),
    )


@router.post(
    "/import",
    response_model=RulePackageDetail,
    status_code=status.HTTP_201_CREATED,
)
async def import_rule_package(
    payload: RulePackageContentRequest,
    session: DbSession,
    admin: AdminRequired,
) -> RulePackage:
    package_model, errors = validate_workflow_package(payload.content)
    if package_model is None:
        raise HTTPException(status_code=422, detail=errors)
    content = package_model.model_dump(mode="json")
    content["review_status"] = "draft"
    package = RulePackage(
        package_type="workflow",
        package_id=package_model.package_id,
        version=package_model.version,
        status="draft",
        content=content,
        checksum=rule_package_checksum(content),
        created_by_id=admin.id,
    )
    session.add(package)
    try:
        await session.flush()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(status_code=409, detail="规则包版本已存在") from error
    _audit(session, admin.id, "admin.rule_package_imported", package)
    await session.commit()
    await session.refresh(package)
    return package


@router.get("/{package_id}", response_model=RulePackageDetail)
async def get_rule_package(
    package_id: int,
    session: DbSession,
    _: AdminRequired,
) -> RulePackage:
    return await _get_package(session, package_id)


@router.put("/{package_id}", response_model=RulePackageDetail)
async def update_rule_package(
    package_id: int,
    payload: RulePackageContentRequest,
    session: DbSession,
    admin: AdminRequired,
) -> RulePackage:
    package = await _get_package(session, package_id)
    if package.status not in {"draft", "rejected"}:
        raise HTTPException(status_code=409, detail="当前状态不允许修改内容")
    package_model, errors = validate_workflow_package(payload.content)
    if package_model is None:
        raise HTTPException(status_code=422, detail=errors)
    content = package_model.model_dump(mode="json")
    content["review_status"] = package.status
    package.package_id = package_model.package_id
    package.version = package_model.version
    package.content = content
    package.checksum = rule_package_checksum(content)
    _audit(session, admin.id, "admin.rule_package_updated", package)
    await session.commit()
    await session.refresh(package)
    return package


@router.post("/{package_id}/submit", response_model=RulePackageDetail)
async def submit_rule_package(
    package_id: int,
    session: DbSession,
    admin: AdminRequired,
) -> RulePackage:
    package = await _get_package(session, package_id)
    return await _transition(
        session,
        package,
        admin.id,
        allowed={"draft", "rejected"},
        target="pending_review",
        action="admin.rule_package_submitted",
    )


@router.post("/{package_id}/review", response_model=RulePackageDetail)
async def review_rule_package(
    package_id: int,
    payload: RulePackageReviewRequest,
    session: DbSession,
    admin: AdminRequired,
) -> RulePackage:
    package = await _get_package(session, package_id)
    package = await _transition(
        session,
        package,
        admin.id,
        allowed={"pending_review"},
        target=payload.decision,
        action="admin.rule_package_reviewed",
        note=payload.note,
    )
    package.reviewed_by_id = admin.id
    await session.commit()
    await session.refresh(package)
    return package


@router.post("/{package_id}/publish", response_model=RulePackageDetail)
async def publish_rule_package(
    package_id: int,
    session: DbSession,
    admin: AdminRequired,
) -> RulePackage:
    package = await _get_package(session, package_id)
    previous_packages = list(
        await session.scalars(
            select(RulePackage).where(
                RulePackage.package_id == package.package_id,
                RulePackage.status == "published",
                RulePackage.id != package.id,
            )
        )
    )
    for previous in previous_packages:
        _set_status(previous, "retired")
    package = await _transition(
        session,
        package,
        admin.id,
        allowed={"approved"},
        target="published",
        action="admin.rule_package_published",
    )
    package.published_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(package)
    return package


@router.post("/{package_id}/retire", response_model=RulePackageDetail)
async def retire_rule_package(
    package_id: int,
    session: DbSession,
    admin: AdminRequired,
) -> RulePackage:
    package = await _get_package(session, package_id)
    return await _transition(
        session,
        package,
        admin.id,
        allowed={"published"},
        target="retired",
        action="admin.rule_package_retired",
    )


async def _get_package(session: DbSession, package_id: int) -> RulePackage:
    package = await session.get(RulePackage, package_id)
    if package is None:
        raise HTTPException(status_code=404, detail="规则包不存在")
    return package


async def _transition(
    session: DbSession,
    package: RulePackage,
    actor_id: int,
    *,
    allowed: set[str],
    target: str,
    action: str,
    note: str = "",
) -> RulePackage:
    if package.status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"不能从 {package.status} 转换为 {target}",
        )
    _set_status(package, target)
    _audit(session, actor_id, action, package, note)
    await session.commit()
    await session.refresh(package)
    return package


def _set_status(package: RulePackage, target: str) -> None:
    content = dict(package.content)
    content["review_status"] = target
    package.content = content
    package.status = target
    package.checksum = rule_package_checksum(content)


def _audit(
    session: DbSession,
    actor_id: int,
    action: str,
    package: RulePackage,
    note: str = "",
) -> None:
    session.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            object_type="rule_package",
            object_id=package.id,
            metadata_json={
                "package_id": package.package_id,
                "version": package.version,
                "status": package.status,
                "note": note,
            },
        )
    )
