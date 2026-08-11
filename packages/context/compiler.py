from __future__ import annotations

from dataclasses import dataclass
from dataclasses import asdict

from packages.domain import Location
from packages.geospatial import AtlasResult, AtlasService
from packages.persistence import GaiaRepository
from packages.persistence.sqlite import TenantAccessError
from packages.tools import ToolExecutionContext
from packages.environment.terra import TerraResult, TerraService


@dataclass(frozen=True, slots=True)
class ContextBundle:
    geo_context: object
    environmental_snapshot: object | None
    atlas: AtlasResult
    terra: TerraResult | None
    botanist_context: object | None = None
    model_run_count: int = 0

    def to_dict(self) -> dict:
        geo = asdict(self.geo_context)
        snapshot = asdict(self.environmental_snapshot) if self.environmental_snapshot is not None else None
        botanist = (
            self.botanist_context.to_dict()
            if self.botanist_context is not None and hasattr(self.botanist_context, "to_dict")
            else self.botanist_context
        )
        return {
            "geo_context": geo,
            "environmental_snapshot": snapshot,
            "botanist_context": botanist,
            "atlas_provider_statuses": self.atlas.provider_statuses,
            "terra_provider_statuses": snapshot.get("provider_statuses", {}) if snapshot is not None else {},
            "source_record_ids": sorted(
                set(geo.get("source_record_ids", []))
                | set(snapshot.get("source_record_ids", []) if snapshot is not None else [])
            ),
            "model_run_count": self.model_run_count,
        }


class ContextCompiler:
    def __init__(self, repository: GaiaRepository, atlas: AtlasService, terra: TerraService) -> None:
        self.repository = repository
        self.atlas = atlas
        self.terra = terra

    async def build_environmental_context(
        self,
        context: ToolExecutionContext,
        location_id: str,
        *,
        timestamp: str | None = None,
    ) -> ContextBundle:
        location = self._load_location(context.organization_id, location_id)
        atlas_result = await self.atlas.build_geo_context(location, at_time=timestamp)
        terra_result = await self.terra.build_environmental_snapshot(location, context, timestamp=timestamp)
        return ContextBundle(
            geo_context=atlas_result.geo_context,
            environmental_snapshot=terra_result.snapshot,
            atlas=atlas_result,
            terra=terra_result,
            model_run_count=0,
        )

    async def build_geography_context(
        self,
        context: ToolExecutionContext,
        location_id: str,
        *,
        timestamp: str | None = None,
    ) -> ContextBundle:
        location = self._load_location(context.organization_id, location_id)
        atlas_result = await self.atlas.build_geo_context(location, at_time=timestamp)
        return ContextBundle(
            geo_context=atlas_result.geo_context,
            environmental_snapshot=None,
            atlas=atlas_result,
            terra=None,
            model_run_count=0,
        )

    def _load_location(self, organization_id: str, location_id: str) -> Location:
        raw_location = self.repository.get_location(organization_id, location_id)
        if raw_location is None:
            raise TenantAccessError("Location is missing or inaccessible")
        return Location(
            id=raw_location["id"],
            organization_id=raw_location["organization_id"],
            label=raw_location["label"],
            latitude=raw_location["latitude"],
            longitude=raw_location["longitude"],
            elevation_m=raw_location["elevation_m"],
            accuracy_m=raw_location["accuracy_m"],
            privacy_precision=raw_location["privacy_precision"],
            exact_coordinates_authorized=bool(raw_location["exact_coordinates_authorized"]),
            timezone=raw_location["timezone"],
            country_code=raw_location["country_code"],
            admin1=raw_location["admin1"],
            admin2=raw_location["admin2"],
            county_fips=raw_location["county_fips"],
        )
