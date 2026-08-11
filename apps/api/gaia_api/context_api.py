from __future__ import annotations

from dataclasses import asdict

from packages.context.compiler import ContextCompiler
from packages.tools import ToolExecutionContext


async def post_context_geography(
    compiler: ContextCompiler,
    context: ToolExecutionContext,
    location_id: str,
    timestamp: str | None = None,
) -> dict:
    bundle = await compiler.build_geography_context(context, location_id, timestamp=timestamp)
    geo = bundle.geo_context
    return {
        "geo_context": {
            "id": geo.id,
            "country": geo.country,
            "country_code": geo.country_code,
            "state_or_region": geo.state_or_region,
            "state_code": geo.state_code,
            "county_or_district": geo.county_or_district,
            "county_fips": geo.county_fips,
            "timezone": geo.timezone,
            "hardiness_zone": geo.hardiness_zone,
            "watershed": geo.watershed,
            "source_record_ids": geo.source_record_ids,
        },
        "display_coordinate": asdict(bundle.atlas.display_coordinate),
        "provider_statuses": bundle.atlas.provider_statuses,
    }


async def post_context_environment(
    compiler: ContextCompiler,
    context: ToolExecutionContext,
    location_id: str,
    timestamp: str | None = None,
) -> dict:
    bundle = await compiler.build_environmental_context(context, location_id, timestamp=timestamp)
    snapshot = bundle.environmental_snapshot
    return {
        "environmental_snapshot": {
            "id": snapshot.id,
            "location_id": snapshot.location_id,
            "temperature": snapshot.temperature,
            "forecast": snapshot.forecast,
            "solar_radiation": snapshot.solar_radiation,
            "photoperiod": snapshot.photoperiod,
            "soil_context": snapshot.soil_context,
            "soil_moisture_context": snapshot.soil_moisture_context,
            "water_context": snapshot.water_context,
            "provider_statuses": snapshot.provider_statuses,
            "source_record_ids": snapshot.source_record_ids,
        },
        "model_run_count": bundle.model_run_count,
    }
