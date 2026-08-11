from __future__ import annotations

from dataclasses import asdict

from packages.persistence import GaiaRepository
from packages.research import ScholarService
from packages.tools import ToolExecutionContext


async def get_research_search(
    scholar: ScholarService,
    context: ToolExecutionContext,
    *,
    query: str,
    limit: int = 10,
) -> dict:
    result = await scholar.search(context, query, limit=limit)
    return {
        "query_variants": result.query_variants,
        "works": [asdict(work) for work in result.works],
        "source_record_ids": result.source_record_ids,
        "provider_statuses": [provider_result.status for provider_result in result.provider_results],
    }


async def get_research_work(repository: GaiaRepository, work_id: str) -> dict | None:
    return repository.get_research_work(work_id)


async def post_research_synthesize(
    scholar: ScholarService,
    context: ToolExecutionContext,
    *,
    question: str,
    user_plant_id: str | None = None,
    location_id: str | None = None,
    use_model: bool = True,
) -> dict:
    synthesis = await scholar.synthesize(
        context,
        question,
        user_plant_id=user_plant_id,
        location_id=location_id,
        use_model=use_model,
    )
    return asdict(synthesis)


async def get_research_synthesis(repository: GaiaRepository, context: ToolExecutionContext, synthesis_id: str) -> dict | None:
    return repository.get_evidence_synthesis(context.organization_id, synthesis_id)

