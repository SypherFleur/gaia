from __future__ import annotations

from dataclasses import dataclass

from packages.geospatial.providers import AdminResolution, GeographyProvider, ProviderStatus
from packages.tools import ToolExecutionContext, ToolRequest, ToolResult, ToolRisk


@dataclass(slots=True)
class CensusGeographyTool:
    provider: GeographyProvider
    id: str = "atlas.census.resolve_admin"
    version: str = "0.1.0"
    risk_class: ToolRisk = ToolRisk.READ
    required_permissions: tuple[str, ...] = ("tool.read",)
    provider_id: str = "census-geocoder"

    async def execute(self, context: ToolExecutionContext, request: ToolRequest) -> ToolResult:
        resolution = await self.provider.resolve_admin(
            request.payload["latitude"],
            request.payload["longitude"],
            request.payload.get("timestamp"),
        )
        return ToolResult(
            data=admin_resolution_to_data(resolution),
            provenance=resolution.provenance,
            status=resolution.status.status.lower(),
        )


def admin_resolution_to_data(resolution: AdminResolution) -> dict:
    return {
        "status": resolution.status.status,
        "reason": resolution.status.reason,
        "country": resolution.country,
        "country_code": resolution.country_code,
        "state_or_region": resolution.state_or_region,
        "state_code": resolution.state_code,
        "county_or_district": resolution.county_or_district,
        "county_fips": resolution.county_fips,
        "timezone": resolution.timezone,
        "elevation_m": resolution.elevation_m,
    }


def admin_resolution_from_tool_result(result: ToolResult) -> AdminResolution:
    data = result.data or {}
    if result.status in {"denied", "failed", "fail_closed"} or not data:
        return AdminResolution(status=ProviderStatus("UNAVAILABLE", result.denial_reason or result.status))
    return AdminResolution(
        status=ProviderStatus(str(data.get("status") or "UNAVAILABLE"), data.get("reason")),
        country=data.get("country"),
        country_code=data.get("country_code"),
        state_or_region=data.get("state_or_region"),
        state_code=data.get("state_code"),
        county_or_district=data.get("county_or_district"),
        county_fips=data.get("county_fips"),
        timezone=data.get("timezone"),
        elevation_m=data.get("elevation_m"),
        provenance=result.provenance,
    )
