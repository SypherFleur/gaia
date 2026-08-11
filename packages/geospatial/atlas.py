from __future__ import annotations

from dataclasses import dataclass

from packages.domain import GeoContext, Location, SourceRecord
from packages.geospatial.privacy import Coordinate, PrivacyReducedCoordinate, reduce_coordinate_precision
from packages.geospatial.providers import GeographyProvider, HardinessProvider, RegulatoryGeometryProvider, WatershedProvider
from packages.persistence import GaiaRepository
from packages.provenance import ProvenanceRecord


@dataclass(frozen=True, slots=True)
class AtlasResult:
    geo_context: GeoContext
    display_coordinate: PrivacyReducedCoordinate
    provider_statuses: dict[str, str]


class AtlasService:
    def __init__(
        self,
        repository: GaiaRepository,
        geography_provider: GeographyProvider,
        watershed_provider: WatershedProvider,
        hardiness_provider: HardinessProvider,
        regulatory_geometry_provider: RegulatoryGeometryProvider,
    ) -> None:
        self.repository = repository
        self.geography_provider = geography_provider
        self.watershed_provider = watershed_provider
        self.hardiness_provider = hardiness_provider
        self.regulatory_geometry_provider = regulatory_geometry_provider

    async def build_geo_context(self, location: Location, *, at_time: str | None = None, persist: bool = True) -> AtlasResult:
        if location.latitude is None or location.longitude is None:
            raise ValueError("Atlas requires latitude and longitude")

        admin = await self.geography_provider.resolve_admin(location.latitude, location.longitude, at_time)
        watershed = await self.watershed_provider.resolve_watershed(location.latitude, location.longitude, at_time)
        hardiness = await self.hardiness_provider.resolve_zone(location.latitude, location.longitude, at_time)
        zones = await self.regulatory_geometry_provider.resolve_zones(location.latitude, location.longitude, at_time)

        provenance = [*admin.provenance, *watershed.provenance, *hardiness.provenance, *zones.provenance]
        source_record_ids = [self._persist_source_record(location.organization_id, item) for item in provenance]

        geo_context = GeoContext(
            organization_id=location.organization_id,
            location_id=location.id,
            country=admin.country,
            country_code=admin.country_code,
            state_or_region=admin.state_or_region,
            state_code=admin.state_code,
            county_or_district=admin.county_or_district,
            county_fips=admin.county_fips,
            timezone=admin.timezone,
            elevation_m=admin.elevation_m,
            hardiness_zone=hardiness.hardiness_zone,
            watershed=watershed.watershed,
            regulatory_zones=[zone.name for zone in zones.regulatory_zones],
            quarantine_zones=[zone.name for zone in zones.quarantine_zones],
            pest_zones=[zone.name for zone in zones.pest_zones],
            economic_regions=[zone.name for zone in zones.economic_regions],
            source_record_ids=source_record_ids,
        )
        if persist:
            self.repository.create_geo_context(geo_context)

        display_coordinate = reduce_coordinate_precision(
            location.latitude,
            location.longitude,
            location.privacy_precision,
            county_centroid=Coordinate(location.latitude, location.longitude),
        )
        return AtlasResult(
            geo_context=geo_context,
            display_coordinate=display_coordinate,
            provider_statuses={
                "admin": admin.status.status,
                "watershed": watershed.status.status,
                "hardiness": hardiness.status.status,
                "regulatory_geometry": zones.status.status,
            },
        )

    def _persist_source_record(self, organization_id: str, provenance: ProvenanceRecord) -> str:
        source_record = SourceRecord(
            organization_id=organization_id,
            provider=provenance.provider,
            source_type="geospatial",
            canonical_url=provenance.canonical_url,
            external_record_id=provenance.external_record_id,
            title=provenance.authority or provenance.provider,
            authority=provenance.authority,
            retrieved_at=provenance.retrieved_at,
            observed_at=provenance.observed_at,
            valid_from=provenance.valid_at,
            license=provenance.license,
            attribution=provenance.attribution,
            content_hash=provenance.content_hash,
        )
        self.repository.create_source_record(source_record)
        return source_record.id

