from datetime import UTC, datetime, timedelta, timezone

from app.db.types import UTCDateTime


def test_utc_datetime_binds_aware_values_as_naive_utc() -> None:
    value = datetime(
        2026,
        11,
        3,
        12,
        30,
        tzinfo=timezone(timedelta(hours=8)),
    )

    bound = UTCDateTime().process_bind_param(value, None)

    assert bound == datetime(2026, 11, 3, 4, 30)
    assert bound.tzinfo is None


def test_utc_datetime_restores_utc_after_read() -> None:
    value = datetime(2026, 11, 3, 4, 30)

    restored = UTCDateTime().process_result_value(value, None)

    assert restored == datetime(2026, 11, 3, 4, 30, tzinfo=UTC)
