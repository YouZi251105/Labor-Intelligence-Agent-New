from app.services import jobs


def test_inline_task_backend_returns_sync_dispatch() -> None:
    dispatch = jobs.dispatch_evidence_extraction(12, backend="inline")

    assert dispatch.backend == "inline"
    assert dispatch.task_id is None
    assert dispatch.status == "sync"


def test_celery_task_backend_uses_send_task(monkeypatch) -> None:
    calls: list[tuple[str, list[object]]] = []

    def fake_send_task(name: str, args: list[object]) -> object:
        calls.append((name, args))
        return type("Result", (), {"id": "task-123"})()

    monkeypatch.setattr(jobs.celery_app, "send_task", fake_send_task)
    dispatch = jobs.dispatch_evidence_extraction(12, backend="celery")

    assert dispatch.backend == "celery"
    assert dispatch.task_id == "task-123"
    assert dispatch.status == "queued"
    assert calls == [("evidence.extract", [12])]


def test_document_export_dispatch_supports_inline_and_celery(monkeypatch) -> None:
    inline = jobs.dispatch_document_export(5, "pdf", backend="inline")
    assert inline.status == "sync"

    def fake_send_task(name: str, args: list[object]) -> object:
        assert name == "document.export"
        assert args == [5, "pdf"]
        return type("Result", (), {"id": "export-123"})()

    monkeypatch.setattr(jobs.celery_app, "send_task", fake_send_task)
    queued = jobs.dispatch_document_export(5, "pdf", backend="celery")
    assert queued.task_id == "export-123"
    assert queued.status == "queued"
