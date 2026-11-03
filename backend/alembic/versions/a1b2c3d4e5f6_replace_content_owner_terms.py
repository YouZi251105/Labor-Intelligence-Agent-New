"""replace content owner wording with manual review wording

Revision ID: a1b2c3d4e5f6
Revises: f0a1b2c3d4e5
Create Date: 2026-11-03 20:50:00
"""

import hashlib
import json
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f0a1b2c3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REPLACEMENTS = [
    ("待法律内容负责人复核", "待内容复核人员校验"),
    ("法律内容负责人复核", "内容复核人员校验"),
    ("法律内容负责人", "内容复核人员"),
]


def upgrade() -> None:
    _replace_rule_sources(REPLACEMENTS)
    _replace_rule_packages(REPLACEMENTS)


def downgrade() -> None:
    replacements = [(new, old) for old, new in REPLACEMENTS]
    _replace_rule_sources(replacements)
    _replace_rule_packages(replacements)


def _replace_rule_sources(replacements: list[tuple[str, str]]) -> None:
    table = sa.table(
        "rule_configs",
        sa.column("id", sa.Integer),
        sa.column("source_note", sa.Text),
    )
    bind = op.get_bind()
    rows = bind.execute(sa.select(table.c.id, table.c.source_note)).mappings()
    for row in rows:
        updated = _replace_text(row["source_note"] or "", replacements)
        if updated == row["source_note"]:
            continue
        bind.execute(
            table.update()
            .where(table.c.id == row["id"])
            .values(source_note=updated)
        )


def _replace_rule_packages(replacements: list[tuple[str, str]]) -> None:
    table = sa.table(
        "rule_packages",
        sa.column("id", sa.Integer),
        sa.column("content_json", sa.JSON),
        sa.column("checksum", sa.String),
    )
    bind = op.get_bind()
    rows = bind.execute(sa.select(table.c.id, table.c.content_json)).mappings()
    for row in rows:
        content: Any = row["content_json"]
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                continue
        if not isinstance(content, dict):
            continue
        serialized = json.dumps(
            content,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        updated_serialized = _replace_text(serialized, replacements)
        if updated_serialized == serialized:
            continue
        bind.execute(
            table.update()
            .where(table.c.id == row["id"])
            .values(
                content_json=json.loads(updated_serialized),
                checksum=hashlib.sha256(updated_serialized.encode()).hexdigest(),
            )
        )


def _replace_text(
    value: str,
    replacements: list[tuple[str, str]],
) -> str:
    result = value
    for old, new in replacements:
        result = result.replace(old, new)
    return result
