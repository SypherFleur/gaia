from __future__ import annotations

from dataclasses import dataclass

from packages.environment.providers import ClimateProvider, SoilSurveyProvider, WaterProvider, WeatherProvider
from packages.tools import ToolExecutionContext, ToolRequest, ToolResult, ToolRisk


@dataclass(slots=True)
class NWSForecastTool:
    provider: WeatherProvider
    id: str = "terra.nws.forecast"
    version: str = "0.1.0"
    risk_class: ToolRisk = ToolRisk.READ
    required_permissions: tuple[str, ...] = ("tool.read",)
    provider_id: str = "nws"

    async def execute(self, context: ToolExecutionContext, request: ToolRequest) -> ToolResult:
        result = await self.provider.forecast(request.payload["latitude"], request.payload["longitude"], request.payload.get("timestamp"))
        return ToolResult(data=result.data, provenance=result.provenance, warnings=result.warnings, status=result.status.lower())


@dataclass(slots=True)
class NASAPowerClimateTool:
    provider: ClimateProvider
    id: str = "terra.nasa_power.climate"
    version: str = "0.1.0"
    risk_class: ToolRisk = ToolRisk.READ
    required_permissions: tuple[str, ...] = ("tool.read",)
    provider_id: str = "nasa-power"

    async def execute(self, context: ToolExecutionContext, request: ToolRequest) -> ToolResult:
        result = await self.provider.climate_context(request.payload["latitude"], request.payload["longitude"], request.payload.get("timestamp"))
        return ToolResult(data=result.data, provenance=result.provenance, warnings=result.warnings, status=result.status.lower())


@dataclass(slots=True)
class USDASoilSurveyTool:
    provider: SoilSurveyProvider
    id: str = "terra.usda_soil.survey"
    version: str = "0.1.0"
    risk_class: ToolRisk = ToolRisk.READ
    required_permissions: tuple[str, ...] = ("tool.read",)
    provider_id: str = "usda-nrcs-sda"

    async def execute(self, context: ToolExecutionContext, request: ToolRequest) -> ToolResult:
        result = await self.provider.soil_context(request.payload["latitude"], request.payload["longitude"], request.payload.get("timestamp"))
        return ToolResult(data=result.data, provenance=result.provenance, warnings=result.warnings, status=result.status.lower())


@dataclass(slots=True)
class USGSWaterSitesTool:
    provider: WaterProvider
    id: str = "terra.usgs_water.nearby_sites"
    version: str = "0.1.0"
    risk_class: ToolRisk = ToolRisk.READ
    required_permissions: tuple[str, ...] = ("tool.read",)
    provider_id: str = "usgs-water"

    async def execute(self, context: ToolExecutionContext, request: ToolRequest) -> ToolResult:
        result = await self.provider.nearby_sites(request.payload["latitude"], request.payload["longitude"])
        return ToolResult(data=result.data, provenance=result.provenance, warnings=result.warnings, status=result.status.lower())

