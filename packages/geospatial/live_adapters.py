from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.parse
import urllib.request

from packages.geospatial.providers import AdminResolution, ProviderStatus, WatershedResolution
from packages.providers.http_retry import RetryExhausted, request_json
from packages.provenance import ProvenanceRecord, content_hash


class CensusGeocoderAdapter:
    """Live U.S. admin geography from the Census Bureau reverse geocoder.

    Coordinates are reduced to two decimal places (~1.1 km) before any request
    is built, so exact private coordinates never leave the machine regardless
    of the caller's privacy settings. County resolution is unaffected except
    within roughly one kilometer of a county border.
    """

    provider_id = "census-geocoder"

    def __init__(
        self,
        *,
        user_agent: str = "GAIA Local Alpha/0.1",
        base_url: str = "https://geocoding.geo.census.gov",
        timeout_seconds: float = 10.0,
    ) -> None:
        self.user_agent = user_agent
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.last_request_url: str | None = None

    async def resolve_admin(self, latitude: float, longitude: float, at_time: str | None = None) -> AdminResolution:
        return await asyncio.to_thread(self._resolve_admin_sync, latitude, longitude)

    def _resolve_admin_sync(self, latitude: float, longitude: float) -> AdminResolution:
        url = self.request_url(latitude, longitude)
        self.last_request_url = url
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent, "Accept": "application/json"})
        try:
            payload = request_json(request, timeout_seconds=self.timeout_seconds)
        except urllib.error.HTTPError as exc:
            return AdminResolution(status=ProviderStatus("UNAVAILABLE", f"census_http_{exc.code}"))
        except RetryExhausted as exc:
            return AdminResolution(status=ProviderStatus("UNAVAILABLE", f"census_error:{exc.last_error.__class__.__name__}"))
        return self.normalize_geographies_response(payload, url)

    def request_url(self, latitude: float, longitude: float) -> str:
        reduced_latitude = round(latitude, 2)
        reduced_longitude = round(longitude, 2)
        params = urllib.parse.urlencode(
            {
                "x": reduced_longitude,
                "y": reduced_latitude,
                "benchmark": "Public_AR_Current",
                "vintage": "Current_Current",
                "layers": "States,Counties",
                "format": "json",
            }
        )
        return f"{self.base_url}/geocoder/geographies/coordinates?{params}"

    def normalize_geographies_response(self, payload: dict, url: str | None = None) -> AdminResolution:
        geographies = ((payload.get("result") or {}).get("geographies")) or {}
        counties = geographies.get("Counties") or []
        states = geographies.get("States") or []
        if not counties or not states:
            # Non-U.S. or offshore coordinates: the Census geocoder has no
            # answer, and fabricating one is worse than saying so.
            return AdminResolution(
                status=ProviderStatus("UNRESOLVED", "coordinate_outside_census_coverage"),
                provenance=[self._provenance(url, None, payload)],
            )
        county = counties[0]
        state = states[0]
        county_fips = str(county.get("GEOID") or "") or None
        return AdminResolution(
            status=ProviderStatus("AVAILABLE"),
            country="United States",
            country_code="US",
            state_or_region=state.get("NAME"),
            state_code=state.get("STUSAB"),
            county_or_district=county.get("NAME"),
            county_fips=county_fips,
            # The Census geocoder does not report timezone or elevation;
            # downstream consumers use the Location record's own values.
            timezone=None,
            elevation_m=None,
            provenance=[self._provenance(url, county_fips, payload)],
        )

    def _provenance(self, url: str | None, external_record_id: str | None, payload: dict) -> ProvenanceRecord:
        return ProvenanceRecord(
            provider=self.provider_id,
            external_record_id=external_record_id,
            canonical_url=url or f"{self.base_url}/geocoder/geographies/coordinates",
            authority="U.S. Census Bureau Geocoding Services",
            geographic_scope="US administrative geography",
            license="public domain (U.S. federal government work)",
            attribution="U.S. Census Bureau",
            content_hash=content_hash(payload),
        )


class USGSWatershedAdapter:
    """Watershed (HUC) containing a point, via the USGS NLDI service.

    Free and keyless. Returns the hydrologic unit name and code; a point with
    no NLDI feature resolves UNRESOLVED rather than guessing a basin.
    """

    provider_id = "usgs-nldi"

    def __init__(
        self,
        *,
        user_agent: str = "GAIA Local Alpha/0.1",
        base_url: str = "https://api.water.usgs.gov/nldi",
        timeout_seconds: float = 15.0,
    ) -> None:
        self.user_agent = user_agent
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def resolve_watershed(self, latitude: float, longitude: float, at_time: str | None = None) -> WatershedResolution:
        return await asyncio.to_thread(self._resolve_sync, latitude, longitude)

    def _resolve_sync(self, latitude: float, longitude: float) -> WatershedResolution:
        url = self.request_url(latitude, longitude)
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent, "Accept": "application/json"})
        try:
            payload = request_json(request, timeout_seconds=self.timeout_seconds)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return WatershedResolution(status=ProviderStatus("UNRESOLVED", "coordinate_outside_nldi_coverage"))
            return WatershedResolution(status=ProviderStatus("UNAVAILABLE", f"nldi_http_{exc.code}"))
        except RetryExhausted as exc:
            return WatershedResolution(status=ProviderStatus("UNAVAILABLE", f"nldi_error:{exc.last_error.__class__.__name__}"))
        return self.normalize_feature_response(payload, url)

    def request_url(self, latitude: float, longitude: float) -> str:
        # Reduced to ~1.1 km before egress; HUC polygons are far larger, so
        # this costs no resolution.
        point = f"POINT({round(longitude, 2)} {round(latitude, 2)})"
        return f"{self.base_url}/linked-data/comid/position?f=json&coords={urllib.parse.quote(point)}"

    def normalize_feature_response(self, payload: dict, url: str | None = None) -> WatershedResolution:
        features = payload.get("features") or []
        if not features:
            return WatershedResolution(
                status=ProviderStatus("UNRESOLVED", "no_nldi_feature_for_coordinate"),
                provenance=[self._provenance(url, None, payload)],
            )
        properties = features[0].get("properties") or {}
        # NLDI exposes the catchment identifier under varying keys by endpoint
        # version; prefer a human-readable name and fall back to the code.
        name = properties.get("name") or properties.get("reachcode") or properties.get("comid")
        identifier = properties.get("comid") or properties.get("reachcode")
        if not name:
            return WatershedResolution(
                status=ProviderStatus("UNRESOLVED", "nldi_feature_missing_identifier"),
                provenance=[self._provenance(url, None, payload)],
            )
        return WatershedResolution(
            status=ProviderStatus("AVAILABLE"),
            watershed=str(name),
            provenance=[self._provenance(url, str(identifier) if identifier else None, payload)],
        )

    def _provenance(self, url: str | None, external_record_id: str | None, payload: dict) -> ProvenanceRecord:
        return ProvenanceRecord(
            provider=self.provider_id,
            external_record_id=external_record_id,
            canonical_url=url or f"{self.base_url}/linked-data/comid/position",
            authority="U.S. Geological Survey Network-Linked Data Index",
            geographic_scope="US hydrologic units",
            license="public domain (U.S. federal government work)",
            attribution="USGS NLDI",
            content_hash=content_hash(payload),
        )
