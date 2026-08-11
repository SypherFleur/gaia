from __future__ import annotations

from packages.botany.providers import GermplasmProvider, TaxonomyProvider
from packages.tools import GaiaTool, ToolExecutionContext, ToolRequest, ToolResult, ToolRisk


class GBIFTaxonomyTool(GaiaTool):
    id = "botany.gbif.taxonomy.resolve"
    version = "0.1.0"
    risk_class = ToolRisk.READ
    required_permissions = ("tool.read",)
    provider_id = "gbif"

    def __init__(self, provider: TaxonomyProvider) -> None:
        self.provider = provider

    async def execute(self, context: ToolExecutionContext, request: ToolRequest) -> ToolResult:
        resolution = await self.provider.resolve_taxon(str(request.payload.get("query", "")))
        return ToolResult(
            data={
                "status": resolution.status,
                "query": resolution.query,
                "canonical_taxon_id": resolution.canonical_taxon_id,
                "accepted_scientific_name": resolution.accepted_scientific_name,
                "matched_name": resolution.matched_name,
                "match_type": resolution.match_type,
                "rank": resolution.rank,
                "kingdom": resolution.kingdom,
                "family": resolution.family,
                "genus": resolution.genus,
                "species": resolution.species,
                "subspecies": resolution.subspecies,
                "common_names": resolution.common_names,
                "synonyms": resolution.synonyms,
                "alternatives": resolution.alternatives,
                "external_source_ids": resolution.external_source_ids,
                "semantic_note": "GBIF occurrence evidence indicates observed presence, not cultivation suitability.",
            },
            provenance=resolution.provenance,
            warnings=resolution.warnings,
            status=resolution.status,
        )


class GenesysGermplasmTool(GaiaTool):
    id = "botany.genesys.germplasm.search"
    version = "0.1.0"
    risk_class = ToolRisk.READ
    required_permissions = ("tool.read",)
    provider_id = "genesys-pgr"

    def __init__(self, provider: GermplasmProvider) -> None:
        self.provider = provider

    async def execute(self, context: ToolExecutionContext, request: ToolRequest) -> ToolResult:
        result = await self.provider.search_accessions(
            str(request.payload.get("query", "")),
            limit=int(request.payload.get("limit", 10)),
        )
        return ToolResult(
            data={
                "status": result.status,
                "query": result.query,
                "accessions": result.accessions,
                "semantic_note": "Genesys discovery does not prove legal movement, availability, price, import eligibility, or agronomic suitability.",
            },
            provenance=result.provenance,
            warnings=result.warnings,
            status=result.status,
        )
