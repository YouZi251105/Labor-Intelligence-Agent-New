from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import DbSession, require_roles
from app.models.audit import AuditLog
from app.models.case import Case
from app.models.collaboration import (
    LawyerOpinion,
    RevenueLedger,
    ServiceRecord,
)
from app.models.user import User
from app.schemas.collaboration import (
    LawyerOpinionCreate,
    LawyerOpinionRead,
    RevenueLedgerCreate,
    RevenueLedgerRead,
    RevenueStatusUpdate,
    ServiceRecordCreate,
    ServiceRecordRead,
    ServiceStatusUpdate,
)
from app.services.collaboration import (
    validate_revenue_transition,
    validate_service_transition,
)

router = APIRouter(prefix="/lawyer", tags=["lawyer-collaboration"])
admin_router = APIRouter(prefix="/admin", tags=["admin-collaboration"])

LawyerUser = require_roles("lawyer")
LawyerRequired = Annotated[User, Depends(LawyerUser)]
AdminUser = require_roles("admin")
AdminRequired = Annotated[User, Depends(AdminUser)]


async def get_assigned_case(
    case_id: int,
    session: DbSession,
    lawyer: User,
) -> Case:
    case = await session.get(Case, case_id)
    if case is None or case.assigned_lawyer_id != lawyer.id:
        raise HTTPException(status_code=404, detail="案件不存在")
    return case


@router.get("/opinions", response_model=list[LawyerOpinionRead])
async def list_opinions(
    session: DbSession,
    lawyer: LawyerRequired,
    case_id: int | None = Query(default=None),
) -> list[LawyerOpinion]:
    query = select(LawyerOpinion).where(LawyerOpinion.lawyer_id == lawyer.id)
    if case_id is not None:
        await get_assigned_case(case_id, session, lawyer)
        query = query.where(LawyerOpinion.case_id == case_id)
    results = await session.scalars(query.order_by(LawyerOpinion.created_at.desc()))
    return list(results)


