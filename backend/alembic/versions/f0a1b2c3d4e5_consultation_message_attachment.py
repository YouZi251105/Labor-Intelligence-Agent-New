"""add consultation message attachment columns

Revision ID: f0a1b2c3d4e5
Revises: e6f7a8b9c0d1
Create Date: 2026-11-03 18:40:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f0a1b2c3d4e5"
down_revision: str | None = "e6f7a8b9c0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "consultation_messages",
        sa.Column("attachment_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "consultation_messages",
        sa.Column("attachment_key", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "consultation_messages",
        sa.Column("attachment_size", sa.Integer(), nullable=True),
    )
    op.add_column(
        "consultation_messages",
        sa.Column("attachment_type", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("consultation_messages", "attachment_type")
    op.drop_column("consultation_messages", "attachment_size")
    op.drop_column("consultation_messages", "attachment_key")
    op.drop_column("consultation_messages", "attachment_name")
