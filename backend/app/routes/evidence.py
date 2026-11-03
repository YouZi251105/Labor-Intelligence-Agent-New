import hashlib
from contextlib import suppress
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import quote

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from sqlalchemy import select

from app.api.deps import CompleteWorkerProfile, CurrentUser, DbSession
from app.core.config import get_settings
from app.models.audit import AuditLog
from app.models.document import DocumentEvidence
from app.models.evidence import Evidence
from app.routes.cases import get_accessible_case, get_worker_owned_case
from app.schemas.evidence import (
    ContractFileReviewResponse,
    ContractReviewRequest,
    ContractReviewResponse,
    EvidenceExtractionResponse,
    EvidenceRead,
)
from app.services.evidence import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    assess_case_evidence,
    detect_category,
    read_stored_content,
    review_contract,
    save_upload,
    validate_signature,
)
from app.services.evidence_forensics import analyze_image
from app.services.extraction import IMAGE_EXTENSIONS, ExtractionResult, extract_text_from_bytes
from app.services.jobs import dispatch_evidence_extraction
from app.services.storage import get_storage

router = APIRouter(prefix="/cases", tags=["evidence"])


def apply_extraction(evidence: Evidence, result: ExtractionResult) -> None:
    evidence.text_content = result.text
    evidence.screening_status = (
        "accepted" if result.status == "extracted" else "needs_review"
    )
    assessment = dict(evidence.assessment or {})
    assessment["extraction"] = result.as_assessment()
    evidence.assessment = assessment


@router.get("/{case_id}/evidence")
async def list_case_evidence(
    case_id: int,
    session: DbSession,
    user: CurrentUser,
) -> dict[str, Any]:
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
    user: CompleteWorkerProfile,
    file: Annotated[UploadFile, File()],
) -> Evidence:
    case = await get_worker_owned_case(case_id, session, user)
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

    extension = Path(filename).suffix.lower()
    forensics = None
    if extension in IMAGE_EXTENSIONS:
        forensics = analyze_image(filename, content)
        if forensics.suspicious:
            reasons = "；".join(forensics.reasons)
            raise HTTPException(
                status_code=422,
                detail=(
                    f"图片真实性初筛未通过：{reasons}。"
                    f"{forensics.disclaimer}"
                    "请上传未经拼接或涂抹的原始图片；如确有合理脱敏需要，请通过人工协助提交。"
                ),
            )

    try:
        stored_path, digest = save_upload(case_id, filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    extraction = extract_text_from_bytes(
        filename,
        content,
        file.content_type or "",
    )
    category = detect_category(filename, file.content_type or "", extraction.text)
    evidence = Evidence(
        case_id=case_id,
        uploader_id=user.id,
        filename=filename,
        stored_path=stored_path,
        content_type=file.content_type or "application/octet-stream",
        file_size=len(content),
        sha256=digest,
        category=category,
        text_content=extraction.text,
        screening_status=(
            "accepted" if extraction.status == "extracted" else "needs_review"
        ),
        assessment={
            "extraction": extraction.as_assessment(),
            **(
                {
                    "forensics": {
                        "image_type": forensics.image_type,
                        "suspicious": forensics.suspicious,
                        "reasons": forensics.reasons,
                        "checks": forensics.checks,
                        "disclaimer": forensics.disclaimer,
                    }
                }
                if forensics is not None
                else {}
            ),
        },
    )
    session.add(evidence)
    await session.flush()

    all_evidence = list(
        await session.scalars(select(Evidence).where(Evidence.case_id == case_id))
    )
    assessment = assess_case_evidence(case, all_evidence)
    assessment["extraction"] = extraction.as_assessment()
    if forensics is not None:
        assessment["forensics"] = {
            "image_type": forensics.image_type,
            "suspicious": forensics.suspicious,
            "reasons": forensics.reasons,
            "checks": forensics.checks,
            "disclaimer": forensics.disclaimer,
        }
    evidence.assessment = assessment
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
    if forensics is not None:
        session.add(
            AuditLog(
                actor_id=user.id,
                action="evidence.forensics_screened",
                object_type="evidence",
                object_id=evidence.id,
                metadata_json={
                    "image_type": forensics.image_type,
                    "suspicious": forensics.suspicious,
                },
            )
        )
    session.add(
        AuditLog(
            actor_id=user.id,
            action="evidence.extracted",
            object_type="evidence",
            object_id=evidence.id,
            metadata_json={"status": extraction.status, "provider": extraction.provider},
        )
    )
    await session.commit()
    await session.refresh(evidence)
    return evidence


@router.post(
    "/{case_id}/evidence/{evidence_id}/extract",
    response_model=EvidenceExtractionResponse,
)
async def retry_evidence_extraction(
    case_id: int,
    evidence_id: int,
    session: DbSession,
    user: CompleteWorkerProfile,
) -> EvidenceExtractionResponse:
    await get_worker_owned_case(case_id, session, user)
    evidence = await session.get(Evidence, evidence_id)
    if evidence is None or evidence.case_id != case_id:
        raise HTTPException(status_code=404, detail="材料不存在")
    if get_settings().task_backend.lower() == "celery":
        dispatch = dispatch_evidence_extraction(evidence.id)
        return EvidenceExtractionResponse(
            evidence_id=evidence.id,
            extraction_status="pending",
            extracted_text="",
            message=f"已加入后台提取队列：{dispatch.task_id}",
        )
    try:
        content = read_stored_content(evidence.stored_path)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="材料文件不存在") from None
    extraction = extract_text_from_bytes(evidence.filename, content, evidence.content_type)
    apply_extraction(evidence, extraction)
    session.add(
        AuditLog(
            actor_id=user.id,
            action="evidence.extraction_retried",
            object_type="evidence",
            object_id=evidence.id,
            metadata_json={"status": extraction.status, "provider": extraction.provider},
        )
    )
    await session.commit()
    await session.refresh(evidence)
    return EvidenceExtractionResponse(
        evidence_id=evidence.id,
        extraction_status=extraction.status,
        extracted_text=extraction.text,
        message=extraction.message,
    )


