from __future__ import annotations

from dataclasses import asdict

from packages.research.providers import ResearchFetchRequest, ResearchProvider, ResearchSearchRequest
from packages.tools import GaiaTool, ToolExecutionContext, ToolRequest, ToolResult, ToolRisk


class EuropePMCSearchTool(GaiaTool):
    id = "scholar.europe_pmc.search"
    version = "0.1.0"
    risk_class = ToolRisk.READ
    required_permissions = ("research.read",)
    provider_id = "europe-pmc"

    def __init__(self, provider: ResearchProvider) -> None:
        self.provider = provider

    async def execute(self, context: ToolExecutionContext, request: ToolRequest) -> ToolResult:
        response = await self.provider.search(
            ResearchSearchRequest(query=str(request.payload.get("query", "")), limit=int(request.payload.get("limit", 10)), context=request.payload.get("context", {}))
        )
        return ToolResult(
            data={
                "provider_id": response.provider_id,
                "query": response.query,
                "works": [asdict(work) for work in response.works],
                "status": response.status,
            },
            provenance=response.provenance,
            warnings=response.warnings,
            status=response.status,
        )


class EuropePMCFetchTool(GaiaTool):
    id = "scholar.europe_pmc.fetch"
    version = "0.1.0"
    risk_class = ToolRisk.READ
    required_permissions = ("research.read",)
    provider_id = "europe-pmc"

    def __init__(self, provider: ResearchProvider) -> None:
        self.provider = provider

    async def execute(self, context: ToolExecutionContext, request: ToolRequest) -> ToolResult:
        document = await self.provider.fetch(
            ResearchFetchRequest(
                provider_id="europe-pmc",
                external_id=str(request.payload.get("external_id", "")),
                source=request.payload.get("source"),
                doi=request.payload.get("doi"),
                pmid=request.payload.get("pmid"),
                pmcid=request.payload.get("pmcid"),
            )
        )
        return ToolResult(
            data={"work": asdict(document.work), "status": document.status, "raw_text_available": document.raw_text is not None},
            provenance=document.provenance,
            warnings=document.warnings,
            status=document.status,
        )

