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
        if normalized in {"vigna unguiculata", "cowpea", "black-eyed pea"}:
            return _cowpea_taxonomy(status="ACCEPTED", query=query, matched_name="Vigna unguiculata")
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
        native_range=[{"region": "western South America", "source": "GBIF fixture", "certainty": "broad_source_backed"}],
        introduced_range=[{"region": "cultivated globally", "source": "GBIF fixture", "certainty": "broad_source_backed"}],
        biomes=["temperate cropland", "subtropical cropland", "tropical highland agriculture"],
        ecoregions=[{"name": "cultivated and naturalized records are global; local occurrence does not prove suitability", "source": "GBIF fixture"}],
        climate_associations={"temperature": "warm-season crop; frost-sensitive", "moisture": "moderate water demand with disease risk under prolonged leaf wetness"},
        crop_origin={"crop": "tomato", "origin_region": "Andean/western South American domestication context", "source": "GBIF fixture"},
        plant_traits={"growth_habit": "herbaceous vine/forb", "lifecycle": "annual in temperate production; perennial in frost-free conditions"},
        agricultural_uses={"crop_use": ["vegetable crop"], "food_use": ["fruit"], "forage_use": [], "ornamental_use": []},
        occurrence_sources=[{"provider": "gbif", "record_type": "taxonomy_and_occurrence_gateway", "note": "Occurrence evidence is presence data, not cultivation suitability."}],
        provenance=[_gbif_provenance("fixture://gbif/species/2930137", "2930137", payload)],
    )


def _cowpea_taxonomy(*, status: str, query: str, matched_name: str) -> TaxonomyResolution:
    payload = {
        "usageKey": 2959342,
        "scientificName": "Vigna unguiculata (L.) Walp.",
        "canonicalName": "Vigna unguiculata",
        "kingdom": "Plantae",
    }
    return TaxonomyResolution(
        status=status,
        query=query,
        canonical_taxon_id="gbif:2959342",
        accepted_scientific_name="Vigna unguiculata",
        matched_name=matched_name,
        match_type="EXACT",
        rank="SPECIES",
        kingdom="Plantae",
        family="Fabaceae",
        genus="Vigna",
        species="unguiculata",
        common_names=["cowpea", "black-eyed pea"],
        synonyms=[],
        external_source_ids={"gbif_usage_key": "2959342", "gbif_accepted_usage_key": "2959342"},
        native_range=[{"region": "Africa", "source": "GBIF fixture", "certainty": "broad_source_backed"}],
        introduced_range=[{"region": "cultivated in tropical and subtropical regions worldwide", "source": "GBIF fixture", "certainty": "broad_source_backed"}],
        biomes=["tropical savanna agriculture", "semi-arid cropland", "subtropical cropland"],
        ecoregions=[{"name": "African dryland and savanna farming systems", "source": "GBIF fixture"}],
        climate_associations={"temperature": "warm-season legume", "moisture": "often associated with drought-prone production systems, subject to cultivar-specific variation"},
        crop_origin={"crop": "cowpea", "origin_region": "Africa", "source": "GBIF fixture"},
        plant_traits={"growth_habit": "herbaceous legume", "lifecycle": "annual"},
        agricultural_uses={"crop_use": ["pulse crop", "cover crop"], "food_use": ["seed", "leafy vegetable in some regions"], "forage_use": ["forage"], "ornamental_use": []},
        occurrence_sources=[{"provider": "gbif", "record_type": "taxonomy_and_occurrence_gateway", "note": "Occurrence evidence is presence data, not cultivation suitability."}],
        provenance=[_gbif_provenance("fixture://gbif/species/2959342", "2959342", payload)],
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
