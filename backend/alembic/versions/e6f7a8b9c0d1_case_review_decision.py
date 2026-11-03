"""add user decision to case reviews

Revision ID: e6f7a8b9c0d1
Revises: d5e7f8a9b0c1
Create Date: 2026-11-03 18:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: str | None = "d5e7f8a9b0c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "case_reviews",
        sa.Column("user_decision", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "case_reviews",
        sa.Column("user_decision_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("case_reviews", "user_decision_at")
    op.drop_column("case_reviews", "user_decision")
