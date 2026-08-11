from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from packages.botany import BotanistService
from packages.context import ContextCompiler
from packages.domain import EvidenceSynthesis, ResearchClaim, ResearchCollection, ResearchWork, SourceRecord
from packages.model_gateway import ModelGateway, ModelRequest
from packages.persistence import GaiaRepository
from packages.provenance import ProvenanceRecord
from packages.research.prompts import build_scholar_prompt
from packages.research.query import normalize_research_query, plan_research_queries
from packages.research.tools import EuropePMCFetchTool, EuropePMCSearchTool
from packages.research.validation import ResearchValidationError, validate_synthesis_draft
from packages.tools import ToolExecutionContext, ToolGateway, ToolRequest, ToolResult


JsonDict = dict[str, Any]


@dataclass(frozen=True, slots=True)
class ScholarContext:
    research_question: str
    works: list[JsonDict]
    claims: list[JsonDict]
    evidence_quality: str
    contradictions: list[JsonDict]
    applicability: JsonDict
    provenance: list[str]
    work_ids: list[str]
    model_run_count: int = 0

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ScholarSearchResult:
    query_variants: list[str]
    works: list[ResearchWork]
    provider_results: list[ToolResult]
    source_record_ids: list[str]


class ScholarService:
    def __init__(
        self,
        *,
        repository: GaiaRepository,
        tool_gateway: ToolGateway,
        search_tool: EuropePMCSearchTool,
        fetch_tool: EuropePMCFetchTool,
        model_gateway: ModelGateway | None = None,
        botanist: BotanistService | None = None,
        context_compiler: ContextCompiler | None = None,
        default_model_provider_id: str = "ollama-local",
    ) -> None:
        self.repository = repository
        self.tool_gateway = tool_gateway
        self.search_tool = search_tool
        self.fetch_tool = fetch_tool
        self.model_gateway = model_gateway
        self.botanist = botanist
        self.context_compiler = context_compiler
        self.default_model_provider_id = default_model_provider_id

    async def search(self, context: ToolExecutionContext, question: str, *, botanist_context: JsonDict | None = None, limit: int = 10) -> ScholarSearchResult:
        variants = plan_research_queries(question, botanist_context=botanist_context, limit=3)
        all_works: list[ResearchWork] = []
        provider_results = []
        source_record_ids: list[str] = []
        for variant in variants:
            result = await self.tool_gateway.execute(
                self.search_tool,
                context,
                ToolRequest(
                    payload={"query": variant, "limit": limit, "context": botanist_context or {}},
                    cache_key=f"research:europe-pmc:search:{normalize_research_query(variant)}:{limit}",
                    cache_ttl_seconds=86400 * 7,
                    stale_if_error_seconds=86400 * 30,
                    allow_stale_cache=True,
                    estimated_cost_usd=0.0,
                    contains_private_text=bool(botanist_context),
                ),
            )
            provider_results.append(result)
            source_ids = self._persist_sources(context.organization_id, result.provenance)
            source_record_ids.extend(source_ids)
            for raw in result.data.get("works", []):
                work = _work_from_dict(raw)
                work.source_record_ids = sorted(set(work.source_record_ids + source_ids))
                all_works.append(self.repository.upsert_research_work(work))
        return ScholarSearchResult(query_variants=variants, works=_dedupe_works(all_works), provider_results=provider_results, source_record_ids=sorted(set(source_record_ids)))

    async def fetch(self, context: ToolExecutionContext, external_id: str, *, doi: str | None = None, pmid: str | None = None, pmcid: str | None = None) -> ResearchWork | None:
        result = await self.tool_gateway.execute(
            self.fetch_tool,
            context,
            ToolRequest(
                payload={"external_id": external_id, "doi": doi, "pmid": pmid, "pmcid": pmcid},
                cache_key=f"research:europe-pmc:fetch:{external_id}:{doi}:{pmid}:{pmcid}",
                cache_ttl_seconds=86400 * 90,
                stale_if_error_seconds=86400 * 365,
                allow_stale_cache=True,
                estimated_cost_usd=0.0,
            ),
        )
        source_ids = self._persist_sources(context.organization_id, result.provenance)
        raw = result.data.get("work")
        if not raw or not raw.get("title"):
            return None
        work = _work_from_dict(raw)
        work.source_record_ids = sorted(set(work.source_record_ids + source_ids))
        return self.repository.upsert_research_work(work)

    async def build_context(
        self,
        context: ToolExecutionContext,
        question: str,
        *,
        user_plant_id: str | None = None,
        location_id: str | None = None,
    ) -> ScholarContext:
        botanist_context = {}
        if user_plant_id and self.botanist is not None:
            botanist_context = (await self.botanist.build_context(context, user_plant_id)).to_dict()
        if location_id and self.context_compiler is not None:
            botanist_context["environmental_context"] = (await self.context_compiler.build_environmental_context(context, location_id)).to_dict()
        search = await self.search(context, question, botanist_context=botanist_context or None)
        claims = [self.repository.create_research_claim(_claim_for_work(context.organization_id, question, work)) for work in search.works]
        claim_dicts = [asdict(claim) for claim in claims]
        contradictions = [claim for claim in claim_dicts if claim["evidence_direction"] == "contradictory"]
        return ScholarContext(
            research_question=question,
            works=[asdict(work) for work in search.works],
            claims=claim_dicts,
            evidence_quality=_overall_quality(claim_dicts),
            contradictions=contradictions,
            applicability=_overall_applicability(claim_dicts),
            provenance=sorted(set(search.source_record_ids + [source for work in search.works for source in work.source_record_ids])),
            work_ids=[work.id for work in search.works],
            model_run_count=0,
        )

    async def synthesize(
        self,
        context: ToolExecutionContext,
        question: str,
        *,
        user_plant_id: str | None = None,
        location_id: str | None = None,
        use_model: bool = True,
    ) -> EvidenceSynthesis:
        scholar_context = await self.build_context(context, question, user_plant_id=user_plant_id, location_id=location_id)
        model_run_ids: list[str] = []
        model_confidence = "not_model_generated"
        model_draft = _deterministic_synthesis(question, scholar_context)
        if use_model and self.model_gateway is not None and scholar_context.work_ids:
            prompt = build_scholar_prompt(question, scholar_context.to_dict())
            self.repository.upsert_prompt_harness(prompt.harness)
            response = await self.model_gateway.generate(
                context,
                self.default_model_provider_id,
                ModelRequest(
                    messages=prompt.messages,
                    prompt_id=prompt.prompt_id,
                    prompt_version=prompt.semantic_version,
                    prompt_hash=prompt.prompt_hash,
                    response_format="json",
                    max_output_tokens=1000,
                    metadata={"route": "scholar", "retrieved_work_count": len(scholar_context.work_ids)},
                    contains_private_text=True,
                    estimated_cost_usd=0.0,
                ),
            )
            if response.model_run_id:
                model_run_ids.append(response.model_run_id)
            if response.status == "success":
                draft = validate_synthesis_draft(response.content, allowed_work_ids=set(scholar_context.work_ids))
                model_draft.update(draft)
                model_confidence = draft.get("model_confidence") or "moderate"
        synthesis = EvidenceSynthesis(
            organization_id=context.organization_id,
            workspace_id=context.workspace_id,
            question=question,
            scope={"query": question, "work_count": len(scholar_context.work_ids), "no_results": not scholar_context.work_ids},
            supporting_claims=[claim for claim in scholar_context.claims if claim["evidence_direction"] == "supporting"],
            contradictory_claims=[claim for claim in scholar_context.claims if claim["evidence_direction"] == "contradictory"],
            uncertain_claims=[claim for claim in scholar_context.claims if claim["evidence_direction"] == "uncertain"],
            evidence_quality=model_draft.get("evidence_quality", scholar_context.evidence_quality),
            model_confidence=model_confidence,
            data_freshness="cached_or_recent_provider_metadata",
            uncertainty=model_draft.get("uncertainty", {"level": scholar_context.evidence_quality}),
            applicability=scholar_context.applicability,
            source_work_ids=scholar_context.work_ids,
            source_record_ids=scholar_context.provenance,
            model_run_ids=model_run_ids,
            export_payload={
                "question": question,
                "provider": "europe-pmc",
                "works": scholar_context.works,
                "claims": scholar_context.claims,
                "contradictions": scholar_context.contradictions,
                "model_run_ids": model_run_ids,
                "provenance": scholar_context.provenance,
            },
        )
        return self.repository.create_evidence_synthesis(synthesis)

    def create_collection(self, context: ToolExecutionContext, name: str, *, work_ids: list[str] | None = None, visibility: str = "private") -> ResearchCollection:
        return self.repository.create_research_collection(
            ResearchCollection(organization_id=context.organization_id, workspace_id=context.workspace_id, name=name, visibility=visibility, work_ids=work_ids or [])
        )

    def _persist_sources(self, organization_id: str, provenance_records: list[ProvenanceRecord]) -> list[str]:
        source_ids = []
        for provenance in provenance_records:
            source = SourceRecord(
                organization_id=organization_id,
                provider=provenance.provider,
                source_type="research",
                canonical_url=provenance.canonical_url,
                external_record_id=provenance.external_record_id,
                title=provenance.external_record_id or provenance.provider,
                authority=provenance.authority,
                retrieved_at=provenance.retrieved_at,
                observed_at=provenance.observed_at,
                valid_from=provenance.valid_at,
                license=provenance.license,
                attribution=provenance.attribution,
                content_hash=provenance.content_hash,
            )
            self.repository.create_source_record(source)
            source_ids.append(source.id)
        return source_ids


