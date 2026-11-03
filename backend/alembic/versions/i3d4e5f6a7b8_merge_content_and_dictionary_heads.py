"""merge content wording and dictionary migration heads

Revision ID: i3d4e5f6a7b8
Revises: a1b2c3d4e5f6, h2c3d4e5f6a7b8
Create Date: 2026-11-03 21:15:00
"""

from collections.abc import Sequence

revision: str = "i3d4e5f6a7b8"
down_revision: tuple[str, str] | None = (
    "a1b2c3d4e5f6",
    "h2c3d4e5f6a7b8",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
