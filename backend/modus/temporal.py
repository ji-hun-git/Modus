"""Event dates and server-owned knowledge instants have different meanings."""
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc)


def instant(value):
    """Canonical UTC, fixed precision for SQLite range comparisons. No naive time."""
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('A knowledge timestamp must include a timezone offset')
    return value.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')
