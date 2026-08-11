from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from math import acos, asin, cos, degrees, floor, radians, sin, tan


def c_to_f(value_c: float) -> float:
    return (value_c * 9 / 5) + 32


def f_to_c(value_f: float) -> float:
    return (value_f - 32) * 5 / 9


def _day_of_year(value: date) -> int:
    return value.timetuple().tm_yday


def sunrise_sunset_utc(latitude: float, longitude: float, value: date) -> tuple[datetime, datetime]:
    day = _day_of_year(value)
    lng_hour = longitude / 15

    def calculate(is_sunrise: bool) -> datetime:
        t = day + ((6 - lng_hour) / 24 if is_sunrise else (18 - lng_hour) / 24)
        mean_anomaly = (0.9856 * t) - 3.289
        true_long = mean_anomaly + (1.916 * sin(radians(mean_anomaly))) + (0.020 * sin(radians(2 * mean_anomaly))) + 282.634
        true_long = true_long % 360
        right_ascension = degrees(asin(0) + __import__("math").atan(0.91764 * tan(radians(true_long))))
        right_ascension = right_ascension % 360
        l_quadrant = floor(true_long / 90) * 90
        ra_quadrant = floor(right_ascension / 90) * 90
        right_ascension = (right_ascension + (l_quadrant - ra_quadrant)) / 15
        sin_dec = 0.39782 * sin(radians(true_long))
        cos_dec = cos(asin(sin_dec))
        cos_hour_angle = (cos(radians(90.833)) - (sin_dec * sin(radians(latitude)))) / (cos_dec * cos(radians(latitude)))
        cos_hour_angle = min(1, max(-1, cos_hour_angle))
        hour_angle = 360 - degrees(acos(cos_hour_angle)) if is_sunrise else degrees(acos(cos_hour_angle))
        hour_angle /= 15
        local_mean_time = hour_angle + right_ascension - (0.06571 * t) - 6.622
        utc_hour = (local_mean_time - lng_hour) % 24
        hours = int(utc_hour)
        minutes = int((utc_hour - hours) * 60)
        seconds = int((((utc_hour - hours) * 60) - minutes) * 60)
        return datetime(value.year, value.month, value.day, tzinfo=UTC) + timedelta(hours=hours, minutes=minutes, seconds=seconds)

    sunrise = calculate(True)
    sunset = calculate(False)
    if sunset <= sunrise:
        sunset += timedelta(days=1)
    return sunrise, sunset


def photoperiod_hours(latitude: float, longitude: float, value: date) -> float:
    day = _day_of_year(value)
    declination = radians(23.44) * sin(radians((360 / 365) * (day - 81)))
    lat = radians(latitude)
    hour_angle = acos(max(-1, min(1, -tan(lat) * tan(declination))))
    return round((2 * degrees(hour_angle)) / 15, 2)


def moon_phase(value: date) -> dict:
    known_new_moon = date(2000, 1, 6)
    days = (value - known_new_moon).days
    lunations = days / 29.53058867
    phase_fraction = lunations - floor(lunations)
    illumination = round((1 - cos(2 * __import__("math").pi * phase_fraction)) / 2, 3)
    if phase_fraction < 0.03 or phase_fraction > 0.97:
        label = "new"
    elif phase_fraction < 0.25:
        label = "waxing_crescent"
    elif phase_fraction < 0.28:
        label = "first_quarter"
    elif phase_fraction < 0.50:
        label = "waxing_gibbous"
    elif phase_fraction < 0.53:
        label = "full"
    elif phase_fraction < 0.75:
        label = "waning_gibbous"
    elif phase_fraction < 0.78:
        label = "last_quarter"
    else:
        label = "waning_crescent"
    return {"phase": label, "phase_fraction": round(phase_fraction, 3), "illumination": illumination, "evidence_type": "DERIVED"}
