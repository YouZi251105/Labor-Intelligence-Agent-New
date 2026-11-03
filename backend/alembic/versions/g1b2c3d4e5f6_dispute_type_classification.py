"""migrate dispute types to legal classification

Revision ID: g1b2c3d4e5f6
Revises: f0a1b2c3d4e5
Create Date: 2026-11-03 21:05:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.services.dictionary import DISPUTE_TYPE_MIGRATIONS

revision: str = "g1b2c3d4e5f6"
down_revision: str | None = "f0a1b2c3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MIGRATIONS = DISPUTE_TYPE_MIGRATIONS


def upgrade() -> None:
    table = sa.table("cases", sa.column("dispute_type", sa.String))
    bind = op.get_bind()
    for old, new in MIGRATIONS.items():
        if old == new:
            continue
        bind.execute(
            table.update()
            .where(table.c.dispute_type == old)
            .values(dispute_type=new)
        )


def downgrade() -> None:
    reverse = {new: old for old, new in MIGRATIONS.items()}
    table = sa.table("cases", sa.column("dispute_type", sa.String))
    bind = op.get_bind()
    for new, old in reverse.items():
        if old == new:
            continue
        bind.execute(
            table.update()
            .where(table.c.dispute_type == new)
            .values(dispute_type=old)
        )
