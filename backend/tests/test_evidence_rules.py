from app.services.evidence_rules import assess_evidence_rules


def _item(category: str, **kwargs) -> dict:
    item = {"category": category, "screening_status": "accepted"}
    item.update(kwargs)
    return item


def test_completeness_reports_missing_categories() -> None:
    result = assess_evidence_rules("wage", [])
    completeness = result["completeness"]
    assert completeness["status"] == "needs_more"
    assert "payroll" in completeness["missing_categories"]
    assert "工资或转账记录" in completeness["missing_labels"]


def test_completeness_ready_when_all_present() -> None:
    items = [_item("payroll"), _item("chat"), _item("contract")]
    result = assess_evidence_rules("wage", items)
    assert result["completeness"]["status"] == "ready"
    assert result["completeness"]["missing_categories"] == []


def test_legality_flags_quarantined() -> None:
    items = [_item("payroll", screening_status="quarantined")]
    result = assess_evidence_rules("wage", items)
    assert result["legality"]["status"] == "issue"
    assert any("隔离" in finding["message"] for finding in result["legality"]["findings"])


def test_legality_flags_unsupported_content_type() -> None:
    items = [_item("payroll", content_type="application/x-msdownload")]
    result = assess_evidence_rules("wage", items)
    assert result["legality"]["status"] == "issue"
    assert any("形式异常" in finding["message"] for finding in result["legality"]["findings"])


def test_legality_flags_oversized_file() -> None:
    items = [_item("payroll", file_size=21 * 1024 * 1024)]
    result = assess_evidence_rules("wage", items)
    assert result["legality"]["status"] == "issue"


def test_relevance_warns_on_unrelated_category() -> None:
    items = [_item("medical")]
    result = assess_evidence_rules("wage", items)
    assert result["relevance"]["status"] == "warning"
    assert any("关联性" in finding["message"] for finding in result["relevance"]["findings"])


def test_relevance_ok_for_related_categories() -> None:
    items = [_item("payroll"), _item("chat"), _item("contract")]
    result = assess_evidence_rules("wage", items)
    assert result["relevance"]["status"] == "ok"


def test_sufficiency_flags_missing_core() -> None:
    items = [_item("contract")]
    result = assess_evidence_rules("wage", items)
    assert result["sufficiency"]["status"] == "issue"
    assert any("核心证据" in finding["message"] for finding in result["sufficiency"]["findings"])


def test_sufficiency_ok_when_core_present() -> None:
    items = [_item("payroll"), _item("chat")]
    result = assess_evidence_rules("wage", items)
    assert result["sufficiency"]["status"] == "ok"


def test_unknown_dispute_type_falls_back_to_general() -> None:
    result = assess_evidence_rules("unknown_type", [])
    assert result["completeness"]["required_categories"] == ["contract", "chat", "payroll"]


def test_result_contains_disclaimer() -> None:
    result = assess_evidence_rules("wage", [])
    assert "不构成" in result["disclaimer"]
