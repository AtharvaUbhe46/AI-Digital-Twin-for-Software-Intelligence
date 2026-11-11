"""
Centralized Datetime Utilities for AI Digital Twin.
Ensures all datetime objects are consistently timezone-aware in UTC across
database persistence, API serialization, and in-memory comparisons.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Any


def utc_now() -> datetime:
    """Returns the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Guarantees that a datetime object is timezone-aware in UTC.
    - If dt is None, returns None.
    - If dt is offset-naive (tzinfo is None), assumes it was recorded in UTC and attaches timezone.utc.
    - If dt is offset-aware in another timezone, converts it to timezone.utc preserving the instant.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_iso_datetime(dt_val: Optional[Any]) -> Optional[datetime]:
    """
    Parses an ISO string or normalizes a datetime object into a timezone-aware UTC datetime.
    Handles 'Z', offsets (+/-HH:MM), fractional seconds, and naive strings safely.
    Always returns a timezone-aware UTC datetime, or None if input cannot be parsed.
    """
    if dt_val is None:
        return None
    if isinstance(dt_val, datetime):
        return ensure_utc(dt_val)
    if not isinstance(dt_val, str):
        return None

    trimmed = dt_val.strip()
    if not trimmed:
        return None

    # Handle standard ISO formats with 'Z'
    try:
        normalized = trimmed.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        return ensure_utc(dt)
    except Exception:
        pass

    # Common fallback patterns
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(trimmed, fmt)
            return ensure_utc(dt)
        except Exception:
            continue

    return None


def safe_datetime_diff_minutes(dt1: Optional[datetime], dt2: Optional[datetime]) -> Optional[float]:
    """
    Safely calculates difference (dt1 - dt2) in minutes.
    Guarantees offset-aware UTC comparison without raising TypeError.
    """
    if dt1 is None or dt2 is None:
        return None
    d1 = ensure_utc(dt1)
    d2 = ensure_utc(dt2)
    return round((d1 - d2).total_seconds() / 60.0, 1)


def safe_datetime_diff_days(dt1: Optional[datetime], dt2: Optional[datetime]) -> Optional[float]:
    """
    Safely calculates difference (dt1 - dt2) in days.
    Guarantees offset-aware UTC comparison.
    """
    if dt1 is None or dt2 is None:
        return None
    d1 = ensure_utc(dt1)
    d2 = ensure_utc(dt2)
    return (d1 - d2).total_seconds() / 86400.0


def format_iso_utc(dt: Optional[datetime]) -> Optional[str]:
    """Returns ISO 8601 string representation in UTC."""
    if dt is None:
        return None
    return ensure_utc(dt).isoformat()

