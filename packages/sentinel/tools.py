from __future__ import annotations

from dataclasses import asdict

from packages.sentinel.providers import RegulationProvider, RegulationRequest
from packages.tools import GaiaTool, ToolExecutionContext, ToolRequest, ToolResult, ToolRisk


class RegulationMovementRulesTool(GaiaTool):
    id = "sentinel.regulation.movement_rules"
    version = "0.1.0"
    risk_class = ToolRisk.READ
    required_permissions = ("regulation.read",)

    def __init__(self, provider: RegulationProvider, provider_id: str) -> None:
        self.provider = provider
        self.provider_id = provider_id

    async def execute(self, context: ToolExecutionContext, request: ToolRequest) -> ToolResult:
        response = await self.provider.movement_rules(_request_from_payload(request.payload))
        return ToolResult(
            data={
                "provider_id": response.provider_id,
                "status": response.status,
                "rules": [asdict(rule) for rule in response.rules],
                "zones": [asdict(zone) for zone in response.zones],
                "alerts": response.alerts,
                "reporting_requirements": response.reporting_requirements,
                "freshness": response.freshness,
            },
            provenance=response.provenance,
            warnings=response.warnings,
            status=response.status,
        )


class RegulationPestAlertsTool(RegulationMovementRulesTool):
    id = "sentinel.regulation.pest_alerts"

    async def execute(self, context: ToolExecutionContext, request: ToolRequest) -> ToolResult:
        response = await self.provider.pest_alerts(_request_from_payload(request.payload))
        return ToolResult(
            data={
                "provider_id": response.provider_id,
                "status": response.status,
                "alerts": response.alerts,
                "reporting_requirements": response.reporting_requirements,
                "freshness": response.freshness,
            },
            provenance=response.provenance,
            warnings=response.warnings,
            status=response.status,
        )


def _request_from_payload(payload: dict) -> RegulationRequest:
    return RegulationRequest(
        jurisdiction_pack=str(payload.get("jurisdiction_pack", "")),
        origin=payload.get("origin", {}),
        destination=payload.get("destination", {}),
        species=payload.get("species"),
        plant_part=str(payload.get("plant_part", "unknown")),
        live_plant=bool(payload.get("live_plant", False)),
        soil_attached=bool(payload.get("soil_attached", False)),
        planned_date=payload.get("planned_date"),
        metadata=payload.get("metadata", {}),
    )

