from __future__ import annotations

from packages.botany.providers import GermplasmSearchResult, TaxonomyResolution
from packages.provenance import ProvenanceRecord, content_hash


class FixtureGBIFProvider:
    provider_id = "gbif"

    def __init__(self, *, unavailable: bool = False) -> None:
        self.unavailable = unavailable
        self.calls = 0

    async def resolve_taxon(self, query: str) -> TaxonomyResolution:
        self.calls += 1
        if self.unavailable:
            return TaxonomyResolution(status="PROVIDER_ERROR", query=query, warnings=["gbif_unavailable"])
        normalized = query.strip().lower()
        if normalized in {"solanum lycopersicum", "tomato"}:
            data = _tomato_taxonomy(status="ACCEPTED", query=query, matched_name="Solanum lycopersicum")
            return data
        if normalized == "lycopersicon esculentum":
            data = _tomato_taxonomy(status="SYNONYM", query=query, matched_name="Lycopersicon esculentum")
            return data
        if normalized in {"mint", "bean"}:
            return TaxonomyResolution(
                status="AMBIGUOUS",
                query=query,
                alternatives=[
                    {"scientific_name": "Mentha spicata", "canonical_taxon_id": "gbif:2927293"},
                    {"scientific_name": "Mentha x piperita", "canonical_taxon_id": "gbif:2927324"},
                ],
                provenance=[_gbif_provenance("fixture://gbif/species/search?name=mint", "fixture-gbif-ambiguous")],
                warnings=["ambiguous_common_name"],
            )
        return TaxonomyResolution(
            status="UNRESOLVED",
            query=query,
            provenance=[_gbif_provenance("fixture://gbif/species/match?name=unknown", "fixture-gbif-no-match")],
            warnings=["taxon_unresolved"],
        )


class FixtureGenesysProvider:
    provider_id = "genesys-pgr"

    def __init__(self, *, unavailable: bool = False, include_traits: bool = True) -> None:
        self.unavailable = unavailable
        self.include_traits = include_traits
        self.calls = 0

    async def search_accessions(self, query: str, *, limit: int = 10) -> GermplasmSearchResult:
        self.calls += 1
        if self.unavailable:
            return GermplasmSearchResult(status="PROVIDER_ERROR", query=query, warnings=["genesys_unavailable"])
        traits = [{"trait": "heat tolerance", "evidence": "published descriptor fixture"}] if self.include_traits else []
        accession = {
            "accession_id": "genesys:VIGNA-IITA-TVu-12345",
            "accession_number": "TVu-12345",
            "taxon": "Vigna unguiculata",
            "crop": "cowpea",
            "institute_code": "NGA039",
            "institute_name": "IITA Genetic Resources Center fixture",
            "origin_country": "Nigeria",
            "traits": traits,
            "availability_verified": False,
            "legal_movement_verified": False,
            "commercial_availability_verified": False,
            "semantic_caveat": "Genesys discovery does not prove availability, legal shipment, import eligibility, cost, or agronomic suitability.",
        }
        return GermplasmSearchResult(
            status="AVAILABLE",
            query=query,
            accessions=[accession][:limit],
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    external_record_id="VIGNA-IITA-TVu-12345",
                    canonical_url="fixture://genesys/accessions/VIGNA-IITA-TVu-12345",
                    authority="Genesys PGR",
                    geographic_scope="global accession passport fixture",
                    license="unknown",
                    attribution="Genesys PGR / Crop Trust",
                    content_hash=content_hash(accession),
                )
            ],
        )


def _tomato_taxonomy(*, status: str, query: str, matched_name: str) -> TaxonomyResolution:
    payload = {
        "usageKey": 2930137,
        "scientificName": "Solanum lycopersicum L.",
        "canonicalName": "Solanum lycopersicum",
        "kingdom": "Plantae",
    }
    return TaxonomyResolution(
        status=status,
        query=query,
        canonical_taxon_id="gbif:2930137",
        accepted_scientific_name="Solanum lycopersicum",
        matched_name=matched_name,
        match_type="EXACT",
        rank="SPECIES",
        kingdom="Plantae",
        family="Solanaceae",
        genus="Solanum",
        species="lycopersicum",
        common_names=["tomato"],
        synonyms=[{"name": "Lycopersicon esculentum", "relationship": "synonym", "source": "gbif"}],
        external_source_ids={"gbif_usage_key": "2930137", "gbif_accepted_usage_key": "2930137"},
        provenance=[_gbif_provenance("fixture://gbif/species/2930137", "2930137", payload)],
    )


def _gbif_provenance(url: str, external_record_id: str, payload: dict | str | None = None) -> ProvenanceRecord:
    return ProvenanceRecord(
        provider="gbif",
        external_record_id=external_record_id,
        canonical_url=url,
        authority="GBIF Backbone Taxonomy",
        geographic_scope="global taxonomy",
        license="unknown",
        attribution="GBIF",
        content_hash=content_hash(payload or external_record_id),
    )
