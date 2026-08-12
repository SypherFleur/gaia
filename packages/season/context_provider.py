from __future__ import annotations

from packages.context import ContextCompiler
from packages.mercator import MercatorContextProvider
from packages.persistence import GaiaRepository
from packages.season.types import SeasonContext, SeasonPlanRequest
from packages.tools import ToolExecutionContext


class SeasonContextProvider:
    def __init__(
        self,
        *,
        repository: GaiaRepository,
        context_compiler: ContextCompiler | None = None,
        mercator_context_provider: MercatorContextProvider | None = None,
    ) -> None:
        self.repository = repository
        self.context_compiler = context_compiler
        self.mercator_context_provider = mercator_context_provider

    async def build(
        self,
        context: ToolExecutionContext,
        request: SeasonPlanRequest,
        *,
        sentinel_constraints: list[dict] | None = None,
        scholar_evidence: list[dict] | None = None,
        climate_context: dict | None = None,
        weather_forecast_context: dict | None = None,
        include_mercator: bool = False,
    ) -> SeasonContext:
        workspace = self.repository.get_workspace(context.organization_id, request.workspace_id)
        if workspace is None:
            raise PermissionError("Workspace is missing or inaccessible")
        location = self.repository.get_location(context.organization_id, request.location_id) if request.location_id else None
        geo_context = None
        environmental_snapshot = None
        if request.location_id and self.context_compiler is not None:
            bundle = await self.context_compiler.build_environmental_context(context, request.location_id)
            geo_context = bundle.to_dict()["geo_context"]
            environmental_snapshot = bundle.to_dict()["environmental_snapshot"]
        user_plants = []
        plant_profiles = []
        observations = []
        mercator_context = None
        for plant in self.repository.list_user_plants(context.organization_id, request.workspace_id):
            if request.user_plant_ids and plant["id"] not in request.user_plant_ids:
                continue
            user_plants.append(plant)
            profile = self.repository.get_latest_plant_profile(context.organization_id, plant["plant_entity_id"])
            if profile is not None:
                plant_profiles.append(profile)
            observations.extend(self.repository.list_observations(context.organization_id, plant["id"])[:3])
        if include_mercator and self.mercator_context_provider is not None and request.crop_names:
            geography = geo_context or {
                "country_code": location.get("country_code") if location else None,
                "state_code": location.get("admin1") if location else None,
                "county_or_district": location.get("admin2") if location else None,
                "county_fips": location.get("county_fips") if location else None,
            }
            result = await self.mercator_context_provider.build_context(
                context,
                commodity=request.crop_names[0],
                geography=geography,
                location_id=request.location_id,
            )
            mercator_context = result.to_dict()["mercator_context"]
        return SeasonContext(
            workspace=workspace,
            location=location,
            geo_context=geo_context,
            environmental_snapshot=environmental_snapshot,
            climate_context=climate_context or {},
            weather_forecast_context=weather_forecast_context or {},
            user_plants=user_plants,
            plant_profiles=plant_profiles,
            recent_observations=observations,
            sentinel_constraints=sentinel_constraints or [],
            scholar_evidence=scholar_evidence or [],
            mercator_context=mercator_context,
            user_objectives=[request.objective],
            resource_constraints=request.constraints,
            date_range={"start": request.start_date, "end": request.end_date},
            timezone=request.timezone,
            luna_context={"phase": "waxing crescent", "evidence_status": "Experimental", "influence_on_plan": "None"} if request.include_luna else {},
        )
