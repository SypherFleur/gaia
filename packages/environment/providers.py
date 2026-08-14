from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from packages.provenance import ProvenanceRecord


JsonDict = dict[str, Any]

ENVIRONMENTAL_EVIDENCE_TYPES = {
    "OBSERVED",
    "FORECAST",
    "HISTORICAL",
    "CLIMATOLOGY",
    "MODELED",
    "SURVEY",
    "USER_MEASURED",
    "SENSOR",
    "DERIVED",
}


@dataclass(frozen=True, slots=True)
class EnvironmentalProviderResult:
    status: str
    data: JsonDict = field(default_factory=dict)
    provenance: list[ProvenanceRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class WeatherProvider(Protocol):
    async def forecast(self, latitude: float, longitude: float, at_time: str | None = None) -> EnvironmentalProviderResult: ...


class ClimateProvider(Protocol):
    async def climate_context(self, latitude: float, longitude: float, at_time: str | None = None) -> EnvironmentalProviderResult: ...


class SoilSurveyProvider(Protocol):
    async def soil_context(self, latitude: float, longitude: float, at_time: str | None = None) -> EnvironmentalProviderResult: ...


class WaterProvider(Protocol):
    async def nearby_sites(self, latitude: float, longitude: float) -> EnvironmentalProviderResult: ...

    async def current_conditions(self, latitude: float, longitude: float) -> EnvironmentalProviderResult: ...

    async def historical_conditions(self, latitude: float, longitude: float) -> EnvironmentalProviderResult: ...


class DisabledWeatherProvider:
    async def forecast(self, latitude: float, longitude: float, at_time: str | None = None) -> EnvironmentalProviderResult:
        return EnvironmentalProviderResult(status="UNAVAILABLE", warnings=["weather_provider_disabled"])


class DisabledClimateProvider:
    async def climate_context(self, latitude: float, longitude: float, at_time: str | None = None) -> EnvironmentalProviderResult:
        return EnvironmentalProviderResult(status="UNAVAILABLE", warnings=["climate_provider_disabled"])


class DisabledSoilSurveyProvider:
    async def soil_context(self, latitude: float, longitude: float, at_time: str | None = None) -> EnvironmentalProviderResult:
        return EnvironmentalProviderResult(status="UNAVAILABLE", warnings=["soil_provider_disabled"])


class DisabledWaterProvider:
    async def nearby_sites(self, latitude: float, longitude: float) -> EnvironmentalProviderResult:
        return EnvironmentalProviderResult(status="UNAVAILABLE", warnings=["water_provider_disabled"])

    async def current_conditions(self, latitude: float, longitude: float) -> EnvironmentalProviderResult:
        return EnvironmentalProviderResult(status="UNAVAILABLE", warnings=["water_provider_disabled"])

    async def historical_conditions(self, latitude: float, longitude: float) -> EnvironmentalProviderResult:
        return EnvironmentalProviderResult(status="UNAVAILABLE", warnings=["water_provider_disabled"])
