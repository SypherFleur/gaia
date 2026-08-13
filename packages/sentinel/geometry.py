from __future__ import annotations

from typing import Any, Literal


JsonDict = dict[str, Any]
ZoneRelation = Literal["POINT_INSIDE", "POINT_OUTSIDE", "COUNTY_INSIDE", "COUNTY_PARTIAL", "NO_GEOMETRY"]


def point_in_rectangle(latitude: float, longitude: float, rectangle: JsonDict) -> bool:
    return (
        float(rectangle["min_lat"]) <= latitude <= float(rectangle["max_lat"])
        and float(rectangle["min_lon"]) <= longitude <= float(rectangle["max_lon"])
    )


def rectangle_contains(outer: JsonDict, inner: JsonDict) -> bool:
    return (
        float(outer["min_lat"]) <= float(inner["min_lat"])
        and float(outer["max_lat"]) >= float(inner["max_lat"])
        and float(outer["min_lon"]) <= float(inner["min_lon"])
        and float(outer["max_lon"]) >= float(inner["max_lon"])
    )


def rectangle_intersects(left: JsonDict, right: JsonDict) -> bool:
    return not (
        float(left["max_lat"]) < float(right["min_lat"])
        or float(left["min_lat"]) > float(right["max_lat"])
        or float(left["max_lon"]) < float(right["min_lon"])
        or float(left["min_lon"]) > float(right["max_lon"])
    )


def zone_relation(zone_geometry: JsonDict | None, *, point: tuple[float, float] | None = None, county_geometry: JsonDict | None = None) -> ZoneRelation:
    if not zone_geometry:
        return "NO_GEOMETRY"
    if point is not None:
        return "POINT_INSIDE" if point_in_rectangle(point[0], point[1], zone_geometry) else "POINT_OUTSIDE"
    if county_geometry is not None:
        if rectangle_contains(zone_geometry, county_geometry):
            return "COUNTY_INSIDE"
        if rectangle_intersects(zone_geometry, county_geometry):
            return "COUNTY_PARTIAL"
        return "POINT_OUTSIDE"
    return "NO_GEOMETRY"
