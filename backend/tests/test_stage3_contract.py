import pytest
from pydantic import ValidationError

from app.models import (
    HelpResource,
    LawyerOpinion,
    RevenueLedger,
    RuleConfig,
    ServiceRecord,
    SimulationMessage,
    SimulationSession,
    UserProfile,
)
from app.schemas.profile import UserProfileUpdate
from app.services.profile import mask_identity_number


def test_stage3_tables_are_registered() -> None:
    assert SimulationSession.__tablename__ == "simulation_sessions"
    assert SimulationMessage.__tablename__ == "simulation_messages"
    assert LawyerOpinion.__tablename__ == "lawyer_opinions"
    assert ServiceRecord.__tablename__ == "service_records"
    assert RevenueLedger.__tablename__ == "revenue_ledger"
    assert UserProfile.__tablename__ == "user_profiles"
    assert HelpResource.__tablename__ == "help_resources"
    assert RuleConfig.__tablename__ == "rule_configs"


def test_identity_number_is_masked() -> None:
    assert mask_identity_number("110101199001011234") == "110***********1234"
    assert mask_identity_number("bad") == ""


def test_profile_update_rejects_invalid_phone() -> None:
    with pytest.raises(ValidationError):
        UserProfileUpdate(
            real_name="张三",
            phone="123",
            id_number="110101199001011234",
        )


def test_rule_config_defaults_to_pending_review() -> None:
    RuleConfig(
        dispute_type="wage",
        name="欠薪证据规则",
        evidence_requirements=["payroll", "chat"],
        next_steps=["整理工资记录"],
    )
    assert RuleConfig.__table__.c.review_status.default.arg == "pending_review"
    assert RuleConfig.__table__.c.version.default.arg == 1


def test_service_record_defaults_to_pending() -> None:
    ServiceRecord(
        case_id=1,
        lawyer_id=2,
        service_type="consultation",
        summary="电话咨询",
        duration_minutes=30,
    )
    assert ServiceRecord.__table__.c.status.default.arg == "pending"


def test_revenue_ledger_uses_integer_cents() -> None:
    entry = RevenueLedger(
        lawyer_id=2,
        amount_cents=19900,
        entry_type="consultation",
        note="演示咨询收入",
    )
    assert entry.amount_cents == 19900
    assert RevenueLedger.__table__.c.status.default.arg == "pending"
