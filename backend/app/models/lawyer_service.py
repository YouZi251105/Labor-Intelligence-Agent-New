from datetime import UTC, date, datetime

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime


class LawyerRequest(Base):
    """用户发起的律师服务预约（被动介入）。"""

    __tablename__ = "lawyer_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    lawyer_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    reason: Mapped[str] = mapped_column(Text)
    preferred_time: Mapped[str] = mapped_column(String(160), default="")
    preferred_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    preferred_slot: Mapped[str | None] = mapped_column(String(20), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    reject_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), nullable=True
    )


class ConsultationSession(Base):
    """用户与律师之间的咨询会话。"""

    __tablename__ = "consultation_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[int | None] = mapped_column(
        ForeignKey("lawyer_requests.id"), nullable=True, index=True
    )
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    lawyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=lambda: datetime.now(UTC)
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), nullable=True
    )


class ConsultationMessage(Base):
    """咨询会话中的消息，只增不改不删，保证留存可追溯。"""

    __tablename__ = "consultation_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("consultation_sessions.id"), index=True
    )
    sender_role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    attachment_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attachment_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    attachment_size: Mapped[int | None] = mapped_column(nullable=True)
    attachment_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=lambda: datetime.now(UTC)
    )


class CaseReview(Base):
    """结案前的必经律师复核（主动介入）。"""

    __tablename__ = "case_reviews"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("cases.id"), unique=True, index=True
    )
    lawyer_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    conclusion: Mapped[str | None] = mapped_column(String(40), nullable=True)
    comment: Mapped[str] = mapped_column(Text, default="")
    user_decision: Mapped[str | None] = mapped_column(String(20), nullable=True)
    user_decision_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=lambda: datetime.now(UTC)
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), nullable=True
    )
