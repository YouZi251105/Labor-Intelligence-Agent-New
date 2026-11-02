"""add case archive flag

Revision ID: f8a1c2d3e4b5
Revises: 7c27b8a91f42
Create Date: 2026-11-03 00:40:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f8a1c2d3e4b5"
down_revision: str | None = "7c27b8a91f42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cases",
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("cases", "archived")
