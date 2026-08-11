from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime

from packages.domain import EnvironmentalSnapshot, Location, SourceRecord
from packages.environment.calculations import moon_phase, photoperiod_hours, sunrise_sunset_utc
from packages.environment.tools import NASAPowerClimateTool, NWSForecastTool, USDASoilSurveyTool, USGSWaterSitesTool
from packages.persistence import GaiaRepository
from packages.provenance import ProvenanceRecord
from packages.tools import ToolExecutionContext, ToolGateway, ToolRequest, ToolResult


@dataclass(frozen=True, slots=True)
class TerraResult:
    snapshot: EnvironmentalSnapshot
    provider_results: dict[str, ToolResult]


class TerraService:
    def __init__(
        self,
        repository: GaiaRepository,
        tool_gateway: ToolGateway,
        nws_tool: NWSForecastTool,
        nasa_power_tool: NASAPowerClimateTool,
        soil_tool: USDASoilSurveyTool,
        water_tool: USGSWaterSitesTool,
    ) -> None:
        self.repository = repository
        self.tool_gateway = tool_gateway
        self.nws_tool = nws_tool
        self.nasa_power_tool = nasa_power_tool
        self.soil_tool = soil_tool
        self.water_tool = water_tool

    async def build_environmental_snapshot(
        self,
        location: Location,
        context: ToolExecutionContext,
        *,
        timestamp: str | None = None,
        persist: bool = True,
    ) -> TerraResult:
        if location.latitude is None or location.longitude is None:
            raise ValueError("Terra requires latitude and longitude")

        payload = {"latitude": location.latitude, "longitude": location.longitude, "timestamp": timestamp}
        requests = [
            self.tool_gateway.execute(self.nws_tool, context, ToolRequest(payload=payload, cache_key=f"nws:{location.id}", cache_ttl_seconds=900, stale_if_error_seconds=900, allow_stale_cache=True, contains_exact_location=True)),
            self.tool_gateway.execute(self.nasa_power_tool, context, ToolRequest(payload=payload, cache_key=f"nasa:{location.id}", cache_ttl_seconds=86400 * 30, stale_if_error_seconds=86400 * 365, allow_stale_cache=True, contains_exact_location=True)),
            self.tool_gateway.execute(self.soil_tool, context, ToolRequest(payload=payload, cache_key=f"soil:{location.id}", cache_ttl_seconds=86400 * 365, stale_if_error_seconds=86400 * 365, allow_stale_cache=True, contains_exact_location=True)),
            self.tool_gateway.execute(self.water_tool, context, ToolRequest(payload=payload, cache_key=f"water-sites:{location.id}", cache_ttl_seconds=86400, stale_if_error_seconds=86400, allow_stale_cache=True, contains_exact_location=True)),
        ]
        nws, nasa, soil, water = await asyncio.gather(*requests, return_exceptions=True)
        provider_results = {
            "nws": self._coerce_result(nws),
            "nasa_power": self._coerce_result(nasa),
            "soil": self._coerce_result(soil),
            "water": self._coerce_result(water),
        }

        source_record_ids = []
        for result in provider_results.values():
            for provenance in result.provenance:
                source_record_ids.append(self._persist_source_record(location.organization_id, provenance))

        value_date = datetime.now(UTC).date()
        if timestamp:
            value_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).date()
        sunrise, sunset = sunrise_sunset_utc(location.latitude, location.longitude, value_date)
        photoperiod = photoperiod_hours(location.latitude, location.longitude, value_date)

        nws_data = provider_results["nws"].data
        nasa_data = provider_results["nasa_power"].data
        soil_data = provider_results["soil"].data
        water_data = provider_results["water"].data

        snapshot = EnvironmentalSnapshot(
            organization_id=location.organization_id,
            location_id=location.id,
            observed_or_valid_at=nws_data.get("valid_at") or timestamp or datetime.now(UTC).isoformat(),
            retrieved_at=nws_data.get("retrieved_at") or datetime.now(UTC).isoformat(),
            temperature=nws_data.get("temperature") or nasa_data.get("temperature_history", {}),
            humidity=nws_data.get("humidity", {}),
            precipitation=nws_data.get("precipitation_probability") or nasa_data.get("precipitation_context", {}),
            wind=nws_data.get("wind", {}),
            forecast=nws_data,
            solar_radiation=nasa_data.get("solar_radiation", {}),
            photoperiod={"value": photoperiod, "unit": "hours", "sunrise_utc": sunrise.isoformat(), "sunset_utc": sunset.isoformat(), "evidence_type": "DERIVED"},
            solar_context={"sunrise_utc": sunrise.isoformat(), "sunset_utc": sunset.isoformat(), "evidence_type": "DERIVED"},
            soil_context=soil_data,
            soil_moisture_context={"status": "UNAVAILABLE", "semantic_note": "No direct root-zone sensor soil moisture is present.", "evidence_type": "MODELED"},
            drought_context={"status": "UNAVAILABLE", "evidence_type": "MODELED"},
            water_context=water_data,
            season_context={"date": value_date.isoformat(), "evidence_type": "DERIVED"},
            astronomical_context={**moon_phase(value_date), "experimental": True},
            provider_statuses={key: result.status.upper() for key, result in provider_results.items()},
            source_record_ids=source_record_ids,
        )
        if persist:
            self.repository.create_environmental_snapshot(snapshot)
        return TerraResult(snapshot=snapshot, provider_results=provider_results)

    def _coerce_result(self, result: ToolResult | BaseException) -> ToolResult:
        if isinstance(result, ToolResult):
            return result
        return ToolResult.failed(f"provider_exception:{result.__class__.__name__}")

    def _persist_source_record(self, organization_id: str, provenance: ProvenanceRecord) -> str:
        source_record = SourceRecord(
            organization_id=organization_id,
            provider=provenance.provider,
            source_type="environmental",
            canonical_url=provenance.canonical_url,
            external_record_id=provenance.external_record_id,
            title=provenance.authority or provenance.provider,
            authority=provenance.authority,
            retrieved_at=provenance.retrieved_at,
            observed_at=provenance.observed_at,
            valid_from=provenance.valid_at,
            license=provenance.license,
            attribution=provenance.attribution,
            content_hash=provenance.content_hash,
        )
        self.repository.create_source_record(source_record)
        return source_record.id
