from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DbSession, require_roles
from app.models.audit import AuditLog
from app.models.rule_package import RulePackage
from app.models.user import User
from app.schemas.rule_package import (
    RulePackageAIGenerateRequest,
    RulePackageContentRequest,
    RulePackageDetail,
    RulePackageExcelErrorResponse,
    RulePackageReviewRequest,
    RulePackageSummary,
    RulePackageValidationResponse,
    RulePackageValidationSummary,
)
from app.services.rule_package_ai import (
    RulePackageAIError,
    RulePackageAIUnavailableError,
    generate_rule_package_draft,
)
from app.services.rule_package_document import export_rule_package_review_docx
from app.services.rule_package_excel import (
    RulePackageExcelError,
    export_rule_package_excel,
    import_rule_package_excel,
)
from app.services.rule_packages import (
    load_default_workflow_package,
    rule_package_checksum,
    validate_workflow_package,
)

router = APIRouter(prefix="/admin/rule-packages", tags=["admin-rule-packages"])

AdminUser = require_roles("admin")
AdminRequired = Annotated[User, Depends(AdminUser)]
EXCEL_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
MAX_EXCEL_BYTES = 5 * 1024 * 1024


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


@router.get("/template.xlsx", response_class=Response)
async def rule_package_excel_template(_: AdminRequired) -> Response:
    content = load_default_workflow_package().model_dump(mode="json")
    return _excel_response(
        export_rule_package_excel(content),
        "workflow-rule-package-template.xlsx",
    )


@router.post("/validate", response_model=RulePackageValidationResponse)
async def validate_rule_package(
    payload: RulePackageContentRequest,
    _: AdminRequired,
) -> RulePackageValidationResponse:
    package, errors = validate_workflow_package(payload.content)
    if package is None:
        return RulePackageValidationResponse(valid=False, errors=errors)
    block_types: dict[str, int] = {}
    if package.designer is not None:
        for block in package.designer.blocks.values():
            block_types[block.block_type] = block_types.get(block.block_type, 0) + 1
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
            block_count=len(package.designer.blocks) if package.designer else 0,
            block_types=block_types,
            review_status=package.review_status,
        ),
    )


@router.post(
    "/import-excel",
    response_model=RulePackageDetail,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "文件类型、大小或工作簿结构无效"},
        422: {
            "model": RulePackageExcelErrorResponse,
            "description": "Excel 字段、引用或规则结构无效",
        },
    },
)
async def import_rule_package_from_excel(
    session: DbSession,
    admin: AdminRequired,
    file: Annotated[UploadFile, File(description="规则包 Excel 工作簿")],
) -> RulePackage:
    filename = file.filename or ""
    if Path(filename).suffix.lower() != ".xlsx":
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 文件")
    data = await file.read(MAX_EXCEL_BYTES + 1)
    await file.close()
    if len(data) > MAX_EXCEL_BYTES:
        raise HTTPException(status_code=400, detail="Excel 文件不能超过 5 MiB")
    try:
        content = import_rule_package_excel(data)
    except RulePackageExcelError as error:
        raise HTTPException(
            status_code=422,
            detail={"errors": error.errors},
        ) from error
    package_model, errors = validate_workflow_package(content)
    if package_model is None:
        raise HTTPException(status_code=422, detail={"errors": errors})
    return await _create_draft(
        session,
        admin,
        package_model,
        package_model.model_dump(mode="json"),
    )


@router.post(
    "/ai-draft",
    response_model=RulePackageDetail,
    status_code=status.HTTP_201_CREATED,
    responses={
        422: {
            "model": RulePackageExcelErrorResponse,
            "description": "AI 输出未通过规则包结构校验",
        },
        503: {"description": "AI 服务未配置或暂时不可用"},
    },
)
async def generate_rule_package_from_ai(
    payload: RulePackageAIGenerateRequest,
    session: DbSession,
    admin: AdminRequired,
) -> RulePackage:
    try:
        package_model = await generate_rule_package_draft(payload.instruction)
    except RulePackageAIUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except RulePackageAIError as error:
        raise HTTPException(
            status_code=422,
            detail={"errors": error.errors},
        ) from error
    return await _create_draft(
        session,
        admin,
        package_model,
        package_model.model_dump(mode="json"),
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
    return await _create_draft(
        session,
        admin,
        package_model,
        package_model.model_dump(mode="json"),
    )


@router.get("/{package_id}/export.xlsx", response_class=Response)
async def export_rule_package(
    package_id: int,
    session: DbSession,
    _: AdminRequired,
) -> Response:
    package = await _get_package(session, package_id)
    safe_version = "".join(
        character if character.isalnum() or character in ".-_" else "-"
        for character in package.version
    )
    return _excel_response(
        export_rule_package_excel(package.content),
        f"workflow-rule-package-{safe_version or package.id}.xlsx",
    )


@router.get("/{package_id}/export.docx", response_class=Response)
async def export_rule_package_review(
    package_id: int,
    session: DbSession,
    _: AdminRequired,
) -> Response:
    package = await _get_package(session, package_id)
    safe_version = "".join(
        character if character.isalnum() or character in ".-_" else "-"
        for character in package.version
    )
    return Response(
        content=export_rule_package_review_docx(package.content),
        media_type=DOCX_MEDIA_TYPE,
        headers={
            "Content-Disposition": (
                f'attachment; filename="workflow-rule-package-'
                f'{safe_version or package.id}-review.docx"'
            ),
            "Cache-Control": "no-store",
        },
    )


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


async def _create_draft(
    session: DbSession,
    admin: User,
    package_model: Any,
    content: dict[str, Any],
) -> RulePackage:
    content = dict(content)
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


def _excel_response(content: bytes, filename: str) -> Response:
    return Response(
        content=content,
        media_type=EXCEL_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


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
