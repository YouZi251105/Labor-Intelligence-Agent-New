from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.collaboration import HelpResource
from app.models.lawyer import LawyerProfile
from app.models.user import User
from app.schemas.help import HelpResourceRead, SiteLawyerRead

router = APIRouter(prefix="/help", tags=["help"])


@router.get("/resources", response_model=list[HelpResourceRead])
async def list_help_resources(
    session: DbSession,
    _: CurrentUser,
) -> list[HelpResource]:
    results = await session.scalars(
        select(HelpResource)
        .where(HelpResource.status == "active")
        .order_by(HelpResource.resource_type, HelpResource.name)
    )
    return list(results)


@router.get("/site-lawyers", response_model=list[SiteLawyerRead])
async def list_site_lawyers(
    session: DbSession,
    _: CurrentUser,
) -> list[SiteLawyerRead]:
    rows = (
        await session.execute(
            select(User, LawyerProfile)
            .join(LawyerProfile, LawyerProfile.user_id == User.id)
            .where(
                User.role == "lawyer",
                User.is_active.is_(True),
                LawyerProfile.status == "active",
            )
            .order_by(User.display_name)
        )
    ).all()
    return [
        SiteLawyerRead(
            id=user.id,
            display_name=user.display_name or user.username,
            specialties=profile.specialties,
            bio=profile.bio,
            status=profile.status,
        )
        for user, profile in rows
    ]
