from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from packages.provenance import ProvenanceRecord


JsonDict = dict[str, Any]
TaxonomyStatus = Literal["ACCEPTED", "SYNONYM", "AMBIGUOUS", "UNRESOLVED", "PROVIDER_ERROR"]
GermplasmStatus = Literal["AVAILABLE", "UNAVAILABLE", "PROVIDER_ERROR"]


@dataclass(frozen=True, slots=True)
class TaxonomyResolution:
    status: TaxonomyStatus
    query: str
    canonical_taxon_id: str | None = None
    accepted_scientific_name: str | None = None
    matched_name: str | None = None
    match_type: str | None = None
    rank: str | None = None
    kingdom: str | None = None
    family: str | None = None
    genus: str | None = None
    species: str | None = None
    subspecies: str | None = None
    common_names: list[str] = field(default_factory=list)
    synonyms: list[JsonDict] = field(default_factory=list)
    alternatives: list[JsonDict] = field(default_factory=list)
    external_source_ids: JsonDict = field(default_factory=dict)
    native_range: list[JsonDict] = field(default_factory=list)
    introduced_range: list[JsonDict] = field(default_factory=list)
    biomes: list[str] = field(default_factory=list)
    ecoregions: list[JsonDict] = field(default_factory=list)
    climate_associations: JsonDict = field(default_factory=dict)
    crop_origin: JsonDict = field(default_factory=dict)
    plant_traits: JsonDict = field(default_factory=dict)
    agricultural_uses: JsonDict = field(default_factory=dict)
    occurrence_sources: list[JsonDict] = field(default_factory=list)
    research_sources: list[JsonDict] = field(default_factory=list)
    provenance: list[ProvenanceRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class GermplasmSearchResult:
    status: GermplasmStatus
    query: str
    accessions: list[JsonDict] = field(default_factory=list)
    provenance: list[ProvenanceRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class TaxonomyProvider(Protocol):
    provider_id: str

    async def resolve_taxon(self, query: str) -> TaxonomyResolution: ...


class GermplasmProvider(Protocol):
    provider_id: str

    async def search_accessions(self, query: str, *, limit: int = 10) -> GermplasmSearchResult: ...


class DisabledTaxonomyProvider:
    provider_id = "taxonomy-disabled"

    async def resolve_taxon(self, query: str) -> TaxonomyResolution:
        return TaxonomyResolution(status="PROVIDER_ERROR", query=query, warnings=["taxonomy_provider_disabled"])


class DisabledGermplasmProvider:
    provider_id = "germplasm-disabled"

    async def search_accessions(self, query: str, *, limit: int = 10) -> GermplasmSearchResult:
        return GermplasmSearchResult(status="UNAVAILABLE", query=query, warnings=["germplasm_provider_disabled"])
