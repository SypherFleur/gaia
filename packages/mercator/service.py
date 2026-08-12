from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass

from packages.domain import MercatorContext, SourceRecord
from packages.domain.models import now_iso
from packages.mercator.normalization import comparable_units, normalize_commodity
from packages.mercator.tools import AMSMarketReportTool, AMSSupplyChainTool, NASSProductionTool, NASSRegionalContextTool
from packages.persistence import GaiaRepository
from packages.provenance import ProvenanceRecord
from packages.tools import ToolExecutionContext, ToolGateway, ToolRequest, ToolResult


@dataclass(frozen=True, slots=True)
class MercatorResult:
    mercator_context: MercatorContext
    provider_results: dict[str, ToolResult]
    model_run_count: int = 0

    def to_dict(self) -> dict:
        return {
            "mercator_context": asdict(self.mercator_context),
            "provider_statuses": {key: value.status.upper() for key, value in self.provider_results.items()},
            "model_run_count": self.model_run_count,
        }


class MercatorContextProvider:
    def __init__(
        self,
        *,
        repository: GaiaRepository,
        tool_gateway: ToolGateway,
        nass_production_tool: NASSProductionTool,
        nass_region_tool: NASSRegionalContextTool,
        ams_market_tool: AMSMarketReportTool,
        ams_supply_chain_tool: AMSSupplyChainTool,
    ) -> None:
        self.repository = repository
        self.tool_gateway = tool_gateway
        self.nass_production_tool = nass_production_tool
        self.nass_region_tool = nass_region_tool
        self.ams_market_tool = ams_market_tool
        self.ams_supply_chain_tool = ams_supply_chain_tool

    async def build_context(
        self,
        context: ToolExecutionContext,
        *,
        commodity: str,
        geography: dict,
        location_id: str | None = None,
        crop_or_taxon: dict | None = None,
        market_region: str | None = None,
        persist: bool = True,
    ) -> MercatorResult:
        self._require_workspace(context)
        safe_geo = _safe_public_geography(geography)
        commodity_obj = normalize_commodity(commodity, crop_or_taxon=crop_or_taxon or {})
        payload = {
            "commodity": commodity,
            "geography": safe_geo,
            "crop_or_taxon": crop_or_taxon or {},
            "market_region": market_region,
            "periods": ["2020"],
        }
        tasks = {
            "nass_production": self.tool_gateway.execute(
                self.nass_production_tool,
                context,
                ToolRequest(payload=payload, cache_key=f"mercator:nass:production:{commodity_obj['canonical_name']}:{_geo_key(safe_geo)}", cache_ttl_seconds=86400 * 30, stale_if_error_seconds=86400 * 365, allow_stale_cache=True, estimated_cost_usd=0.0, contains_exact_location=False),
            ),
            "nass_region": self.tool_gateway.execute(
                self.nass_region_tool,
                context,
                ToolRequest(payload=payload, cache_key=f"mercator:nass:region:{_geo_key(safe_geo)}", cache_ttl_seconds=86400 * 90, stale_if_error_seconds=86400 * 365, allow_stale_cache=True, estimated_cost_usd=0.0, contains_exact_location=False),
            ),
            "ams_market": self.tool_gateway.execute(
                self.ams_market_tool,
                context,
                ToolRequest(payload=payload, cache_key=f"mercator:ams:market:{commodity_obj['canonical_name']}:{market_region or _geo_key(safe_geo)}", cache_ttl_seconds=3600 * 6, stale_if_error_seconds=86400 * 7, allow_stale_cache=True, estimated_cost_usd=0.0, contains_exact_location=False),
            ),
            "ams_supply_chain": self.tool_gateway.execute(
                self.ams_supply_chain_tool,
                context,
                ToolRequest(payload=payload, cache_key=f"mercator:ams:supply:{commodity_obj['canonical_name']}:{_geo_key(safe_geo)}", cache_ttl_seconds=86400 * 180, stale_if_error_seconds=86400 * 365, allow_stale_cache=True, estimated_cost_usd=0.0, contains_exact_location=False),
            ),
        }
        resolved = await asyncio.gather(*tasks.values(), return_exceptions=True)
        provider_results = {key: _coerce_result(value) for key, value in zip(tasks, resolved)}
        source_record_ids = []
        for result in provider_results.values():
            source_record_ids.extend(self._persist_sources(context.organization_id, result.provenance))

        production = _items(provider_results, "production_statistics")
        markets = _items(provider_results, "market_reports")
        prices = _items(provider_results, "price_observations")
        regional = _items(provider_results, "regional_economic_context")
        supply_chain = _items(provider_results, "supply_chain_context")
        limitations = _limitations(provider_results, production, markets, supply_chain)
        context_obj = MercatorContext(
            organization_id=context.organization_id,
            workspace_id=context.workspace_id,
            location_id=location_id,
            commodity=commodity_obj,
            crop_or_taxon=crop_or_taxon or {},
            geography=safe_geo,
            production_statistics=production,
            market_reports=markets,
            price_observations=prices,
            regional_economic_context=regional,
            supply_chain_context=supply_chain,
            data_dates=_data_dates(production, markets, regional, supply_chain),
            freshness={
                "production": _freshness(production),
                "markets": _freshness(markets),
                "regional": _freshness(regional),
                "supply_chain": _freshness(supply_chain),
            },
            provider_statuses={key: result.status.upper() for key, result in provider_results.items()},
            source_record_ids=sorted(set(source_record_ids)),
            limitations=limitations,
            generated_at=now_iso(),
        )
        if persist:
            self.repository.create_mercator_context(context_obj)
        return MercatorResult(mercator_context=context_obj, provider_results=provider_results)

    def compare_prices(self, left: dict, right: dict) -> dict:
        comparable, reason = comparable_units(left, right)
        if not comparable:
            return {"comparable": False, "reason": reason, "difference": None}
        left_value = float(left["value"])
        right_value = float(right["value"])
        return {"comparable": True, "reason": reason, "difference": left_value - right_value}

    def _require_workspace(self, context: ToolExecutionContext) -> None:
        if self.repository.get_workspace(context.organization_id, context.workspace_id) is None:
            raise PermissionError("Workspace is missing or inaccessible")

    def _persist_sources(self, organization_id: str, provenance_records: list[ProvenanceRecord]) -> list[str]:
        source_ids = []
        for provenance in provenance_records:
            source = SourceRecord(
                organization_id=organization_id,
                provider=provenance.provider,
                source_type="economic",
                canonical_url=provenance.canonical_url,
                external_record_id=provenance.external_record_id,
                title=provenance.external_record_id or provenance.provider,
                authority=provenance.authority,
                retrieved_at=provenance.retrieved_at,
                observed_at=provenance.observed_at,
                valid_from=provenance.valid_at,
                license=provenance.license,
                attribution=provenance.attribution,
                content_hash=provenance.content_hash,
            )
            self.repository.create_source_record(source)
            source_ids.append(source.id)
        return source_ids


