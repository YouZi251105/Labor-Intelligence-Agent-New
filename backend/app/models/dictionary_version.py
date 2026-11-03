"""字典版本模型：管理端发布纠纷分类等字典内容，业务服务读取已发布包。"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime


class DictionaryVersion(Base):
    __tablename__ = "dictionary_versions"
    __table_args__ = (
        UniqueConstraint("version", name="uq_dictionary_versions_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    content: Mapped[dict[str, Any]] = mapped_column("content_json", JSON, default=dict)
    checksum: Mapped[str] = mapped_column(String(64), default="")
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=lambda: datetime.now(UTC)
    )
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
