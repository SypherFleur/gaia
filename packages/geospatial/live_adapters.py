from __future__ import annotations

import asyncio
import json
import re
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


# The Watershed Boundary Dataset is published as an ArcGIS map service whose
# layers are one hydrologic-unit level each ("8-digit HU (Subbasin)",
# "12-digit HU (Subwatershed)", ...). The most specific level is the most
# useful answer, so the layer is discovered from the service rather than
# pinned to an index that could move underneath us.
_HU_LAYER_PATTERN = re.compile(r"(\d+)\s*-\s*digit", re.IGNORECASE)
DEFAULT_HU_LAYER_ID = 6  # 12-digit HU (Subwatershed), used only if discovery fails


class USGSWatershedAdapter:
    """Watershed (hydrologic unit) containing a point, from the USGS Watershed
    Boundary Dataset.

    Free and keyless. This used to ask the NLDI position endpoint, but that
    returns the NHDPlus *flowline* at the coordinate — a stream reach, not a
    watershed — whose ``name`` is a GNIS stream name and is usually empty. The
    answer therefore degraded to a bare COMID presented as a watershed name.
    WBD is the authority that actually names hydrologic units, so the name
    comes from there. A point outside WBD coverage resolves UNRESOLVED rather
    than guessing a basin.
    """

    provider_id = "usgs-wbd"

    def __init__(
        self,
        *,
        user_agent: str = "GAIA Local Alpha/0.1",
        base_url: str = "https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer",
        timeout_seconds: float = 15.0,
        layer_id: int | None = None,
    ) -> None:
        self.user_agent = user_agent
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._layer_id = layer_id

    async def resolve_watershed(self, latitude: float, longitude: float, at_time: str | None = None) -> WatershedResolution:
        return await asyncio.to_thread(self._resolve_sync, latitude, longitude)

    def _resolve_sync(self, latitude: float, longitude: float) -> WatershedResolution:
        layer_id = self._hydrologic_unit_layer_id()
        url = self.request_url(latitude, longitude, layer_id)
        try:
            payload = self._get(url)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return WatershedResolution(status=ProviderStatus("UNRESOLVED", "coordinate_outside_wbd_coverage"))
            return WatershedResolution(status=ProviderStatus("UNAVAILABLE", f"wbd_http_{exc.code}"))
        except RetryExhausted as exc:
            return WatershedResolution(status=ProviderStatus("UNAVAILABLE", f"wbd_error:{exc.last_error.__class__.__name__}"))
        return self.normalize_feature_response(payload, url)

    def _hydrologic_unit_layer_id(self) -> int:
        """Ask the service which layer holds the finest hydrologic unit.

        Discovery is an optimization, not a dependency: if the catalog request
        fails we still query the documented default layer. A wrong layer yields
        no named feature and therefore UNRESOLVED — never a wrong watershed.
        """
        if self._layer_id is not None:
            return self._layer_id
        try:
            catalog = self._get(f"{self.base_url}?f=json")
        except (urllib.error.HTTPError, RetryExhausted):
            return DEFAULT_HU_LAYER_ID
        discovered = self.select_hydrologic_unit_layer(catalog)
        self._layer_id = DEFAULT_HU_LAYER_ID if discovered is None else discovered
        return self._layer_id

    @staticmethod
    def select_hydrologic_unit_layer(catalog: dict) -> int | None:
        """Layer id of the most specific ``N-digit HU`` layer in the service."""
        best_id: int | None = None
        best_digits = -1
        for layer in catalog.get("layers") or []:
            match = _HU_LAYER_PATTERN.search(str(layer.get("name", "")))
            if match is None:
                continue
            digits = int(match.group(1))
            layer_id = layer.get("id")
            if isinstance(layer_id, int) and digits > best_digits:
                best_id, best_digits = layer_id, digits
        return best_id

    def request_url(self, latitude: float, longitude: float, layer_id: int = DEFAULT_HU_LAYER_ID) -> str:
        # Reduced to ~1.1 km before egress; hydrologic units are far larger, so
        # this costs no resolution.
        query = urllib.parse.urlencode(
            {
                "geometry": f"{round(longitude, 2)},{round(latitude, 2)}",
                "geometryType": "esriGeometryPoint",
                "inSR": "4326",
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "*",
                "returnGeometry": "false",
                "f": "json",
            }
        )
        return f"{self.base_url}/{layer_id}/query?{query}"

    def _get(self, url: str) -> dict:
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent, "Accept": "application/json"})
        return request_json(request, timeout_seconds=self.timeout_seconds)

    def normalize_feature_response(self, payload: dict, url: str | None = None) -> WatershedResolution:
        # ArcGIS reports service-side failures as HTTP 200 with an error body.
        # Reading that as "no features" would turn an outage into a confident
        # "no watershed here", so it maps to UNAVAILABLE.
        error = payload.get("error")
        if isinstance(error, dict):
            return WatershedResolution(status=ProviderStatus("UNAVAILABLE", f"wbd_service_error_{error.get('code', 'unknown')}"))

        features = payload.get("features") or []
        if not features:
            return WatershedResolution(
                status=ProviderStatus("UNRESOLVED", "coordinate_outside_wbd_coverage"),
                provenance=[self._provenance(url, None, payload)],
            )

        attributes = features[0].get("attributes") or {}
        name = _attribute(attributes, lambda key: key == "name")
        huc_code = _attribute(attributes, lambda key: key.startswith("huc"))
        if not name:
            return WatershedResolution(
                status=ProviderStatus("UNRESOLVED", "wbd_feature_missing_name"),
                provenance=[self._provenance(url, huc_code, payload)],
            )
        return WatershedResolution(
            status=ProviderStatus("AVAILABLE"),
            watershed=name,
            provenance=[self._provenance(url, huc_code, payload)],
        )

    def _provenance(self, url: str | None, external_record_id: str | None, payload: dict) -> ProvenanceRecord:
        return ProvenanceRecord(
            provider=self.provider_id,
            external_record_id=external_record_id,
            canonical_url=url or f"{self.base_url}/query",
            authority="U.S. Geological Survey Watershed Boundary Dataset",
            geographic_scope="US hydrologic units",
            license="public domain (U.S. federal government work)",
            attribution="USGS Watershed Boundary Dataset (WBD)",
            content_hash=content_hash(payload),
        )


def _attribute(attributes: dict, matches) -> str | None:
    """First non-empty attribute whose lowercased key satisfies ``matches``.

    WBD field casing varies by layer and service release (``Name``/``NAME``,
    ``HUC12``/``huc12``), so keys are matched case-insensitively instead of
    being spelled out.
    """
    for key, value in attributes.items():
        if not matches(str(key).strip().lower()):
            continue
        text = str(value).strip() if value is not None else ""
        if text and text.lower() != "null":
            return text
    return None