@router.get("/{case_id}/evidence/{evidence_id}/download")
async def download_evidence(
    case_id: int,
    evidence_id: int,
    session: DbSession,
    user: CurrentUser,
) -> Response:
    await get_accessible_case(case_id, session, user)
    evidence = await session.get(Evidence, evidence_id)
    if evidence is None or evidence.case_id != case_id:
        raise HTTPException(status_code=404, detail="材料不存在")
    try:
        content = read_stored_content(evidence.stored_path)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="材料文件不存在") from None

    session.add(
        AuditLog(
            actor_id=user.id,
            action="evidence.downloaded",
            object_type="evidence",
            object_id=evidence.id,
            metadata_json={"content_type": evidence.content_type},
        )
    )
    await session.commit()
    encoded_name = quote(evidence.filename)
    return Response(
        content=content,
        media_type=evidence.content_type,
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"evidence-{evidence.id}{Path(evidence.filename).suffix}\"; "
                f"filename*=UTF-8''{encoded_name}"
            )
        },
    )


@router.delete(
    "/{case_id}/evidence/{evidence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"description": "材料不存在或不属于当前案件"},
        409: {"description": "材料已纳入法律文书，不能直接删除"},
    },
)
async def delete_case_evidence(
    case_id: int,
    evidence_id: int,
    session: DbSession,
    user: CompleteWorkerProfile,
) -> Response:
    await get_worker_owned_case(case_id, session, user)
    evidence = await session.get(Evidence, evidence_id)
    if evidence is None or evidence.case_id != case_id:
        raise HTTPException(status_code=404, detail="材料不存在")

    document_reference = await session.scalar(
        select(DocumentEvidence.id)
        .where(DocumentEvidence.evidence_id == evidence_id)
        .limit(1)
    )
    if document_reference is not None:
        raise HTTPException(
            status_code=409,
            detail="该材料已纳入法律文书，不能直接删除",
        )

    stored_key = evidence.stored_path
    filename = evidence.filename
    digest = evidence.sha256
    await session.delete(evidence)
    session.add(
        AuditLog(
            actor_id=user.id,
            action="evidence.deleted",
            object_type="evidence",
            object_id=evidence_id,
            metadata_json={"filename": filename, "sha256": digest},
        )
    )
    await session.commit()

    # 文件可能已不存在，忽略，保证删除流程不因存储异常中断
    with suppress(FileNotFoundError, ValueError):
        get_storage().delete(stored_key)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{case_id}/contract-review", response_model=ContractReviewResponse)
async def review_case_contract(
    case_id: int,
    payload: ContractReviewRequest,
    session: DbSession,
    user: CompleteWorkerProfile,
) -> dict[str, Any]:
    case = await get_worker_owned_case(case_id, session, user)
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


@router.post(
    "/{case_id}/contract-review/file",
    response_model=ContractFileReviewResponse,
)
async def review_contract_file(
    case_id: int,
    session: DbSession,
    user: CompleteWorkerProfile,
    file: Annotated[UploadFile, File()],
) -> ContractFileReviewResponse:
    case = await get_worker_owned_case(case_id, session, user)
    filename = Path(file.filename or "未命名合同").name
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="不支持的文件类型")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件超过 20MB 限制")
    if not validate_signature(extension, content):
        raise HTTPException(status_code=400, detail="文件内容与扩展名不匹配")

    extraction = extract_text_from_bytes(
        filename,
        content,
        file.content_type or "",
    )
    if extraction.status != "extracted" or len(extraction.text) < 10:
        raise HTTPException(status_code=422, detail=extraction.message)

    review = review_contract(extraction.text)
    session.add(
        AuditLog(
            actor_id=user.id,
            action="contract.file_reviewed",
            object_type="case",
            object_id=case.id,
            metadata_json={
                "filename": filename,
                "risk_level": review["risk_level"],
                "provider": extraction.provider,
            },
        )
    )
    await session.commit()
    return ContractFileReviewResponse(
        filename=filename,
        extraction_status=extraction.status,
        extracted_text=extraction.text,
        review=ContractReviewResponse.model_validate(review),
    )
