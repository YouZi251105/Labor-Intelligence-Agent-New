from dataclasses import dataclass

from app.core.config import get_settings
from app.workers.celery_app import celery_app


@dataclass(frozen=True)
class JobDispatch:
    backend: str
    status: str
    task_id: str | None = None


def dispatch_evidence_extraction(
    evidence_id: int,
    backend: str | None = None,
) -> JobDispatch:
    selected = (backend or get_settings().task_backend).lower()
    if selected != "celery":
        return JobDispatch(backend="inline", status="sync")
    result = celery_app.send_task("evidence.extract", args=[evidence_id])
    return JobDispatch(
        backend="celery",
        status="queued",
        task_id=str(result.id),
    )


def dispatch_document_export(
    document_id: int,
    file_format: str,
    backend: str | None = None,
) -> JobDispatch:
    selected = (backend or get_settings().task_backend).lower()
    if selected != "celery":
        return JobDispatch(backend="inline", status="sync")
    result = celery_app.send_task(
        "document.export",
        args=[document_id, file_format],
    )
    return JobDispatch(
        backend="celery",
        status="queued",
        task_id=str(result.id),
    )
