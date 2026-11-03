"""replace legal review wording with manual review wording

Revision ID: c4e8a1b2d3f6
Revises: f8a1c2d3e4b5
Create Date: 2026-11-03 13:30:00
"""

import hashlib
import json
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

revision: str = "c4e8a1b2d3f6"
down_revision: str | None = "f8a1c2d3e4b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REPLACEMENTS = [
    ("具体依据待法学负责人确认", "具体依据待人工复核人员确认"),
    ("法学内容负责人", "内容复核人员"),
    ("法学内容复核", "人工复核校验"),
    ("待法学复核", "待人工复核"),
    ("法学复核意见", "人工复核意见"),
    ("法学复核", "人工复核"),
    ("法学负责人", "人工复核人员"),
    ("法律复核", "人工复核校验"),
]


def upgrade() -> None:
    _replace_existing_content(REPLACEMENTS)


def downgrade() -> None:
    _replace_existing_content(
        [(new, old) for old, new in REPLACEMENTS],
    )


def _replace_existing_content(replacements: list[tuple[str, str]]) -> None:
    table = sa.table(
        "rule_packages",
        sa.column("id", sa.Integer),
        sa.column("content_json", sa.JSON),
        sa.column("checksum", sa.String),
    )
    bind = op.get_bind()
    rows = bind.execute(
        sa.select(table.c.id, table.c.content_json)
    ).mappings()
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
        updated = json.loads(updated_serialized)
        checksum = hashlib.sha256(updated_serialized.encode()).hexdigest()
        bind.execute(
            table.update()
            .where(table.c.id == row["id"])
            .values(content_json=updated, checksum=checksum)
        )


def _replace_text(
    value: str,
    replacements: list[tuple[str, str]],
) -> str:
    result = value
    for old, new in replacements:
        result = result.replace(old, new)
    return result
