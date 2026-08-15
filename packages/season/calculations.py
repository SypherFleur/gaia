from __future__ import annotations

from datetime import date, datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def parse_date(value: str) -> date:
    return date.fromisoformat(value[:10])


def local_midday_iso(day: date, timezone: str) -> str:
    return datetime(day.year, day.month, day.day, 10, 0, tzinfo=_zoneinfo(timezone)).isoformat()


def horizon_basis(target: date, generated_on: date) -> str:
    days = (target - generated_on).days
    if days <= 0:
        return "current_conditions_and_local_observations"
    if days <= 7:
        return "forecast_execution"
    if days <= 14:
        return "forecast_influenced"
    if days <= 90:
        return "climatological_seasonal_context"
    return "climate_normals_historical_distribution"


def growing_degree_day(t_min_c: float, t_max_c: float, base_c: float, upper_c: float | None = None) -> float:
    low = max(t_min_c, base_c)
    high = min(t_max_c, upper_c) if upper_c is not None else t_max_c
    return max(((low + high) / 2.0) - base_c, 0.0)


def date_in_ranges(day: date, ranges: list[dict]) -> bool:
    for item in ranges:
        start = parse_date(str(item.get("start")))
        end = parse_date(str(item.get("end")))
        if start <= day <= end:
            return True
    return False


def next_available(day: date, ranges: list[dict]) -> date:
    candidate = day
    for _ in range(366):
        if not date_in_ranges(candidate, ranges):
            return candidate
        candidate += timedelta(days=1)
    return day


def hemisphere(latitude: float | None) -> str:
    if latitude is None:
        return "unknown"
    if latitude < -10:
        return "southern"
    if latitude > 10:
        return "northern"
    return "tropical"


# Standard/daylight offsets for the U.S. zones GAIA plans in, used only when
# the optional tzdata package is unavailable (some Windows environments).
_FALLBACK_ZONE_OFFSETS = {
    "America/New_York": (-5, -4),
    "America/Detroit": (-5, -4),
    "America/Chicago": (-6, -5),
    "America/Denver": (-7, -6),
    "America/Phoenix": (-7, -7),
    "America/Los_Angeles": (-8, -7),
    "America/Anchorage": (-9, -8),
    "Pacific/Honolulu": (-10, -10),
    "UTC": (0, 0),
}


class _FallbackUSTimezone(tzinfo):
    """DST-aware stand-in for a real IANA zone.

    Applies the post-2007 U.S. rule (second Sunday in March to first Sunday in
    November). A fixed offset would be silently an hour wrong for roughly half
    the year, which is exactly the kind of plausible-looking constant GAIA
    treats as a bug rather than a placeholder.
    """

    def __init__(self, name: str, standard_hours: int, daylight_hours: int) -> None:
        self._name = name
        self._standard = timedelta(hours=standard_hours)
        self._daylight = timedelta(hours=daylight_hours)

    def utcoffset(self, dt: datetime | None) -> timedelta:
        return self._daylight if self._daylight_active(dt) else self._standard

    def dst(self, dt: datetime | None) -> timedelta:
        return self._daylight - self._standard if self._daylight_active(dt) else timedelta(0)

    def tzname(self, dt: datetime | None) -> str:
        return self._name

    def _daylight_active(self, dt: datetime | None) -> bool:
        if dt is None or self._daylight == self._standard:
            return False
        start = datetime.combine(_nth_sunday(dt.year, 3, 2), datetime.min.time()) + timedelta(hours=2)
        end = datetime.combine(_nth_sunday(dt.year, 11, 1), datetime.min.time()) + timedelta(hours=2)
        return start <= dt.replace(tzinfo=None) < end


def _nth_sunday(year: int, month: int, occurrence: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(6 - first.weekday()) % 7 + 7 * (occurrence - 1))


def _zoneinfo(value: str):
    try:
        return ZoneInfo(value)
    except ZoneInfoNotFoundError:
        offsets = _FALLBACK_ZONE_OFFSETS.get(value)
        if offsets is None:
            # Unknown zone with no tz database: use UTC and say so in the label
            # rather than implying the requested zone was honored.
            return timezone(timedelta(0), f"UTC (unresolved {value})")
        return _FallbackUSTimezone(value, *offsets)
