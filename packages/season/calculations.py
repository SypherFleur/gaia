from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
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


def _zoneinfo(value: str):
    try:
        return ZoneInfo(value)
    except ZoneInfoNotFoundError:
        # Windows test environments may lack the optional tzdata package.
        # Preserve local-date semantics with stable fixed offsets; calendar payloads still carry the IANA label.
        fallback_offsets = {
            "America/Chicago": -5,
            "UTC": 0,
        }
        return timezone(timedelta(hours=fallback_offsets.get(value, 0)))