def _coerce_result(result: ToolResult | BaseException) -> ToolResult:
    if isinstance(result, ToolResult):
        return result
    return ToolResult.failed(f"provider_exception:{result.__class__.__name__}")


def _items(results: dict[str, ToolResult], field: str) -> list[dict]:
    merged = []
    seen = set()
    for result in results.values():
        for item in result.data.get(field, []):
            key = item.get("provider_record_id") or repr(sorted(item.items()))
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def _safe_public_geography(geography: dict) -> dict:
    return {
        key: geography.get(key)
        for key in ["country", "country_code", "state_or_region", "state_code", "county_or_district", "county_fips", "economic_regions"]
        if geography.get(key) is not None
    }


def _geo_key(geography: dict) -> str:
    return ":".join(str(geography.get(key) or "") for key in ["country_code", "state_code", "county_fips", "county_or_district"])


def _data_dates(*groups: list[dict]) -> dict:
    dates = {}
    for name, items in zip(["production", "markets", "regional", "supply_chain"], groups):
        dates[name] = sorted({str(item.get("observation_period") or item.get("report_date") or item.get("period") or "") for item in items if item})
    return dates


def _freshness(items: list[dict]) -> str:
    values = sorted({str(item.get("freshness") or "unknown") for item in items})
    return values[0] if len(values) == 1 else ",".join(values) if values else "unavailable"


def _limitations(results: dict[str, ToolResult], production: list[dict], markets: list[dict], supply_chain: list[dict]) -> list[str]:
    limitations = []
    if not production:
        limitations.append("Production statistics unavailable at requested geography; no interpolation was performed.")
    if not markets:
        limitations.append("Current market reports unavailable; no paid fallback was attempted.")
    if supply_chain:
        limitations.append("Supply-chain context is structural or historical, not live logistics.")
    for key, result in results.items():
        if result.status not in {"available", "success", "cache_hit"}:
            limitations.append(f"{key} status: {result.status.upper()}")
        limitations.extend(result.warnings)
    return sorted(set(limitations))

