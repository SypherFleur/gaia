from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from packages.domain import SeasonPlan


JsonDict = dict[str, Any]


@dataclass(frozen=True, slots=True)
class SeasonPlanRequest:
    workspace_id: str
    location_id: str | None
    objective: str
    crop_names: list[str] = field(default_factory=list)
    user_plant_ids: list[str] = field(default_factory=list)
    start_date: str | None = None
    end_date: str | None = None
    constraints: JsonDict = field(default_factory=dict)
    timezone: str = "UTC"
    include_luna: bool = True
    use_model: bool = False


@dataclass(frozen=True, slots=True)
class SeasonContext:
    workspace: JsonDict
    location: JsonDict | None
    geo_context: JsonDict | None = None
    environmental_snapshot: JsonDict | None = None
    climate_context: JsonDict = field(default_factory=dict)
    weather_forecast_context: JsonDict = field(default_factory=dict)
    crop_entities: list[JsonDict] = field(default_factory=list)
    user_plants: list[JsonDict] = field(default_factory=list)
    plant_profiles: list[JsonDict] = field(default_factory=list)
    recent_observations: list[JsonDict] = field(default_factory=list)
    sentinel_constraints: list[JsonDict] = field(default_factory=list)
    scholar_evidence: list[JsonDict] = field(default_factory=list)
    mercator_context: JsonDict | None = None
    user_objectives: list[str] = field(default_factory=list)
    resource_constraints: JsonDict = field(default_factory=dict)
    date_range: JsonDict = field(default_factory=dict)
    timezone: str = "UTC"
    luna_context: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        return {
            "workspace": self.workspace,
            "location": self.location,
            "geo_context": self.geo_context,
            "environmental_snapshot": self.environmental_snapshot,
            "climate_context": self.climate_context,
            "weather_forecast_context": self.weather_forecast_context,
            "crop_entities": self.crop_entities,
            "user_plants": self.user_plants,
            "plant_profiles": self.plant_profiles,
            "recent_observations": self.recent_observations,
            "sentinel_constraints": self.sentinel_constraints,
            "scholar_evidence": self.scholar_evidence,
            "mercator_context": self.mercator_context,
            "user_objectives": self.user_objectives,
            "resource_constraints": self.resource_constraints,
            "date_range": self.date_range,
            "timezone": self.timezone,
            "luna_context": self.luna_context,
        }


class SeasonPlanner(Protocol):
    async def create_plan(self, request: SeasonPlanRequest, context: SeasonContext) -> tuple[SeasonPlan, list[JsonDict]]: ...

    async def revise_plan(self, existing_plan: SeasonPlan, updated_context: SeasonContext) -> JsonDict: ...
