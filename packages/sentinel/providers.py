from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from packages.provenance import ProvenanceRecord


JsonDict = dict[str, Any]


@dataclass(frozen=True, slots=True)
class RegulationRequest:
    jurisdiction_pack: str
    origin: JsonDict = field(default_factory=dict)
    destination: JsonDict = field(default_factory=dict)
    species: str | None = None
    plant_part: str = "unknown"
    live_plant: bool = False
    soil_attached: bool = False
    planned_date: str | None = None
    metadata: JsonDict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RegulatoryRule:
    rule_id: str
    jurisdiction_pack: str
    authority: str
    authority_level: str
    jurisdiction: str
    regulated_taxa: list[JsonDict] = field(default_factory=list)
    regulated_articles: list[str] = field(default_factory=list)
    plant_parts: list[str] = field(default_factory=list)
    pest_or_disease: str | None = None
    origin_scope: JsonDict = field(default_factory=dict)
    destination_scope: JsonDict = field(default_factory=dict)
    status_effect: str = "CONDITIONAL"
    conditions: list[JsonDict] = field(default_factory=list)
    exceptions: list[JsonDict] = field(default_factory=list)
    permits: list[JsonDict] = field(default_factory=list)
    treatments: list[JsonDict] = field(default_factory=list)
    inspection: list[JsonDict] = field(default_factory=list)
    reporting: list[JsonDict] = field(default_factory=list)
    effective_from: str | None = None
    effective_to: str | None = None
    last_verified_at: str | None = None
    freshness: str = "CURRENT"
    authority_metadata: JsonDict = field(default_factory=dict)
    source_reference: str | None = None


@dataclass(frozen=True, slots=True)
class RegulatoryZone:
    zone_id: str
    jurisdiction_pack: str
    authority: str
    zone_type: str
    name: str
    area_scope: JsonDict = field(default_factory=dict)
    geometry_reference: str | None = None
    freshness: str = "CURRENT"


@dataclass(frozen=True, slots=True)
class RegulationResponse:
    provider_id: str
    status: str
    rules: list[RegulatoryRule] = field(default_factory=list)
    zones: list[RegulatoryZone] = field(default_factory=list)
    alerts: list[JsonDict] = field(default_factory=list)
    reporting_requirements: list[JsonDict] = field(default_factory=list)
    freshness: str = "UNAVAILABLE"
    provenance: list[ProvenanceRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class RegulationProvider(Protocol):
    provider_id: str

    async def resolve_zones(self, request: RegulationRequest) -> RegulationResponse: ...

    async def movement_rules(self, request: RegulationRequest) -> RegulationResponse: ...

    async def pest_alerts(self, request: RegulationRequest) -> RegulationResponse: ...

    async def reporting_requirements(self, request: RegulationRequest) -> RegulationResponse: ...

