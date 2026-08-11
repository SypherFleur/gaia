from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from packages.provenance import ProvenanceRecord, content_hash


@dataclass(frozen=True, slots=True)
class ProviderStatus:
    status: str
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class AdminResolution:
    status: ProviderStatus
    country: str | None = None
    country_code: str | None = None
    state_or_region: str | None = None
    state_code: str | None = None
    county_or_district: str | None = None
    county_fips: str | None = None
    timezone: str | None = None
    elevation_m: float | None = None
    provenance: list[ProvenanceRecord] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class WatershedResolution:
    status: ProviderStatus
    watershed: str | None = None
    provenance: list[ProvenanceRecord] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class HardinessResolution:
    status: ProviderStatus
    hardiness_zone: str | None = None
    provenance: list[ProvenanceRecord] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class AtlasZone:
    zone_id: str
    zone_type: str
    name: str
    authority: str
    effective_from: str | None = None
    effective_to: str | None = None
    source_reference: str | None = None


@dataclass(frozen=True, slots=True)
class RegulatoryZoneResolution:
    status: ProviderStatus
    regulatory_zones: list[AtlasZone] = field(default_factory=list)
    quarantine_zones: list[AtlasZone] = field(default_factory=list)
    pest_zones: list[AtlasZone] = field(default_factory=list)
    economic_regions: list[AtlasZone] = field(default_factory=list)
    provenance: list[ProvenanceRecord] = field(default_factory=list)


class GeographyProvider(Protocol):
    provider_id: str

    async def resolve_admin(self, latitude: float, longitude: float, at_time: str | None = None) -> AdminResolution: ...


class WatershedProvider(Protocol):
    provider_id: str

    async def resolve_watershed(self, latitude: float, longitude: float, at_time: str | None = None) -> WatershedResolution: ...


class HardinessProvider(Protocol):
    provider_id: str

    async def resolve_zone(self, latitude: float, longitude: float, at_time: str | None = None) -> HardinessResolution: ...


class RegulatoryGeometryProvider(Protocol):
    provider_id: str

    async def resolve_zones(self, latitude: float, longitude: float, at_time: str | None = None) -> RegulatoryZoneResolution: ...


class FixtureGeographyProvider:
    provider_id = "fixture-geography"

    async def resolve_admin(self, latitude: float, longitude: float, at_time: str | None = None) -> AdminResolution:
        if 29.0 <= latitude <= 31.5 and -99.0 <= longitude <= -96.0:
            payload = {"county": "Travis County", "state": "Texas", "fips": "48453"}
            return AdminResolution(
                status=ProviderStatus("AVAILABLE"),
                country="United States",
                country_code="US",
                state_or_region="Texas",
                state_code="TX",
                county_or_district="Travis County",
                county_fips="48453",
                timezone="America/Chicago",
                elevation_m=149.0,
                provenance=[
                    ProvenanceRecord(
                        provider=self.provider_id,
                        external_record_id="fixture-us-tx-travis",
                        canonical_url="fixture://geography/us/tx/travis",
                        authority="Fixture Geography Authority",
                        geographic_scope="US/TX/Travis",
                        license="fixture",
                        attribution="GAIA fixture",
                        content_hash=content_hash(payload),
                    )
                ],
            )
        return AdminResolution(
            status=ProviderStatus("AVAILABLE"),
            country="Singapore",
            country_code="SG",
            state_or_region="Central Region",
            county_or_district="Queenstown",
            timezone="Asia/Singapore",
            elevation_m=15.0,
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    external_record_id="fixture-sg-queenstown",
                    canonical_url="fixture://geography/sg/queenstown",
                    authority="Fixture Geography Authority",
                    geographic_scope="SG/Central/Queenstown",
                    license="fixture",
                    attribution="GAIA fixture",
                    content_hash=content_hash({"district": "Queenstown"}),
                )
            ],
        )


class FixtureWatershedProvider:
    provider_id = "fixture-watershed"

    async def resolve_watershed(self, latitude: float, longitude: float, at_time: str | None = None) -> WatershedResolution:
        return WatershedResolution(
            status=ProviderStatus("AVAILABLE"),
            watershed="Lower Colorado-Lavaca",
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    external_record_id="fixture-huc-1209",
                    canonical_url="fixture://watershed/lower-colorado-lavaca",
                    authority="Fixture Watershed Authority",
                    geographic_scope="US/TX",
                    license="fixture",
                    attribution="GAIA fixture",
                    content_hash=content_hash("Lower Colorado-Lavaca"),
                )
            ],
        )


class FixtureHardinessProvider:
    provider_id = "fixture-hardiness"

    async def resolve_zone(self, latitude: float, longitude: float, at_time: str | None = None) -> HardinessResolution:
        return HardinessResolution(
            status=ProviderStatus("AVAILABLE"),
            hardiness_zone="9a",
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    external_record_id="fixture-usda-zone-9a",
                    canonical_url="fixture://hardiness/usda/9a",
                    authority="Fixture Hardiness Authority",
                    geographic_scope="US/TX",
                    license="fixture",
                    attribution="GAIA fixture",
                    content_hash=content_hash("9a"),
                )
            ],
        )


class FixtureRegulatoryGeometryProvider:
    provider_id = "fixture-regulatory-geometry"

    async def resolve_zones(self, latitude: float, longitude: float, at_time: str | None = None) -> RegulatoryZoneResolution:
        return RegulatoryZoneResolution(
            status=ProviderStatus("AVAILABLE"),
            regulatory_zones=[
                AtlasZone(
                    zone_id="us-federal",
                    zone_type="jurisdiction",
                    name="United States federal jurisdiction",
                    authority="US federal",
                    source_reference="fixture://jurisdiction/us-federal",
                )
            ],
            economic_regions=[
                AtlasZone(
                    zone_id="tx-central",
                    zone_type="economic",
                    name="Central Texas",
                    authority="GAIA fixture",
                    source_reference="fixture://economic/tx-central",
                )
            ],
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    external_record_id="fixture-zones",
                    canonical_url="fixture://zones",
                    authority="Fixture Regulatory Geometry Authority",
                    geographic_scope="US/TX",
                    license="fixture",
                    attribution="GAIA fixture",
                    content_hash=content_hash("fixture-zones"),
                )
            ],
        )

