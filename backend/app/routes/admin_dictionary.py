"""管理端字典版本管理：草稿编辑、校验、发布与删除。

字典包发布后，meta/dictionary、AI 分类、证据规则和文书生成
会读取新内容；发布操作写入审计日志并清空运行时缓存。
"""

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from app.api.deps import DbSession, require_roles
from app.models.audit import AuditLog
from app.models.dictionary_version import DictionaryVersion
from app.models.user import User
from app.schemas.dictionary_admin import (
    DictionaryActiveResponse,
    DictionaryPackageContent,
    DictionaryPackageContentRequest,
    DictionaryVersionDetail,
    DictionaryVersionSummary,
    validate_dictionary_package,
)
from app.services.dictionary import (
    apply_package,
    dictionary_checksum,
    get_active_package,
    invalidate_cache,
)

router = APIRouter(prefix="/admin/dictionary", tags=["admin-dictionary"])

AdminUser = require_roles("admin")
AdminRequired = Annotated[User, Depends(AdminUser)]


@router.get("/versions", response_model=list[DictionaryVersionSummary])
async def list_dictionary_versions(
    session: DbSession,
    _: AdminRequired,
) -> list[DictionaryVersion]:
    return list(
        await session.scalars(
            select(DictionaryVersion).order_by(DictionaryVersion.version.desc())
        )
    )


@router.get("/active", response_model=DictionaryActiveResponse)
async def get_active_dictionary(
    session: DbSession,
    _: AdminRequired,
) -> DictionaryActiveResponse:
    content = await get_active_package(session)
    row = await session.scalar(
        select(DictionaryVersion)
        .where(DictionaryVersion.status == "published")
        .order_by(DictionaryVersion.id.desc())
    )
    return DictionaryActiveResponse(
        source="published" if row is not None else "default",
        version=row.version if row is not None else None,
        content=DictionaryPackageContent.model_validate(content),
    )


@router.get("/versions/{version_id}", response_model=DictionaryVersionDetail)
async def get_dictionary_version(
    version_id: int,
    session: DbSession,
    _: AdminRequired,
) -> DictionaryVersion:
    return await _get_version(session, version_id)


@router.post(
    "/versions",
    response_model=DictionaryVersionDetail,
    status_code=201,
)
async def create_dictionary_version(
    payload: DictionaryPackageContentRequest,
    session: DbSession,
    admin: AdminRequired,
) -> DictionaryVersion:
    _ensure_valid(payload.content)
    max_version = await session.scalar(
        select(func.max(DictionaryVersion.version))
    )
    content = payload.content.model_dump(mode="json")
    version = DictionaryVersion(
        version=(max_version or 0) + 1,
        status="draft",
        content=content,
        checksum=dictionary_checksum(content),
        created_by_id=admin.id,
    )
    session.add(version)
    await session.flush()
    _audit(session, admin.id, "admin.dictionary_version_created", version)
    await session.commit()
    await session.refresh(version)
    return version


@router.put("/versions/{version_id}", response_model=DictionaryVersionDetail)
async def update_dictionary_version(
    version_id: int,
    payload: DictionaryPackageContentRequest,
    session: DbSession,
    admin: AdminRequired,
) -> DictionaryVersion:
    version = await _get_version(session, version_id)
    if version.status != "draft":
        raise HTTPException(status_code=409, detail="已发布的字典版本不可修改")
    _ensure_valid(payload.content)
    content = payload.content.model_dump(mode="json")
    version.content = content
    version.checksum = dictionary_checksum(content)
    _audit(session, admin.id, "admin.dictionary_version_updated", version)
    await session.commit()
    await session.refresh(version)
    return version


@router.post(
    "/versions/{version_id}/publish",
    response_model=DictionaryVersionDetail,
)
async def publish_dictionary_version(
    version_id: int,
    session: DbSession,
    admin: AdminRequired,
) -> DictionaryVersion:
    version = await _get_version(session, version_id)
    if version.status != "draft":
        raise HTTPException(status_code=409, detail="只有草稿版本可以发布")
    _ensure_valid(DictionaryPackageContent.model_validate(version.content))

    previous = list(
        await session.scalars(
            select(DictionaryVersion).where(DictionaryVersion.status == "published")
        )
    )
    for item in previous:
        item.status = "retired"

    version.status = "published"
    version.published_at = datetime.now(UTC)
    _audit(session, admin.id, "admin.dictionary_version_published", version)
    await session.commit()
    await session.refresh(version)

    # 提交成功后再应用到运行时并清缓存，保证读到的是已落库内容。
    apply_package(dict(version.content))
    invalidate_cache()
    return version


@router.delete("/versions/{version_id}", status_code=204)
async def delete_dictionary_version(
    version_id: int,
    session: DbSession,
    admin: AdminRequired,
) -> None:
    version = await _get_version(session, version_id)
    if version.status != "draft":
        raise HTTPException(status_code=409, detail="只有草稿版本可以删除")
    version_id_value = version.id
    version_number = version.version
    await session.delete(version)
    _audit(
        session,
        admin.id,
        "admin.dictionary_version_deleted",
        object_id=version_id_value,
        metadata={"version_number": version_number},
    )
    await session.commit()


async def _get_version(session: DbSession, version_id: int) -> DictionaryVersion:
    version = await session.get(DictionaryVersion, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="字典版本不存在")
    return version


def _ensure_valid(content: DictionaryPackageContent) -> None:
    errors = validate_dictionary_package(content)
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})


def _audit(
    session: DbSession,
    actor_id: int,
    action: str,
    version: DictionaryVersion | None = None,
    *,
    object_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = metadata or {}
    if version is not None:
        object_id = version.id
        payload = {
            "version_number": version.version,
            "status": version.status,
            **payload,
        }
    session.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            object_type="dictionary_version",
            object_id=object_id or 0,
            metadata_json=payload,
        )
    )
