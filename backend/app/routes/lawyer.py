from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, require_roles
from app.models.case import Case
from app.models.user import User
from app.schemas.case import CaseRead

router = APIRouter(prefix="/lawyer", tags=["lawyer"])
LawyerUser = require_roles("lawyer")
LawyerRequired = Annotated[User, Depends(LawyerUser)]


@router.get("/cases", response_model=list[CaseRead])
async def lawyer_cases(
    session: DbSession,
    user: LawyerRequired,
) -> list[Case]:
    results = await session.scalars(
        select(Case)
        .where(Case.assigned_lawyer_id == user.id)
        .order_by(Case.updated_at.desc())
    )
    return list(results)
