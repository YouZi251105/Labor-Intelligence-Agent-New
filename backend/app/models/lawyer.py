from datetime import UTC, datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime


class LawyerProfile(Base):
    __tablename__ = "lawyer_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    license_no: Mapped[str] = mapped_column(String(80), default="")
    specialties: Mapped[str] = mapped_column(Text, default="劳动纠纷")
    status: Mapped[str] = mapped_column(String(20), default="active")
    bio: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=lambda: datetime.now(UTC)
    )
