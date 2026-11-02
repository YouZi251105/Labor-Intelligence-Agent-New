"""add rule packages

Revision ID: 7c27b8a91f42
Revises: 4a414e285ecd
Create Date: 2026-11-02 21:20:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "7c27b8a91f42"
down_revision: str | None = "4a414e285ecd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rule_packages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("package_type", sa.String(length=40), nullable=False),
        sa.Column("package_id", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("content_json", sa.JSON(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "package_id",
            "version",
            name="uq_rule_packages_package_version",
        ),
    )
    op.create_index(
        op.f("ix_rule_packages_package_type"),
        "rule_packages",
        ["package_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rule_packages_package_id"),
        "rule_packages",
        ["package_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rule_packages_status"),
        "rule_packages",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_rule_packages_status"), table_name="rule_packages")
    op.drop_index(op.f("ix_rule_packages_package_id"), table_name="rule_packages")
    op.drop_index(op.f("ix_rule_packages_package_type"), table_name="rule_packages")
    op.drop_table("rule_packages")
