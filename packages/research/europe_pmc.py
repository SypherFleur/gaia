from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any
from urllib import parse, request as urlrequest

from packages.domain import ResearchWork
from packages.provenance import ProvenanceRecord, content_hash
from packages.research.providers import (
    ResearchCapabilities,
    ResearchDocument,
    ResearchFetchRequest,
    ResearchProvider,
    ResearchSearchRequest,
    ResearchSearchResponse,
)


JsonDict = dict[str, Any]


EUROPE_PMC_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


@dataclass(slots=True)
class EuropePMCAdapter(ResearchProvider):
    base_url: str = EUROPE_PMC_SEARCH_URL
    timeout_seconds: float = 15.0
    provider_id: str = "europe-pmc"

    async def capabilities(self) -> ResearchCapabilities:
        return ResearchCapabilities(
            provider_id=self.provider_id,
            keyword_search=True,
            metadata=True,
            abstract=True,
            full_text=False,
            publication_date=True,
            author_metadata=True,
            doi=True,
            open_access_status=True,
        )

    async def search(self, request: ResearchSearchRequest) -> ResearchSearchResponse:
        params = {
            "query": request.query,
            "format": "json",
            "pageSize": str(request.limit),
            "resultType": "core",
        }
        url = self.base_url + "?" + parse.urlencode(params)
        try:
            payload = await asyncio.to_thread(self._get_json, url)
        except Exception as exc:
            return ResearchSearchResponse(provider_id=self.provider_id, query=request.query, status="PROVIDER_ERROR", warnings=[f"europe_pmc_error:{exc.__class__.__name__}"])
        works = [normalize_europe_pmc_work(item) for item in payload.get("resultList", {}).get("result", [])]
        return ResearchSearchResponse(
            provider_id=self.provider_id,
            query=request.query,
            works=works,
            provenance=[_provenance(self.provider_id, url, payload, "Europe PMC search")],
            status="AVAILABLE",
        )

    async def fetch(self, request: ResearchFetchRequest) -> ResearchDocument:
        query = request.doi or request.pmid or request.pmcid or request.external_id
        response = await self.search(ResearchSearchRequest(query=query, limit=1))
        if not response.works:
            return ResearchDocument(
                work=ResearchWork(title=""),
                status="UNAVAILABLE",
                warnings=["research_work_not_found"],
                provenance=response.provenance,
            )
        return ResearchDocument(work=response.works[0], provenance=response.provenance, status=response.status, warnings=response.warnings)

    def _get_json(self, url: str) -> JsonDict:
        http_request = urlrequest.Request(url, headers={"Accept": "application/json", "User-Agent": "GAIA Protocol Two Scholar/0.1"})
        with urlrequest.urlopen(http_request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))


def normalize_europe_pmc_work(item: JsonDict) -> ResearchWork:
    doi = _clean_id(item.get("doi"))
    pmid = _clean_id(item.get("pmid"))
    pmcid = _clean_id(item.get("pmcid"))
    publication_types = _list_field(item.get("pubTypeList", {}).get("pubType")) or _list_field(item.get("pubType"))
    evidence_policy = {
        "metadata_allowed": True,
        "abstract_allowed": bool(item.get("abstractText")),
        "full_text_allowed": bool(item.get("isOpenAccess") in {"Y", True} and item.get("fullTextUrlList")),
        "redistribution_allowed": "unknown",
        "embedding_allowed": "unknown",
        "training_allowed": "unknown",
    }
    return ResearchWork(
        title=item.get("title") or "Untitled research work",
        abstract=item.get("abstractText"),
        publication_year=_int_or_none(item.get("pubYear") or item.get("firstPublicationDate", "")[:4]),
        journal=item.get("journalTitle"),
        doi=doi,
        pmid=pmid,
        pmcid=pmcid,
        provider_ids={"europe-pmc": item.get("id") or pmid or pmcid or doi},
        publication_types=publication_types,
        open_access_status="open" if item.get("isOpenAccess") in {"Y", True} else "unknown",
        retracted_status=_retracted_status(item),
        study_type=infer_study_type(publication_types, item.get("title", ""), item.get("abstractText", "")),
        authors=_authors(item),
        evidence_policy=evidence_policy,
    )


def infer_study_type(publication_types: list[str], title: str, abstract: str | None) -> str:
    text = " ".join(publication_types + [title, abstract or ""]).lower()
    if "meta-analysis" in text or "meta analysis" in text:
        return "meta-analysis"
    if "systematic review" in text:
        return "systematic review"
    if "randomized" in text or "randomised" in text:
        return "randomized controlled trial"
    if "field trial" in text:
        return "field trial"
    if "greenhouse" in text or "controlled experiment" in text:
        return "controlled experiment"
    if "laboratory" in text or "in vitro" in text:
        return "laboratory study"
    if "review" in text:
        return "review"
    if "case study" in text:
        return "case study"
    if "observational" in text:
        return "observational study"
    return "unknown"


def _authors(item: JsonDict) -> list[JsonDict]:
    authors = _list_field(item.get("authorString"))
    if authors:
        return [{"display_name": author.strip()} for author in str(item.get("authorString", "")).split(",") if author.strip()]
    author_list = item.get("authorList", {}).get("author", [])
    if isinstance(author_list, dict):
        author_list = [author_list]
    return [
        {
            "display_name": author.get("fullName") or author.get("lastName"),
            "given_name": author.get("firstName"),
            "family_name": author.get("lastName"),
            "orcid": author.get("authorId", {}).get("value") if isinstance(author.get("authorId"), dict) else None,
        }
        for author in author_list
        if isinstance(author, dict)
    ]


def _retracted_status(item: JsonDict) -> str:
    text = " ".join(str(value) for value in [item.get("title"), item.get("pubType"), item.get("abstractText")]).lower()
    if "retracted publication" in text or "retraction of publication" in text or "retracted" in text:
        return "retracted"
    if "correction" in text or "erratum" in text:
        return "corrected"
    return "not_flagged"


def _list_field(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [value]
    return [str(value)]


def _clean_id(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _provenance(provider_id: str, url: str, payload: JsonDict, title: str) -> ProvenanceRecord:
    return ProvenanceRecord(
        provider=provider_id,
        external_record_id=title,
        canonical_url=url,
        authority="Europe PMC",
        geographic_scope="research literature metadata",
        license="Europe PMC terms",
        attribution="Europe PMC",
        content_hash=content_hash(payload),
    )

