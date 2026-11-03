"""add lawyer service tables

Revision ID: c9d4e5f6a7b8
Revises: c4e8a1b2d3f6
Create Date: 2026-11-03 16:20:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c9d4e5f6a7b8"
down_revision: str | None = "c4e8a1b2d3f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lawyer_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("lawyer_id", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("preferred_time", sa.String(length=160), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
        sa.ForeignKeyConstraint(["lawyer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lawyer_requests_case_id"), "lawyer_requests", ["case_id"], unique=False)
    op.create_index(op.f("ix_lawyer_requests_user_id"), "lawyer_requests", ["user_id"], unique=False)
    op.create_index(op.f("ix_lawyer_requests_lawyer_id"), "lawyer_requests", ["lawyer_id"], unique=False)
    op.create_index(op.f("ix_lawyer_requests_status"), "lawyer_requests", ["status"], unique=False)

    op.create_table(
        "consultation_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=True),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("lawyer_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
        sa.ForeignKeyConstraint(["lawyer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["request_id"], ["lawyer_requests.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_consultation_sessions_request_id"), "consultation_sessions", ["request_id"], unique=False)
    op.create_index(op.f("ix_consultation_sessions_case_id"), "consultation_sessions", ["case_id"], unique=False)
    op.create_index(op.f("ix_consultation_sessions_user_id"), "consultation_sessions", ["user_id"], unique=False)
    op.create_index(op.f("ix_consultation_sessions_lawyer_id"), "consultation_sessions", ["lawyer_id"], unique=False)

    op.create_table(
        "consultation_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("sender_role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["consultation_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_consultation_messages_session_id"), "consultation_messages", ["session_id"], unique=False)

    op.create_table(
        "case_reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("lawyer_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("conclusion", sa.String(length=40), nullable=True),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
        sa.ForeignKeyConstraint(["lawyer_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id", name="uq_case_reviews_case_id"),
    )
    op.create_index(op.f("ix_case_reviews_case_id"), "case_reviews", ["case_id"], unique=True)
    op.create_index(op.f("ix_case_reviews_lawyer_id"), "case_reviews", ["lawyer_id"], unique=False)
    op.create_index(op.f("ix_case_reviews_status"), "case_reviews", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_case_reviews_status"), table_name="case_reviews")
    op.drop_index(op.f("ix_case_reviews_lawyer_id"), table_name="case_reviews")
    op.drop_index(op.f("ix_case_reviews_case_id"), table_name="case_reviews")
    op.drop_table("case_reviews")
    op.drop_index(op.f("ix_consultation_messages_session_id"), table_name="consultation_messages")
    op.drop_table("consultation_messages")
    op.drop_index(op.f("ix_consultation_sessions_lawyer_id"), table_name="consultation_sessions")
    op.drop_index(op.f("ix_consultation_sessions_user_id"), table_name="consultation_sessions")
    op.drop_index(op.f("ix_consultation_sessions_case_id"), table_name="consultation_sessions")
    op.drop_index(op.f("ix_consultation_sessions_request_id"), table_name="consultation_sessions")
    op.drop_table("consultation_sessions")
    op.drop_index(op.f("ix_lawyer_requests_status"), table_name="lawyer_requests")
    op.drop_index(op.f("ix_lawyer_requests_lawyer_id"), table_name="lawyer_requests")
    op.drop_index(op.f("ix_lawyer_requests_user_id"), table_name="lawyer_requests")
    op.drop_index(op.f("ix_lawyer_requests_case_id"), table_name="lawyer_requests")
    op.drop_table("lawyer_requests")
