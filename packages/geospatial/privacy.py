from __future__ import annotations

from dataclasses import dataclass
from math import floor


@dataclass(frozen=True, slots=True)
class Coordinate:
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class PrivacyReducedCoordinate:
    latitude: float | None
    longitude: float | None
    precision: str


def reduce_coordinate_precision(
    latitude: float,
    longitude: float,
    privacy_precision: str,
    *,
    county_centroid: Coordinate | None = None,
) -> PrivacyReducedCoordinate:
    if privacy_precision == "exact":
        return PrivacyReducedCoordinate(latitude, longitude, "exact")
    if privacy_precision in {"approximate", "100m"}:
        return PrivacyReducedCoordinate(round(latitude, 3), round(longitude, 3), "100m")
    if privacy_precision == "1km":
        return PrivacyReducedCoordinate(round(latitude, 2), round(longitude, 2), "1km")
    if privacy_precision in {"county", "district", "county_or_district"}:
        if county_centroid is None:
            return PrivacyReducedCoordinate(None, None, "county_or_district")
        return PrivacyReducedCoordinate(round(county_centroid.latitude, 2), round(county_centroid.longitude, 2), "county_or_district")
    if privacy_precision == "custom":
        return PrivacyReducedCoordinate(floor(latitude * 20) / 20, floor(longitude * 20) / 20, "custom")
    return PrivacyReducedCoordinate(round(latitude, 2), round(longitude, 2), "1km")

