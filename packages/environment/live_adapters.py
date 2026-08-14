from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import json
import urllib.error
import urllib.parse
import urllib.request

from packages.environment.providers import EnvironmentalProviderResult
from packages.provenance import ProvenanceRecord, content_hash


class NWSApiAdapter:
    provider_id = "nws"
    base_url = "https://api.weather.gov"

    def __init__(self, user_agent: str, timeout_seconds: int = 10) -> None:
        if not user_agent:
            raise ValueError("NWS requires a configured User-Agent")
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds

    async def forecast(self, latitude: float, longitude: float, at_time: str | None = None) -> EnvironmentalProviderResult:
        try:
            point = self._get_json(f"{self.base_url}/points/{latitude},{longitude}")
            forecast_url = point["properties"]["forecast"]
            forecast = self._get_json(forecast_url)
        except (KeyError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return EnvironmentalProviderResult(status="PROVIDER_ERROR", warnings=[f"nws_error:{exc.__class__.__name__}"])
        return self.normalize_forecast(forecast, forecast_url)

    def normalize_forecast(self, forecast: dict, canonical_url: str) -> EnvironmentalProviderResult:
        period = (forecast.get("properties", {}).get("periods") or [{}])[0]
        data = {
            "temperature": {
                "value": period.get("temperature"),
                "unit": period.get("temperatureUnit"),
                "original_value": period.get("temperature"),
                "original_unit": period.get("temperatureUnit"),
                "evidence_type": "FORECAST",
            },
            "precipitation_probability": {
                "value": (period.get("probabilityOfPrecipitation") or {}).get("value"),
                "unit": "%",
                "evidence_type": "FORECAST",
            },
            "humidity": {"value": (period.get("relativeHumidity") or {}).get("value"), "unit": "%", "evidence_type": "FORECAST"},
            "wind": {"speed": period.get("windSpeed"), "direction": period.get("windDirection"), "evidence_type": "FORECAST"},
            "valid_at": period.get("startTime"),
            "retrieved_at": forecast.get("properties", {}).get("generatedAt"),
            "alerts": [],
        }
        return EnvironmentalProviderResult(
            status="AVAILABLE",
            data=data,
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    canonical_url=canonical_url,
                    authority="NOAA/National Weather Service",
                    valid_at=data["valid_at"],
                    geographic_scope="NWS grid forecast",
                    license="public-domain-us-government",
                    attribution="NOAA/NWS",
                    content_hash=content_hash(forecast),
                )
            ],
        )

    def _get_json(self, url: str) -> dict:
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent, "Accept": "application/geo+json"})
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))


class NASAPowerApiAdapter:
    provider_id = "nasa-power"
    base_url = "https://power.larc.nasa.gov/api/temporal/daily/point"

    def __init__(self, base_url: str | None = None, timeout_seconds: int = 15) -> None:
        if base_url:
            base = base_url.rstrip("/")
            self.base_url = base if base.endswith("/point") else f"{base}/api/temporal/daily/point"
        self.timeout_seconds = timeout_seconds

    async def climate_context(self, latitude: float, longitude: float, at_time: str | None = None) -> EnvironmentalProviderResult:
        power_date = _power_date(at_time)
        params = {
            "parameters": "T2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN",
            "community": "AG",
            "longitude": f"{longitude:.4f}",
            "latitude": f"{latitude:.4f}",
            "start": power_date,
            "end": power_date,
            "format": "JSON",
        }
        url = self.base_url + "?" + urllib.parse.urlencode(params)
        try:
            payload = await asyncio.to_thread(self._get_json, url)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return EnvironmentalProviderResult(status="PROVIDER_ERROR", warnings=[f"nasa_power_error:{exc.__class__.__name__}"])
        return self.normalize_daily_response(payload, url)

    def normalize_daily_response(self, payload: dict, canonical_url: str) -> EnvironmentalProviderResult:
        properties = payload.get("properties", {})
        parameters = properties.get("parameter", {})
        data = {
            "temperature_history": {"value": _first_value(parameters.get("T2M", {})), "unit": "C", "parameter": "T2M", "evidence_type": "MODELED"},
            "precipitation_context": {"value": _first_value(parameters.get("PRECTOTCORR", {})), "unit": "mm/day", "parameter": "PRECTOTCORR", "evidence_type": "MODELED"},
            "solar_radiation": {"value": _first_value(parameters.get("ALLSKY_SFC_SW_DWN", {})), "unit": "MJ/m^2/day", "parameter": "ALLSKY_SFC_SW_DWN", "evidence_type": "MODELED"},
            "temporal_resolution": "daily",
            "semantic_note": "NASA POWER is regional/model-derived environmental data, not an exact on-site sensor reading.",
        }
        return EnvironmentalProviderResult(
            status="AVAILABLE",
            data=data,
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    canonical_url=canonical_url,
                    authority="NASA POWER",
                    geographic_scope="regional modeled grid",
                    license="unknown",
                    attribution="NASA POWER",
                    content_hash=content_hash(payload),
                )
            ],
        )

    def _get_json(self, url: str) -> dict:
        request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "GAIA Local Alpha/0.1"})
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))


class USDASoilDataAccessAdapter:
    provider_id = "usda-nrcs-sda"

    def normalize_mapunit_response(self, payload: dict, canonical_url: str) -> EnvironmentalProviderResult:
        if not payload.get("Table"):
            return EnvironmentalProviderResult(
                status="UNAVAILABLE",
                data={"semantic_note": "No soil survey result available; GAIA did not infer a soil type."},
                provenance=[
                    ProvenanceRecord(
                        provider=self.provider_id,
                        canonical_url=canonical_url,
                        authority="USDA NRCS Soil Data Access",
                        license="unknown",
                        attribution="USDA NRCS",
                        content_hash=content_hash(payload),
                    )
                ],
            )
        row = payload["Table"][0]
        data = {
            "map_unit": row.get("muname"),
            "component": row.get("compname"),
            "drainage_class": row.get("drainagecl"),
            "hydrologic_soil_group": row.get("hydgrp"),
            "texture": {"value": row.get("texture"), "evidence_type": "SURVEY"},
            "ph": {"value": row.get("ph1to1h2o_r"), "evidence_type": "SURVEY"},
            "semantic_note": "SSURGO is soil survey context, not live soil moisture.",
        }
        return EnvironmentalProviderResult(
            status="AVAILABLE",
            data=data,
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    canonical_url=canonical_url,
                    authority="USDA NRCS Soil Data Access",
                    geographic_scope="soil survey map unit",
                    license="unknown",
                    attribution="USDA NRCS",
                    content_hash=content_hash(payload),
                )
            ],
        )


def _first_value(values: dict) -> float | None:
    if not values:
        return None
    return next(iter(values.values()))


def _power_date(at_time: str | None) -> str:
    if at_time:
        normalized = at_time[:10].replace("-", "")
        if len(normalized) == 8 and normalized.isdigit():
            return normalized
    return (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y%m%d")
