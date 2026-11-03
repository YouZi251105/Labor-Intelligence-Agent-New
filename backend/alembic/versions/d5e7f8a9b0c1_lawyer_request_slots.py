"""add structured preferred date and slot to lawyer requests

Revision ID: d5e7f8a9b0c1
Revises: c9d4e5f6a7b8
Create Date: 2026-11-03 16:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d5e7f8a9b0c1"
down_revision: str | None = "c9d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "lawyer_requests",
        sa.Column("preferred_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "lawyer_requests",
        sa.Column("preferred_slot", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "lawyer_requests",
        sa.Column("reject_reason", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("lawyer_requests", "reject_reason")
    op.drop_column("lawyer_requests", "preferred_slot")
    op.drop_column("lawyer_requests", "preferred_date")
