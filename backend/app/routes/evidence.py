import hashlib
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.audit import AuditLog
from app.models.evidence import Evidence
from app.routes.cases import get_accessible_case
from app.schemas.evidence import (
    ContractReviewRequest,
    ContractReviewResponse,
    EvidenceRead,
)
from app.services.evidence import (
    assess_case_evidence,
    detect_category,
    review_contract,
    save_upload,
)

router = APIRouter(prefix="/cases", tags=["evidence"])


@router.get("/{case_id}/evidence")
async def list_case_evidence(
    case_id: int,
    session: DbSession,
    user: CurrentUser,
) -> dict:
    case = await get_accessible_case(case_id, session, user)
    results = await session.scalars(
        select(Evidence)
        .where(Evidence.case_id == case_id)
        .order_by(Evidence.created_at.desc())
    )
    evidence_items = list(results)
    return {
        "items": [EvidenceRead.model_validate(item) for item in evidence_items],
        "assessment": assess_case_evidence(case, evidence_items),
    }


@router.post(
    "/{case_id}/evidence",
    response_model=EvidenceRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_case_evidence(
    case_id: int,
    session: DbSession,
    user: CurrentUser,
    file: UploadFile = File(...),
) -> Evidence:
    case = await get_accessible_case(case_id, session, user)
    filename = Path(file.filename or "未命名材料").name
    content = await file.read()
    digest = hashlib.sha256(content).hexdigest()
    duplicate = await session.scalar(
        select(Evidence).where(
            Evidence.case_id == case_id,
            Evidence.sha256 == digest,
        )
    )
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="该材料已经上传")

    try:
        stored_path, digest = save_upload(case_id, filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    text_content = ""
    if stored_path.suffix.lower() == ".txt":
        try:
            text_content = content.decode("utf-8")
        except UnicodeDecodeError:
            text_content = content.decode("utf-8", errors="ignore")

    category = detect_category(filename, file.content_type or "", text_content)
    evidence = Evidence(
        case_id=case_id,
        uploader_id=user.id,
        filename=filename,
        stored_path=str(stored_path),
        content_type=file.content_type or "application/octet-stream",
        file_size=len(content),
        sha256=digest,
        category=category,
        text_content=text_content,
    )
    session.add(evidence)
    await session.flush()

    all_evidence = list(
        await session.scalars(select(Evidence).where(Evidence.case_id == case_id))
    )
    evidence.assessment = assess_case_evidence(case, all_evidence)
    case.stage = "evidence"
    session.add(
        AuditLog(
            actor_id=user.id,
            action="evidence.uploaded",
            object_type="evidence",
            object_id=evidence.id,
            metadata_json={"category": category, "sha256": digest},
        )
    )
    await session.commit()
    await session.refresh(evidence)
    return evidence


@router.post("/{case_id}/contract-review", response_model=ContractReviewResponse)
async def review_case_contract(
    case_id: int,
    payload: ContractReviewRequest,
    session: DbSession,
    user: CurrentUser,
) -> dict:
    case = await get_accessible_case(case_id, session, user)
    result = review_contract(payload.text)
    session.add(
        AuditLog(
            actor_id=user.id,
            action="contract.reviewed",
            object_type="case",
            object_id=case.id,
            metadata_json={"risk_level": result["risk_level"]},
        )
    )
    await session.commit()
    return result
