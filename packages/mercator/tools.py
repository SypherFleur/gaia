from __future__ import annotations

from dataclasses import dataclass

from packages.mercator.providers import EconomicDataProvider, EconomicRequest
from packages.tools import ToolExecutionContext, ToolRequest, ToolResult, ToolRisk


def _request(payload: dict) -> EconomicRequest:
    return EconomicRequest(
        commodity=str(payload["commodity"]),
        geography=payload.get("geography", {}),
        crop_or_taxon=payload.get("crop_or_taxon", {}),
        periods=payload.get("periods", []),
        market_region=payload.get("market_region"),
    )


@dataclass(slots=True)
class NASSProductionTool:
    provider: EconomicDataProvider
    id: str = "mercator.nass.production"
    version: str = "0.1.0"
    risk_class: ToolRisk = ToolRisk.READ
    required_permissions: tuple[str, ...] = ("tool.read",)
    provider_id: str = "usda-nass"

    async def execute(self, context: ToolExecutionContext, request: ToolRequest) -> ToolResult:
        result = await self.provider.production(_request(request.payload))
        return ToolResult(data=result.data, provenance=result.provenance, warnings=result.warnings, status=result.status.lower(), freshness=result.freshness)


@dataclass(slots=True)
class NASSRegionalContextTool:
    provider: EconomicDataProvider
    id: str = "mercator.nass.region"
    version: str = "0.1.0"
    risk_class: ToolRisk = ToolRisk.READ
    required_permissions: tuple[str, ...] = ("tool.read",)
    provider_id: str = "usda-nass"

    async def execute(self, context: ToolExecutionContext, request: ToolRequest) -> ToolResult:
        result = await self.provider.regional_context(_request(request.payload))
        return ToolResult(data=result.data, provenance=result.provenance, warnings=result.warnings, status=result.status.lower(), freshness=result.freshness)


@dataclass(slots=True)
class AMSMarketReportTool:
    provider: EconomicDataProvider
    id: str = "mercator.ams.market_reports"
    version: str = "0.1.0"
    risk_class: ToolRisk = ToolRisk.READ
    required_permissions: tuple[str, ...] = ("tool.read",)
    provider_id: str = "usda-ams"

    async def execute(self, context: ToolExecutionContext, request: ToolRequest) -> ToolResult:
        result = await self.provider.market_reports(_request(request.payload))
        return ToolResult(data=result.data, provenance=result.provenance, warnings=result.warnings, status=result.status.lower(), freshness=result.freshness)


@dataclass(slots=True)
class AMSSupplyChainTool:
    provider: EconomicDataProvider
    id: str = "mercator.ams.supply_chain"
    version: str = "0.1.0"
    risk_class: ToolRisk = ToolRisk.READ
    required_permissions: tuple[str, ...] = ("tool.read",)
    provider_id: str = "usda-ams"

    async def execute(self, context: ToolExecutionContext, request: ToolRequest) -> ToolResult:
        result = await self.provider.supply_chain(_request(request.payload))
        return ToolResult(data=result.data, provenance=result.provenance, warnings=result.warnings, status=result.status.lower(), freshness=result.freshness)

