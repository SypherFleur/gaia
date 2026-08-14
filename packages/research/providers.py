from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from packages.domain import ResearchWork
from packages.provenance import ProvenanceRecord


JsonDict = dict[str, Any]


@dataclass(frozen=True, slots=True)
class ResearchCapabilities:
    provider_id: str
    keyword_search: bool = True
    semantic_search: bool = False
    metadata: bool = True
    abstract: bool = True
    full_text: bool = False
    citations: bool = False
    references: bool = False
    study_type: bool = True
    publication_date: bool = True
    author_metadata: bool = True
    doi: bool = True
    open_access_status: bool = True


@dataclass(frozen=True, slots=True)
class ResearchSearchRequest:
    query: str
    limit: int = 10
    context: JsonDict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ResearchFetchRequest:
    provider_id: str
    external_id: str
    source: str | None = None
    doi: str | None = None
    pmid: str | None = None
    pmcid: str | None = None


@dataclass(frozen=True, slots=True)
class ResearchDocument:
    work: ResearchWork
    provenance: list[ProvenanceRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    status: str = "AVAILABLE"
    raw_text: str | None = None


@dataclass(frozen=True, slots=True)
class ResearchSearchResponse:
    provider_id: str
    query: str
    works: list[ResearchWork] = field(default_factory=list)
    provenance: list[ProvenanceRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    status: str = "AVAILABLE"


class ResearchProvider(Protocol):
    provider_id: str

    async def capabilities(self) -> ResearchCapabilities: ...

    async def search(self, request: ResearchSearchRequest) -> ResearchSearchResponse: ...

    async def fetch(self, request: ResearchFetchRequest) -> ResearchDocument: ...


class DisabledResearchProvider:
    provider_id = "europe-pmc"

    async def capabilities(self) -> ResearchCapabilities:
        return ResearchCapabilities(provider_id=self.provider_id, keyword_search=False, metadata=False, abstract=False, study_type=False, publication_date=False, author_metadata=False, doi=False, open_access_status=False)

    async def search(self, request: ResearchSearchRequest) -> ResearchSearchResponse:
        return ResearchSearchResponse(provider_id=self.provider_id, query=request.query, status="UNAVAILABLE", warnings=["research_provider_disabled"])

    async def fetch(self, request: ResearchFetchRequest) -> ResearchDocument:
        return ResearchDocument(work=ResearchWork(title=""), status="UNAVAILABLE", warnings=["research_provider_disabled"])
