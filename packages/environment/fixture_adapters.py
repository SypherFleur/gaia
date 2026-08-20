from __future__ import annotations

from packages.environment.providers import EnvironmentalProviderResult
from packages.provenance import ProvenanceRecord, content_hash


class FixtureNWSProvider:
    provider_id = "nws"

    async def forecast(self, latitude: float, longitude: float, at_time: str | None = None) -> EnvironmentalProviderResult:
        data = {
            "temperature": {"value": 18.3, "unit": "C", "original_value": 65, "original_unit": "F", "evidence_type": "FORECAST"},
            "precipitation_probability": {"value": 20, "unit": "%", "evidence_type": "FORECAST"},
            "humidity": {"value": None, "unit": "%", "evidence_type": "FORECAST"},
            "wind": {"speed": 8, "unit": "mph", "direction": "SE", "evidence_type": "FORECAST"},
            "valid_at": "2026-08-11T21:00:00-05:00",
            "retrieved_at": "2026-08-11T12:00:00Z",
            "alerts": [],
        }
        return EnvironmentalProviderResult(
            status="AVAILABLE",
            data=data,
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    external_record_id="fixture-gridpoint-ewx-155-90",
                    canonical_url="fixture://nws/gridpoints/EWX/155,90/forecast",
                    authority="NOAA/National Weather Service",
                    observed_at=None,
                    valid_at=data["valid_at"],
                    geographic_scope="NWS gridpoint fixture",
                    license="public-domain-us-government",
                    attribution="NOAA/NWS",
                    content_hash=content_hash(data),
                )
            ],
        )


class FailingNWSProvider(FixtureNWSProvider):
    async def forecast(self, latitude: float, longitude: float, at_time: str | None = None) -> EnvironmentalProviderResult:
        return EnvironmentalProviderResult(status="PROVIDER_ERROR", warnings=["fixture_nws_failure"])


class FixtureNASAPowerProvider:
    provider_id = "nasa-power"

    async def climate_context(self, latitude: float, longitude: float, at_time: str | None = None) -> EnvironmentalProviderResult:
        data = {
            "temperature_history": {"value": 29.1, "unit": "C", "parameter": "T2M", "evidence_type": "MODELED"},
            "precipitation_context": {"value": 2.1, "unit": "mm/day", "parameter": "PRECTOTCORR", "evidence_type": "MODELED"},
            "solar_radiation": {"value": 23.4, "unit": "MJ/m^2/day", "parameter": "ALLSKY_SFC_SW_DWN", "evidence_type": "MODELED"},
            "observation_date": "2026-08-13",
            "temporal_resolution": "daily",
            "semantic_note": "NASA POWER is regional/model-derived environmental data, not an exact on-site sensor reading.",
        }
        return EnvironmentalProviderResult(
            status="AVAILABLE",
            data=data,
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    external_record_id="fixture-power-daily",
                    canonical_url="fixture://nasa-power/daily",
                    authority="NASA POWER",
                    geographic_scope="regional modeled grid fixture",
                    license="unknown",
                    attribution="NASA POWER",
                    content_hash=content_hash(data),
                )
            ],
        )


class FixtureUSDASoilProvider:
    provider_id = "usda-nrcs-sda"

    async def soil_context(self, latitude: float, longitude: float, at_time: str | None = None) -> EnvironmentalProviderResult:
        data = {
            "map_unit": "Austin silty clay fixture",
            "component": "Austin",
            "drainage_class": "well drained",
            "hydrologic_soil_group": "D",
            "available_water_capacity": {"value": "moderate", "evidence_type": "SURVEY"},
            "texture": {"value": "silty clay", "evidence_type": "SURVEY"},
            "organic_matter": {"value": None, "evidence_type": "SURVEY"},
            "ph": {"value": 7.8, "evidence_type": "SURVEY"},
            "slope": {"value": "1-3%", "evidence_type": "SURVEY"},
            "restrictive_depth": {"value": None, "evidence_type": "SURVEY"},
            "semantic_note": "SSURGO is soil survey context, not live soil moisture.",
        }
        return EnvironmentalProviderResult(
            status="AVAILABLE",
            data=data,
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    external_record_id="fixture-ssurgo-mapunit",
                    canonical_url="fixture://usda-nrcs-sda/mapunit",
                    authority="USDA NRCS Soil Data Access",
                    geographic_scope="survey map unit fixture",
                    license="unknown",
                    attribution="USDA NRCS",
                    content_hash=content_hash(data),
                )
            ],
        )


class MissingUSDASoilProvider(FixtureUSDASoilProvider):
    async def soil_context(self, latitude: float, longitude: float, at_time: str | None = None) -> EnvironmentalProviderResult:
        return EnvironmentalProviderResult(
            status="UNAVAILABLE",
            data={"semantic_note": "No soil survey result available; GAIA did not infer a soil type."},
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    external_record_id=None,
                    canonical_url="fixture://usda-nrcs-sda/no-result",
                    authority="USDA NRCS Soil Data Access",
                    geographic_scope="attempted point lookup",
                    license="unknown",
                    attribution="USDA NRCS",
                    content_hash=content_hash("no soil result"),
                )
            ],
            warnings=["soil_survey_unavailable"],
        )


class FixtureUSGSWaterProvider:
    provider_id = "usgs-water"

    async def nearby_sites(self, latitude: float, longitude: float) -> EnvironmentalProviderResult:
        data = {"sites": [{"site_no": "08158000", "name": "Colorado River at Austin fixture"}], "evidence_type": "OBSERVED"}
        return EnvironmentalProviderResult(
            status="AVAILABLE",
            data=data,
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    external_record_id="fixture-usgs-site-08158000",
                    canonical_url="fixture://usgs/sites/08158000",
                    authority="USGS",
                    geographic_scope="nearby hydrologic site fixture",
                    license="public-domain-us-government",
                    attribution="USGS",
                    content_hash=content_hash(data),
                )
            ],
        )

    async def current_conditions(self, latitude: float, longitude: float) -> EnvironmentalProviderResult:
        return EnvironmentalProviderResult(status="UNAVAILABLE", warnings=["current_water_fixture_not_implemented"])

    async def historical_conditions(self, latitude: float, longitude: float) -> EnvironmentalProviderResult:
        return EnvironmentalProviderResult(status="UNAVAILABLE", warnings=["historical_water_fixture_not_implemented"])

