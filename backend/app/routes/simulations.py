from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CompleteWorkerProfile, DbSession
from app.models.audit import AuditLog
from app.models.case import Case
from app.models.collaboration import SimulationMessage, SimulationSession
from app.models.user import User
from app.routes.cases import get_accessible_case
from app.schemas.simulation import (
    SimulationCreate,
    SimulationMessageCreate,
    SimulationMessageRead,
    SimulationReply,
    SimulationScore,
    SimulationSessionDetail,
    SimulationSessionRead,
)
from app.services.simulation import (
    generate_simulation_reply,
    score_simulation_message,
)

router = APIRouter(prefix="/cases", tags=["simulations"])


async def get_owned_case(
    case_id: int,
    session: DbSession,
    user: User,
) -> Case:
    case = await get_accessible_case(case_id, session, user)
    if case.owner_id != user.id:
        raise HTTPException(status_code=404, detail="案件不存在")
    return case


async def get_owned_simulation(
    case_id: int,
    session_id: int,
    session: DbSession,
    user: User,
) -> SimulationSession:
    await get_owned_case(case_id, session, user)
    simulation = await session.get(SimulationSession, session_id)
    if (
        simulation is None
        or simulation.case_id != case_id
        or simulation.user_id != user.id
    ):
        raise HTTPException(status_code=404, detail="模拟会话不存在")
    return simulation


def message_read(message: SimulationMessage) -> SimulationMessageRead:
    score = SimulationScore.model_validate(message.score) if message.score else None
    return SimulationMessageRead(
        id=message.id,
        role=message.role,
        content=message.content,
        score=score,
        created_at=message.created_at,
    )


@router.post(
    "/{case_id}/simulations",
    response_model=SimulationSessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_simulation(
    case_id: int,
    payload: SimulationCreate,
    session: DbSession,
    user: CompleteWorkerProfile,
) -> SimulationSession:
    case = await get_owned_case(case_id, session, user)
    simulation = SimulationSession(
        case_id=case.id,
        user_id=user.id,
        role_type=payload.role_type,
        scenario=payload.scenario,
    )
    session.add(simulation)
    await session.flush()
    session.add(
        AuditLog(
            actor_id=user.id,
            action="simulation.created",
            object_type="simulation",
            object_id=simulation.id,
            metadata_json={"case_id": case.id, "role_type": payload.role_type},
        )
    )
    await session.commit()
    await session.refresh(simulation)
    return simulation


@router.get(
    "/{case_id}/simulations",
    response_model=list[SimulationSessionRead],
)
async def list_simulations(
    case_id: int,
    session: DbSession,
    user: CompleteWorkerProfile,
) -> list[SimulationSession]:
    await get_owned_case(case_id, session, user)
    results = await session.scalars(
        select(SimulationSession)
        .where(
            SimulationSession.case_id == case_id,
            SimulationSession.user_id == user.id,
        )
        .order_by(SimulationSession.updated_at.desc())
    )
    return list(results)


@router.get(
    "/{case_id}/simulations/{session_id}",
    response_model=SimulationSessionDetail,
)
async def get_simulation(
    case_id: int,
    session_id: int,
    session: DbSession,
    user: CompleteWorkerProfile,
) -> SimulationSessionDetail:
    simulation = await get_owned_simulation(case_id, session_id, session, user)
    messages = list(
        await session.scalars(
            select(SimulationMessage)
            .where(SimulationMessage.session_id == simulation.id)
            .order_by(SimulationMessage.id)
        )
    )
    return SimulationSessionDetail(
        **SimulationSessionRead.model_validate(simulation).model_dump(),
        messages=[message_read(message) for message in messages],
    )


@router.post(
    "/{case_id}/simulations/{session_id}/messages",
    response_model=SimulationReply,
)
async def send_simulation_message(
    case_id: int,
    session_id: int,
    payload: SimulationMessageCreate,
    session: DbSession,
    user: CompleteWorkerProfile,
) -> SimulationReply:
    simulation = await get_owned_simulation(case_id, session_id, session, user)
    previous_count = len(
        list(
            await session.scalars(
                select(SimulationMessage.id).where(
                    SimulationMessage.session_id == simulation.id
                )
            )
        )
    )
    turn_count = previous_count // 2 + 1
    score = score_simulation_message(payload.content)
    user_message = SimulationMessage(
        session_id=simulation.id,
        role="user",
        content=payload.content,
        score=score,
    )
    assistant_message = SimulationMessage(
        session_id=simulation.id,
        role="assistant",
        content=await generate_simulation_reply(
            simulation.role_type,
            simulation.scenario,
            payload.content,
            turn_count,
        ),
        score={},
    )
    session.add_all([user_message, assistant_message])
    simulation.updated_at = datetime.now(UTC)
    session.add(
        AuditLog(
            actor_id=user.id,
            action="simulation.message_sent",
            object_type="simulation",
            object_id=simulation.id,
            metadata_json={"turn": turn_count, "overall": score["overall"]},
        )
    )
    await session.commit()
    await session.refresh(simulation)
    await session.refresh(user_message)
    await session.refresh(assistant_message)
    return SimulationReply(
        session=SimulationSessionRead.model_validate(simulation),
        user_message=message_read(user_message),
        assistant_message=message_read(assistant_message),
        score=SimulationScore.model_validate(score),
    )