@router.post(
    "/cases/{case_id}/opinions",
    response_model=LawyerOpinionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_opinion(
    case_id: int,
    payload: LawyerOpinionCreate,
    session: DbSession,
    lawyer: LawyerRequired,
) -> LawyerOpinion:
    case = await get_assigned_case(case_id, session, lawyer)
    opinion = LawyerOpinion(
        case_id=case.id,
        lawyer_id=lawyer.id,
        content=payload.content,
        status="submitted",
    )
    session.add(opinion)
    await session.flush()
    session.add(
        AuditLog(
            actor_id=lawyer.id,
            action="lawyer.opinion_created",
            object_type="lawyer_opinion",
            object_id=opinion.id,
            metadata_json={"case_id": case.id},
        )
    )
    await session.commit()
    await session.refresh(opinion)
    return opinion


@router.get("/service-records", response_model=list[ServiceRecordRead])
async def list_service_records(
    session: DbSession,
    lawyer: LawyerRequired,
) -> list[ServiceRecord]:
    results = await session.scalars(
        select(ServiceRecord)
        .where(ServiceRecord.lawyer_id == lawyer.id)
        .order_by(ServiceRecord.created_at.desc())
    )
    return list(results)


@router.post(
    "/service-records",
    response_model=ServiceRecordRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_service_record(
    payload: ServiceRecordCreate,
    session: DbSession,
    lawyer: LawyerRequired,
) -> ServiceRecord:
    case = await get_assigned_case(payload.case_id, session, lawyer)
    record = ServiceRecord(
        case_id=case.id,
        lawyer_id=lawyer.id,
        service_type=payload.service_type,
        summary=payload.summary,
        duration_minutes=payload.duration_minutes,
        status="pending",
    )
    session.add(record)
    await session.flush()
    session.add(
        AuditLog(
            actor_id=lawyer.id,
            action="lawyer.service_record_created",
            object_type="service_record",
            object_id=record.id,
            metadata_json={"case_id": case.id},
        )
    )
    await session.commit()
    await session.refresh(record)
    return record


@router.patch(
    "/service-records/{record_id}/status",
    response_model=ServiceRecordRead,
)
async def update_service_status(
    record_id: int,
    payload: ServiceStatusUpdate,
    session: DbSession,
    lawyer: LawyerRequired,
) -> ServiceRecord:
    record = await session.get(ServiceRecord, record_id)
    if record is None or record.lawyer_id != lawyer.id:
        raise HTTPException(status_code=404, detail="服务记录不存在")
    validate_service_transition(record.status, payload.status)
    previous = record.status
    record.status = payload.status
    session.add(
        AuditLog(
            actor_id=lawyer.id,
            action="lawyer.service_record_status_changed",
            object_type="service_record",
            object_id=record.id,
            metadata_json={"from": previous, "to": payload.status},
        )
    )
    await session.commit()
    await session.refresh(record)
    return record


@router.get("/revenue", response_model=list[RevenueLedgerRead])
async def list_revenue(
    session: DbSession,
    lawyer: LawyerRequired,
) -> list[RevenueLedger]:
    results = await session.scalars(
        select(RevenueLedger)
        .where(RevenueLedger.lawyer_id == lawyer.id)
        .order_by(RevenueLedger.created_at.desc())
    )
    return list(results)


@router.post(
    "/revenue",
    response_model=RevenueLedgerRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_revenue(
    payload: RevenueLedgerCreate,
    session: DbSession,
    lawyer: LawyerRequired,
) -> RevenueLedger:
    if payload.case_id is not None:
        await get_assigned_case(payload.case_id, session, lawyer)
    if payload.service_record_id is not None:
        record = await session.get(ServiceRecord, payload.service_record_id)
        if record is None or record.lawyer_id != lawyer.id:
            raise HTTPException(status_code=400, detail="服务记录不存在")

    entry = RevenueLedger(
        lawyer_id=lawyer.id,
        case_id=payload.case_id,
        service_record_id=payload.service_record_id,
        amount_cents=payload.amount_cents,
        entry_type=payload.entry_type,
        status="pending",
        note=payload.note,
    )
    session.add(entry)
    await session.flush()
    session.add(
        AuditLog(
            actor_id=lawyer.id,
            action="lawyer.revenue_created",
            object_type="revenue_ledger",
            object_id=entry.id,
            metadata_json={"amount_cents": entry.amount_cents},
        )
    )
    await session.commit()
    await session.refresh(entry)
    return entry


@admin_router.get("/service-records", response_model=list[ServiceRecordRead])
async def admin_service_records(
    session: DbSession,
    _: AdminRequired,
) -> list[ServiceRecord]:
    results = await session.scalars(
        select(ServiceRecord).order_by(ServiceRecord.created_at.desc())
    )
    return list(results)


@admin_router.get("/revenue", response_model=list[RevenueLedgerRead])
async def admin_revenue(
    session: DbSession,
    _: AdminRequired,
) -> list[RevenueLedger]:
    results = await session.scalars(
        select(RevenueLedger).order_by(RevenueLedger.created_at.desc())
    )
    return list(results)


@admin_router.patch(
    "/revenue/{entry_id}/status",
    response_model=RevenueLedgerRead,
)
async def admin_update_revenue_status(
    entry_id: int,
    payload: RevenueStatusUpdate,
    session: DbSession,
    admin: AdminRequired,
) -> RevenueLedger:
    entry = await session.get(RevenueLedger, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="收益记录不存在")
    validate_revenue_transition(entry.status, payload.status)
    previous = entry.status
    entry.status = payload.status
    session.add(
        AuditLog(
            actor_id=admin.id,
            action="admin.revenue_status_changed",
            object_type="revenue_ledger",
            object_id=entry.id,
            metadata_json={"from": previous, "to": payload.status},
        )
    )
    await session.commit()
    await session.refresh(entry)
    return entry
