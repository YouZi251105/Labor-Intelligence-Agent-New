import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.api.deps import DbSession, require_roles
from app.core.config import get_settings
from app.models.audit import AuditLog
from app.models.collaboration import UserProfile
from app.models.user import User
from app.schemas.profile import UserProfileRead, UserProfileUpdate
from app.services.profile import mask_identity_number

router = APIRouter(prefix="/users/me", tags=["profile"])
WorkerUser = require_roles("user")
WorkerRequired = Annotated[User, Depends(WorkerUser)]


@router.get("/profile", response_model=UserProfileRead)
async def get_profile(session: DbSession, user: WorkerRequired) -> UserProfile:
    profile = await session.scalar(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="尚未补充个人资料")
    return profile


@router.put("/profile", response_model=UserProfileRead)
async def update_profile(
    payload: UserProfileUpdate,
    session: DbSession,
    user: WorkerRequired,
) -> UserProfile:
    masked = mask_identity_number(payload.id_number)
    if not masked:
        raise HTTPException(status_code=400, detail="身份证号格式无效")
    settings = get_settings()
    identity_hash = hashlib.sha256(
        f"{settings.secret_key}:{payload.id_number.upper()}".encode()
    ).hexdigest()
    profile = await session.scalar(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    if profile is None:
        profile = UserProfile(user_id=user.id)
        session.add(profile)

    profile.real_name = payload.real_name
    profile.phone = payload.phone
    profile.id_number_masked = masked
    profile.id_number_hash = identity_hash
    profile.verification_status = "pending"
    user.phone = payload.phone
    session.add(
        AuditLog(
            actor_id=user.id,
            action="user.profile_submitted",
            object_type="user_profile",
            object_id=user.id,
        )
    )
    await session.commit()
    await session.refresh(profile)
    return profile
