from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Awaitable


JsonDict = dict[str, Any]

# A location inside the coverage of every U.S. provider, used only as a probe
# target. Never a user's real location.
PROBE_LATITUDE = 30.27
PROBE_LONGITUDE = -97.74


@dataclass(frozen=True, slots=True)
class ProviderProbe:
    provider_id: str
    label: str
    requires_key: bool = False
    key_env: str | None = None


@dataclass(slots=True)
class ProbeResult:
    provider_id: str
    label: str
    outcome: str
    detail: str = ""
    warnings: list[str] = field(default_factory=list)
    sample: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        return asdict(self)


async def _probe(provider_id: str, label: str, call: Callable[[], Awaitable[Any]], describe: Callable[[Any], tuple[str, str, JsonDict]]) -> ProbeResult:
    try:
        result = await call()
    except Exception as exc:  # a probe must never take the command down
        return ProbeResult(provider_id, label, "ERROR", f"{exc.__class__.__name__}: {exc}")
    outcome, detail, sample = describe(result)
    # Semantic caveats travel with a successful result and must stay visible;
    # they are never evidence that a provider failed.
    return ProbeResult(provider_id, label, outcome, detail, _semantic_warnings(result), sample)


def _semantic_warnings(result: Any) -> list[str]:
    return [str(item) for item in (getattr(result, "warnings", None) or [])]


def _status_of(result: Any) -> str:
    status = getattr(result, "status", None)
    # Geospatial resolutions wrap status in a ProviderStatus object.
    inner = getattr(status, "status", None)
    return str(inner or status or "UNKNOWN")


def _reason_of(result: Any) -> str:
    status = getattr(result, "status", None)
    reason = getattr(status, "reason", None)
    if reason:
        return str(reason)
    warnings = getattr(result, "warnings", None) or []
    if warnings:
        return ", ".join(str(item) for item in warnings)
    # Some adapters carry their explanation in the payload rather than warnings.
    data = getattr(result, "data", None) or {}
    return str(data.get("semantic_note") or "")


# Statuses that mean the provider answered usefully. Subsystems use different
# vocabularies: environment/research report AVAILABLE, taxonomy reports the
# resolution kind. A taxonomy match is a success, not a missing AVAILABLE.
_SUCCESS_STATUSES = frozenset({"AVAILABLE", "ACCEPTED", "SYNONYM", "AMBIGUOUS", "CACHE_HIT"})
_NO_DATA_STATUSES = frozenset({"UNRESOLVED", "UNAVAILABLE", "UNSUPPORTED_LOCATION"})


# Markers that mean the request never completed. An unreachable endpoint is a
# transport failure, not "the provider answered and had nothing" — conflating
# them would make a total outage look like normal fail-closed behavior, which
# is exactly what this command exists to tell apart.
_TRANSPORT_FAILURE_MARKERS = ("_error", "error:", "http_", "timeout", "unreachable", "refused")


def _is_transport_failure(reason: str) -> bool:
    lowered = reason.lower()
    return any(marker in lowered for marker in _TRANSPORT_FAILURE_MARKERS)


def _outcome_for(result: Any, evidence: JsonDict) -> tuple[str, str, JsonDict]:
    status = _status_of(result).upper()
    if status in _SUCCESS_STATUSES:
        # Warnings are reported separately; a semantic caveat riding along with
        # a good response never downgrades the outcome.
        return "OK", "", evidence
    reason = _reason_of(result)
    if status in _NO_DATA_STATUSES:
        if _is_transport_failure(reason):
            return "FAILED", reason, {}
        # Genuine fail-closed: the provider responded and had nothing here.
        return "NO_DATA", reason, {}
    return "FAILED", reason or status, {}


