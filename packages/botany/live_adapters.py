from __future__ import annotations

import asyncio
import json
import urllib.parse
import urllib.request

from packages.botany.providers import GermplasmSearchResult, TaxonomyResolution
from packages.provenance import ProvenanceRecord, content_hash


class GBIFApiAdapter:
    provider_id = "gbif"

    def __init__(self, *, user_agent: str, base_url: str = "https://api.gbif.org/v1", timeout_seconds: float = 10.0) -> None:
        if not user_agent:
            raise ValueError("GBIF adapter requires a User-Agent")
        self.user_agent = user_agent
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def resolve_taxon(self, query: str) -> TaxonomyResolution:
        return await asyncio.to_thread(self._resolve_taxon_sync, query)

    def _resolve_taxon_sync(self, query: str) -> TaxonomyResolution:
        url = f"{self.base_url}/species/match?verbose=true&name={urllib.parse.quote(query)}"
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent, "Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return self.normalize_match_response(query, payload, url)

    def normalize_match_response(self, query: str, payload: dict, url: str | None = None) -> TaxonomyResolution:
        match_type = payload.get("matchType")
        if match_type == "NONE":
            status = "UNRESOLVED"
        elif payload.get("synonym") is True or payload.get("status") == "SYNONYM":
            status = "SYNONYM"
        elif payload.get("alternatives"):
            status = "AMBIGUOUS"
        else:
            status = "ACCEPTED"
        canonical_key = payload.get("acceptedUsageKey") or payload.get("usageKey")
        scientific = payload.get("acceptedScientificName") or payload.get("scientificName") or payload.get("canonicalName")
        synonyms = []
        if status == "SYNONYM" and payload.get("scientificName"):
            synonyms.append({"name": payload["scientificName"], "relationship": "synonym", "source": "gbif"})
        provenance = ProvenanceRecord(
            provider=self.provider_id,
            external_record_id=str(canonical_key) if canonical_key else None,
            canonical_url=url or "https://api.gbif.org/v1/species/match",
            authority="GBIF Backbone Taxonomy",
            geographic_scope="global taxonomy",
            license="unknown",
            attribution="GBIF",
            content_hash=content_hash(payload),
        )
        return TaxonomyResolution(
            status=status,
            query=query,
            canonical_taxon_id=f"gbif:{canonical_key}" if canonical_key else None,
            accepted_scientific_name=scientific,
            matched_name=payload.get("scientificName") or payload.get("canonicalName"),
            match_type=match_type,
            rank=payload.get("rank"),
            kingdom=payload.get("kingdom"),
            family=payload.get("family"),
            genus=payload.get("genus"),
            species=payload.get("species"),
            synonyms=synonyms,
            alternatives=payload.get("alternatives") or [],
            external_source_ids={"gbif_usage_key": str(payload.get("usageKey"))} if payload.get("usageKey") else {},
            provenance=[provenance],
            warnings=["occurrence_is_not_cultivation_suitability"],
        )


class GenesysPGRAdapter:
    provider_id = "genesys-pgr"

    def normalize_accession_search(self, query: str, payload: dict) -> GermplasmSearchResult:
        rows = payload.get("content") or payload.get("results") or payload.get("accessions") or []
        accessions = []
        for row in rows:
            taxonomy = row.get("taxonomy") or {}
            institute = row.get("institute") or {}
            accession_id = row.get("doi") or row.get("uuid") or row.get("id") or row.get("accessionNumber")
            traits = row.get("traits") or row.get("descriptors") or []
            accessions.append(
                {
                    "accession_id": accession_id,
                    "accession_number": row.get("accessionNumber"),
                    "taxon": " ".join(part for part in [taxonomy.get("genus"), taxonomy.get("species")] if part) or row.get("cropName"),
                    "crop": row.get("cropName") or row.get("crop"),
                    "institute_code": row.get("instituteCode") or institute.get("code"),
                    "institute_name": institute.get("fullName") or row.get("instituteName"),
                    "origin_country": row.get("origCty") or row.get("originCountry"),
                    "traits": traits,
                    "availability_verified": False,
                    "legal_movement_verified": False,
                    "commercial_availability_verified": False,
                    "semantic_caveat": "Genesys discovery does not prove availability, legal shipment, import eligibility, cost, or agronomic suitability.",
                }
            )
        provenance = ProvenanceRecord(
            provider=self.provider_id,
            external_record_id=None,
            canonical_url="https://www.genesys-pgr.org/documentation/apis",
            authority="Genesys PGR",
            geographic_scope="global accession passport data",
            license="unknown",
            attribution="Genesys PGR / Crop Trust",
            content_hash=content_hash(payload),
        )
        return GermplasmSearchResult(status="AVAILABLE" if accessions else "UNAVAILABLE", query=query, accessions=accessions, provenance=[provenance])
