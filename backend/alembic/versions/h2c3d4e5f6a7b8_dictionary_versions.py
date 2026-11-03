"""add dictionary_versions table

Revision ID: h2c3d4e5f6a7b8
Revises: g1b2c3d4e5f6
Create Date: 2026-11-04 02:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "h2c3d4e5f6a7b8"
down_revision: str | None = "g1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dictionary_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("content_json", sa.JSON(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("version", name="uq_dictionary_versions_version"),
    )
    op.create_index(
        "ix_dictionary_versions_status", "dictionary_versions", ["status"]
    )


def downgrade() -> None:
    op.drop_index("ix_dictionary_versions_status", table_name="dictionary_versions")
    op.drop_table("dictionary_versions")