async def verify_live_providers(*, latitude: float = PROBE_LATITUDE, longitude: float = PROBE_LONGITUDE) -> list[ProbeResult]:
    """Probe every keyless live adapter against its real endpoint.

    Each adapter is called directly rather than through the runtime so the
    result reflects the provider, not local configuration. Nothing is
    persisted and no key is required.
    """
    from packages.botany.live_adapters import GBIFApiAdapter
    from packages.environment.live_adapters import (
        NASAPowerApiAdapter,
        NWSApiAdapter,
        USDASoilDataAccessAdapter,
        USGSWaterApiAdapter,
    )
    from packages.geospatial.live_adapters import CensusGeocoderAdapter, USGSWatershedAdapter
    from packages.research.europe_pmc import EuropePMCAdapter
    from packages.research.providers import ResearchSearchRequest

    user_agent = "GAIA live verification/0.1"

    async def census() -> Any:
        return await CensusGeocoderAdapter(user_agent=user_agent).resolve_admin(latitude, longitude)

    async def watershed() -> Any:
        return await USGSWatershedAdapter(user_agent=user_agent).resolve_watershed(latitude, longitude)

    async def nws() -> Any:
        return await NWSApiAdapter(user_agent).forecast(latitude, longitude)

    async def nasa() -> Any:
        return await NASAPowerApiAdapter().climate_context(latitude, longitude)

    async def soil() -> Any:
        return await USDASoilDataAccessAdapter(user_agent=user_agent).soil_context(latitude, longitude)

    async def water() -> Any:
        return await USGSWaterApiAdapter(user_agent=user_agent).nearby_sites(latitude, longitude)

    async def gbif() -> Any:
        return await GBIFApiAdapter(user_agent=user_agent).resolve_taxon("Solanum lycopersicum")

    async def europe_pmc() -> Any:
        return await EuropePMCAdapter().search(ResearchSearchRequest(query="tomato heat stress", limit=1))

    probes = [
        ("census-geocoder", "Atlas geography (US Census)", census, lambda r: _outcome_for(r, {"county": getattr(r, "county_or_district", None), "state": getattr(r, "state_code", None)})),
        ("usgs-wbd", "Atlas watershed (USGS WBD)", watershed, lambda r: _outcome_for(r, {"watershed": getattr(r, "watershed", None)})),
        ("nws", "Weather (NWS)", nws, lambda r: _outcome_for(r, {"temperature": (r.data or {}).get("temperature", {}).get("value")})),
        ("nasa-power", "Climate (NASA POWER)", nasa, lambda r: _outcome_for(r, {"temperature_history": (r.data or {}).get("temperature_history", {}).get("value")})),
        ("usda-nrcs-sda", "Soil (SSURGO)", soil, lambda r: _outcome_for(r, {"map_unit": (r.data or {}).get("map_unit")})),
        ("usgs-water", "Water (USGS NWIS)", water, lambda r: _outcome_for(r, {"site_count": len((r.data or {}).get("sites", []))})),
        ("gbif", "Taxonomy (GBIF)", gbif, lambda r: _outcome_for(r, {"accepted_name": getattr(r, "accepted_scientific_name", None)})),
        ("europe-pmc", "Research (Europe PMC)", europe_pmc, lambda r: _outcome_for(r, {"result_count": len(getattr(r, "works", []) or [])})),
    ]

    return list(await asyncio.gather(*(_probe(provider_id, label, call, describe) for provider_id, label, call, describe in probes)))


def probe_coordinate(latitude: float, longitude: float) -> JsonDict:
    """Describe the health-check coordinate so it cannot be mistaken for context.

    This is a fixed diagnostic point. It is never the user's device or saved
    location, is never persisted, and must not be read as geographic context
    for any guidance.
    """
    return {
        "latitude": latitude,
        "longitude": longitude,
        "purpose": "provider_health_check",
        "is_user_location": False,
        "note": "Fixed diagnostic coordinate for provider health only. Not device location, not a saved location, not persisted, and not geographic context for guidance.",
    }


def summarize(results: list[ProbeResult], *, latitude: float = PROBE_LATITUDE, longitude: float = PROBE_LONGITUDE) -> JsonDict:
    counts: dict[str, int] = {}
    for result in results:
        counts[result.outcome] = counts.get(result.outcome, 0) + 1
    return {
        "checked": len(results),
        "ok": counts.get("OK", 0),
        "no_data": counts.get("NO_DATA", 0),
        "failed": counts.get("FAILED", 0) + counts.get("ERROR", 0),
        "probe_coordinate": probe_coordinate(latitude, longitude),
        "providers": [result.to_dict() for result in results],
        "note": "OK means a real response parsed into GAIA's contract; any warnings are semantic caveats, not failures. NO_DATA means the provider answered but had nothing for the probe coordinate, which is correct fail-closed behavior. FAILED or ERROR means the endpoint was unreachable or its schema drifted.",
    }
