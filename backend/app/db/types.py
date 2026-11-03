"""数据库层通用类型。"""
from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator[datetime]):
    """存储 UTC 时间，读取时自动补回 UTC 时区。

    SQLite 不保存时区信息，aware datetime 写入后读回会变成 naive，
    导致前端把 UTC 时间误当本地时间解析。此类型在读取结果时补回 UTC 时区。
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(
        self,
        value: datetime | None,
        dialect: Dialect | None,
    ) -> datetime | None:
        if not isinstance(value, datetime) or value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(
        self,
        value: datetime | None,
        dialect: Dialect | None,
    ) -> datetime | None:
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