def _work_from_dict(raw: JsonDict) -> ResearchWork:
    fields = ResearchWork.__dataclass_fields__
    return ResearchWork(**{key: value for key, value in raw.items() if key in fields})


def _dedupe_works(works: list[ResearchWork]) -> list[ResearchWork]:
    seen: set[str] = set()
    deduped = []
    for work in works:
        key = work.doi or work.pmid or work.pmcid or json.dumps(work.provider_ids, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(work)
    return deduped


def _claim_for_work(organization_id: str, question: str, work: ResearchWork) -> ResearchClaim:
    text = " ".join([work.title, work.abstract or ""]).lower()
    direction = "uncertain"
    statement = f"{work.title} provides context but does not directly settle the question."
    if "retracted" in work.retracted_status:
        direction = "irrelevant"
        statement = f"{work.title} is retracted and should not support current guidance."
    elif "limited" in text or "insufficient" in text or "inconsistent" in text:
        direction = "contradictory"
        statement = f"{work.title} reports limitations or inconsistent evidence relevant to the question."
    elif "reported" in text or "finds" in text or "trial" in text:
        direction = "supporting"
        statement = f"{work.title} offers potentially supporting evidence, with context limits."
    limitations = []
    if work.retracted_status == "retracted":
        limitations.append("Retracted work must not be used as normal supporting evidence.")
    if "greenhouse" in text:
        limitations.append("Greenhouse or protected-environment result may not apply to outdoor field/container conditions.")
    if work.study_type in {"controlled experiment", "laboratory study"}:
        limitations.append("Controlled conditions may not generalize across cultivar, climate, soil, or growing system.")
    applicability = {
        "species_match": "partial" if "tomato" in text or "solanum lycopersicum" in text else "unknown",
        "cultivar_match": "unknown",
        "growing_system_match": "mismatch" if "greenhouse" in text else "unknown",
        "climate_match": "unknown",
        "geographic_match": "unknown",
        "soil_match": "unknown",
        "development_stage_match": "unknown",
        "intervention_match": "partial" if any(term in text for term in question.lower().split()) else "unknown",
    }
    return ResearchClaim(
        organization_id=organization_id,
        statement=statement,
        subject=question,
        evidence_direction=direction,
        evidence_quality=_quality_for(work, direction),
        evidence_grade=_grade_for(work, direction),
        model_confidence="not_model_generated",
        data_freshness="provider_metadata",
        source_work_ids=[work.id],
        source_record_ids=work.source_record_ids,
        limitations=limitations,
        study_type=work.study_type,
        applicability=applicability,
    )


def _quality_for(work: ResearchWork, direction: str) -> str:
    if work.retracted_status == "retracted":
        return "insufficient"
    if direction == "contradictory":
        return "mixed"
    if work.study_type in {"meta-analysis", "systematic review"}:
        return "strong"
    if work.study_type in {"review", "field trial", "controlled experiment"}:
        return "moderate"
    return "limited"


def _grade_for(work: ResearchWork, direction: str) -> str:
    if work.retracted_status == "retracted" or direction == "irrelevant":
        return "E"
    if work.study_type in {"meta-analysis", "systematic review"}:
        return "B"
    if work.study_type in {"review", "field trial", "controlled experiment"}:
        return "C"
    return "E"


def _overall_quality(claims: list[JsonDict]) -> str:
    if not claims:
        return "insufficient"
    directions = {claim["evidence_direction"] for claim in claims}
    if "contradictory" in directions and "supporting" in directions:
        return "mixed"
    if "supporting" in directions:
        return "moderate"
    if directions == {"irrelevant"}:
        return "insufficient"
    return "limited"


def _overall_applicability(claims: list[JsonDict]) -> JsonDict:
    mismatches = [claim for claim in claims if claim.get("applicability", {}).get("growing_system_match") == "mismatch"]
    return {
        "summary": "Some evidence may be only partially applicable to the user's plant/location.",
        "greenhouse_or_system_mismatch_count": len(mismatches),
        "dimensions": [
            "species_match",
            "cultivar_match",
            "growing_system_match",
            "climate_match",
            "geographic_match",
            "soil_match",
            "development_stage_match",
            "intervention_match",
        ],
    }


def _deterministic_synthesis(question: str, scholar_context: ScholarContext) -> JsonDict:
    if not scholar_context.work_ids:
        return {
            "question": question,
            "summary": "GAIA did not retrieve current provider-backed research for this question.",
            "evidence_quality": "insufficient",
            "uncertainty": {"level": "insufficient", "reasons": ["No retrieved works were available."]},
        }
    return {
        "question": question,
        "summary": "Retrieved evidence is source-backed and should be interpreted with its study limitations.",
        "evidence_quality": scholar_context.evidence_quality,
        "uncertainty": {"level": scholar_context.evidence_quality, "reasons": ["Evidence quality and applicability vary by study type and context."]},
    }

