from __future__ import annotations

from packages.domain import ResearchWork
from packages.provenance import ProvenanceRecord, content_hash
from packages.research.providers import ResearchCapabilities, ResearchDocument, ResearchFetchRequest, ResearchSearchRequest, ResearchSearchResponse


class FixtureResearchProvider:
    provider_id = "europe-pmc"

    def __init__(self, *, unavailable: bool = False, no_results: bool = False, include_duplicate: bool = False) -> None:
        self.unavailable = unavailable
        self.no_results = no_results
        self.include_duplicate = include_duplicate
        self.search_calls = 0
        self.fetch_calls = 0

    async def capabilities(self) -> ResearchCapabilities:
        return ResearchCapabilities(provider_id=self.provider_id)

    async def search(self, request: ResearchSearchRequest) -> ResearchSearchResponse:
        self.search_calls += 1
        if self.unavailable:
            return ResearchSearchResponse(provider_id=self.provider_id, query=request.query, status="PROVIDER_ERROR", warnings=["fixture_research_unavailable"])
        if self.no_results:
            return ResearchSearchResponse(provider_id=self.provider_id, query=request.query, status="AVAILABLE", works=[], provenance=[_source("fixture-empty", request.query)])
        works = _fixture_works()
        query = request.query.lower()
        if "moon" in query or "lunar" in query:
            selected = [works[1], works[2]]
        elif "greenhouse" in query:
            selected = [works[3]]
        elif "retract" in query:
            selected = [works[4]]
        else:
            selected = [works[0], works[3]]
        if self.include_duplicate:
            selected.append(_duplicate_calcium_work())
        return ResearchSearchResponse(
            provider_id=self.provider_id,
            query=request.query,
            works=selected[: request.limit],
            provenance=[_source("fixture-search", request.query)],
        )

    async def fetch(self, request: ResearchFetchRequest) -> ResearchDocument:
        self.fetch_calls += 1
        if self.unavailable:
            return ResearchDocument(work=ResearchWork(title=""), status="PROVIDER_ERROR", warnings=["fixture_fetch_unavailable"])
        for work in _fixture_works():
            if request.external_id in {work.provider_ids.get("europe-pmc"), work.doi, work.pmid, work.pmcid, work.id}:
                return ResearchDocument(work=work, provenance=[_source("fixture-fetch", request.external_id)])
        return ResearchDocument(work=ResearchWork(title=""), status="UNAVAILABLE", warnings=["fixture_work_not_found"], provenance=[_source("fixture-fetch-missing", request.external_id)])


def _fixture_works() -> list[ResearchWork]:
    return [
        ResearchWork(
            id="work-calcium-review",
            title="Blossom-end rot of tomato: calcium transport, water stress, and management",
            abstract="A review finds blossom-end rot is linked to calcium transport and water stress; foliar calcium sprays show inconsistent benefit.",
            publication_year=2019,
            journal="Horticultural Reviews",
            doi="10.1000/ber-review",
            pmid="10000001",
            provider_ids={"europe-pmc": "MED/10000001"},
            publication_types=["Review"],
            open_access_status="unknown",
            retracted_status="not_flagged",
            study_type="review",
            authors=[{"display_name": "Doe J"}],
            evidence_policy=_policy(True),
        ),
        ResearchWork(
            id="work-lunar-controlled",
            title="Controlled germination response under simulated lunar illumination",
            abstract="A controlled experiment reported small germination differences under simulated low lunar light.",
            publication_year=2014,
            journal="Plant Signals",
            doi="10.1000/lunar-controlled",
            pmid="10000002",
            provider_ids={"europe-pmc": "MED/10000002"},
            publication_types=["Journal Article"],
            open_access_status="unknown",
            retracted_status="not_flagged",
            study_type="controlled experiment",
            authors=[{"display_name": "Moon A"}],
            evidence_policy=_policy(True),
        ),
        ResearchWork(
            id="work-lunar-review",
            title="Agronomic evidence for lunar phase planting remains limited",
            abstract="A review concludes lunar planting evidence is mixed and insufficient relative to soil temperature, water, and cultivar effects.",
            publication_year=2021,
            journal="Agronomy Evidence",
            doi="10.1000/lunar-review",
            pmid="10000003",
            provider_ids={"europe-pmc": "MED/10000003"},
            publication_types=["Review"],
            open_access_status="open",
            retracted_status="not_flagged",
            study_type="review",
            authors=[{"display_name": "Review R"}],
            evidence_policy=_policy(True),
        ),
        ResearchWork(
            id="work-greenhouse",
            title="Greenhouse calcium sprays in tomato under controlled humidity",
            abstract="A greenhouse trial reported cultivar-specific effects; field applicability is limited.",
            publication_year=2018,
            journal="Protected Horticulture",
            doi=None,
            pmid=None,
            provider_ids={"europe-pmc": "AGR/greenhouse-calcium"},
            publication_types=["Journal Article"],
            open_access_status="unknown",
            retracted_status="not_flagged",
            study_type="controlled experiment",
            authors=[{"display_name": "Green G"}],
            evidence_policy=_policy(True),
        ),
        ResearchWork(
            id="work-retracted",
            title="Retracted publication: impossible tomato yield claims",
            abstract="This work has been retracted.",
            publication_year=2016,
            journal="Retractions in Agronomy",
            doi="10.1000/retracted-yield",
            pmid="10000004",
            provider_ids={"europe-pmc": "MED/10000004"},
            publication_types=["Retracted Publication"],
            open_access_status="unknown",
            retracted_status="retracted",
            study_type="unknown",
            authors=[{"display_name": "Error E"}],
            evidence_policy=_policy(True),
        ),
    ]


def _duplicate_calcium_work() -> ResearchWork:
    duplicate = _fixture_works()[0]
    duplicate.provider_ids["europe-pmc-alt"] = "PMC/duplicate"
    return duplicate


def _policy(abstract_allowed: bool) -> dict:
    return {
        "metadata_allowed": True,
        "abstract_allowed": abstract_allowed,
        "full_text_allowed": False,
        "redistribution_allowed": "unknown",
        "embedding_allowed": "unknown",
        "training_allowed": "unknown",
    }


def _source(record_id: str, query: str) -> ProvenanceRecord:
    payload = {"record_id": record_id, "query": query}
    return ProvenanceRecord(
        provider="europe-pmc",
        external_record_id=record_id,
        canonical_url=f"fixture://europe-pmc/{record_id}",
        authority="Europe PMC fixture",
        geographic_scope="research literature metadata",
        license="fixture",
        attribution="Europe PMC fixture",
        content_hash=content_hash(payload),
    )
