from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from packages.context import ContextCompiler
from packages.domain import MovementDecision, MovementRequest, SourceRecord
from packages.persistence import GaiaRepository
from packages.provenance import ProvenanceRecord
from packages.sentinel.engine import aggregate_status, detect_conflicts, rule_matches
from packages.sentinel.packs import JurisdictionPackRegistry, legacy_registry
from packages.sentinel.tools import RegulationMovementRulesTool, RegulationPestAlertsTool
from packages.tools import ToolExecutionContext, ToolGateway, ToolRequest, ToolResult


JsonDict = dict[str, Any]


@dataclass(frozen=True, slots=True)
class SentinelContext:
    movement_request: JsonDict
    jurisdictions: list[JsonDict]
    active_zones: list[JsonDict]
    applicable_rules: list[JsonDict]
    conflicts: list[JsonDict]
    freshness: str
    provenance: list[str]

    def to_dict(self) -> JsonDict:
        return asdict(self)


class SentinelService:
    def __init__(
        self,
        *,
        repository: GaiaRepository,
        tool_gateway: ToolGateway,
        context_compiler: ContextCompiler,
        federal_tool: RegulationMovementRulesTool,
        texas_tool: RegulationMovementRulesTool | None = None,
        jurisdiction_registry: JurisdictionPackRegistry | None = None,
        alert_tools: list[RegulationPestAlertsTool] | None = None,
    ) -> None:
        self.repository = repository
        self.tool_gateway = tool_gateway
        self.context_compiler = context_compiler
        self.federal_tool = federal_tool
        self.texas_tool = texas_tool
        self.jurisdiction_registry = jurisdiction_registry or legacy_registry(federal_tool, texas_tool)
        self.alert_tools = alert_tools or []

    async def check_movement(
        self,
        context: ToolExecutionContext,
        *,
        origin_location_id: str | None,
        destination_location_id: str | None,
        species: str | None,
        plant_part: str = "unknown",
        live_plant: bool = False,
        soil_attached: bool = False,
        planned_date: str | None = None,
        cultivar: str | None = None,
        growing_media: str | None = None,
        quantity: int | None = None,
        purpose: str | None = None,
        commercial_or_personal: str = "personal",
        source_country: str | None = None,
        destination_country: str | None = None,
        metadata: JsonDict | None = None,
    ) -> MovementDecision:
        movement_request = self.repository.create_movement_request(
            MovementRequest(
                organization_id=context.organization_id,
                workspace_id=context.workspace_id,
                origin_location_id=origin_location_id,
                destination_location_id=destination_location_id,
                planned_date=planned_date,
                species=species,
                cultivar=cultivar,
                plant_part=plant_part,
                live_plant=live_plant,
                soil_attached=soil_attached,
                growing_media=growing_media,
                quantity=quantity,
                purpose=purpose,
                commercial_or_personal=commercial_or_personal,
                source_country=source_country,
                destination_country=destination_country,
                metadata=metadata or {},
            )
        )
        sentinel_context, provider_results, unresolved = await self.build_context(context, movement_request)
        decision = self._decision_from_context(context, movement_request, sentinel_context, provider_results, unresolved)
        return self.repository.create_movement_decision(decision)

    async def build_context(self, context: ToolExecutionContext, movement_request: MovementRequest) -> tuple[SentinelContext, list[ToolResult], list[str]]:
        unresolved = _missing_required(movement_request)
        origin_geo = {}
        destination_geo = {}
        if movement_request.origin_location_id:
            origin_geo = asdict((await self.context_compiler.build_geography_context(context, movement_request.origin_location_id)).geo_context)
        if movement_request.destination_location_id:
            destination_geo = asdict((await self.context_compiler.build_geography_context(context, movement_request.destination_location_id)).geo_context)

        request_payload = {
            "origin": _safe_geo(origin_geo, movement_request.source_country),
            "destination": _safe_geo(destination_geo, movement_request.destination_country),
            "species": movement_request.species,
            "plant_part": movement_request.plant_part,
            "live_plant": movement_request.live_plant,
            "soil_attached": movement_request.soil_attached,
            "planned_date": movement_request.planned_date,
            "metadata": movement_request.metadata,
        }
        if not _movement_touches_us(origin_geo, destination_geo, movement_request):
            unresolved.append("non_us_jurisdiction_not_implemented")
        tools = self.jurisdiction_registry.movement_tools_for(origin_geo, destination_geo, request_payload)
        if _movement_touches_us(origin_geo, destination_geo, movement_request) and not tools:
            unresolved.append("us_jurisdiction_pack_unavailable")
        provider_results = []
        source_record_ids = []
        rules = []
        zones = []
        freshness_values = []
        for tool in tools:
            result = await self.tool_gateway.execute(
                tool,
                context,
                ToolRequest(
                    payload={**request_payload, "jurisdiction_pack": _pack_for_tool(tool.provider_id)},
                    cache_key=(
                        f"sentinel:{tool.provider_id}:{movement_request.species}:{movement_request.plant_part}:"
                        f"{movement_request.live_plant}:{movement_request.soil_attached}:"
                        f"{_geo_fingerprint(origin_geo)}:{_geo_fingerprint(destination_geo)}"
                    ),
                    cache_ttl_seconds=3600,
                    stale_if_error_seconds=86400,
                    allow_stale_cache=True,
                    estimated_cost_usd=0.0,
                    contains_exact_location=False,
                    regulatory_current_required=True,
                ),
            )
            provider_results.append(result)
            source_record_ids.extend(self._persist_sources(context.organization_id, result.provenance))
            if result.status not in {"AVAILABLE", "success", "cache_hit"}:
                unresolved.append(f"{tool.provider_id}_current_regulatory_source_unavailable")
            freshness = result.data.get("freshness", "UNAVAILABLE")
            freshness_values.append(freshness)
            if freshness != "CURRENT":
                unresolved.append(f"{tool.provider_id}_freshness_not_current")
            rules.extend(result.data.get("rules", []))
            zones.extend(result.data.get("zones", []))
        applicable_rules = []
        request_dict = asdict(movement_request)
        for rule in rules:
            match = rule_matches(rule, request_dict, origin_geo, destination_geo)
            if match.applicable:
                rule["match_reasons"] = match.reasons or []
                applicable_rules.append(rule)
        conflicts = detect_conflicts(applicable_rules)
        freshness = "CURRENT" if freshness_values and all(value == "CURRENT" for value in freshness_values) else "UNAVAILABLE"
        if conflicts:
            freshness = "CONFLICT"
        jurisdictions = _jurisdictions(origin_geo, destination_geo)
        return (
            SentinelContext(
                movement_request=request_dict,
                jurisdictions=jurisdictions,
                active_zones=zones,
                applicable_rules=applicable_rules,
                conflicts=conflicts,
                freshness=freshness,
                provenance=sorted(set(source_record_ids)),
            ),
            provider_results,
            unresolved,
        )

    async def regulated_pest_context(self, context: ToolExecutionContext, *, species: str | None, location_id: str | None, visual_hypothesis: str) -> MovementDecision:
        location_geo = {}
        if location_id:
            location_geo = asdict((await self.context_compiler.build_geography_context(context, location_id)).geo_context)
        alert_results: list[ToolResult] = []
        alert_source_ids: list[str] = []
        alert_reporting: list[JsonDict] = []
        alert_tools = self.alert_tools or self.jurisdiction_registry.pest_alert_tools_for(location_geo.get("country_code"), location_geo.get("state_code"))
        alert_payload = {
            "origin": _safe_geo(location_geo, None),
            "destination": _safe_geo(location_geo, None),
            "species": species,
            "plant_part": "live plant",
            "live_plant": True,
            "soil_attached": False,
            "planned_date": None,
            "metadata": {"visual_hypothesis": visual_hypothesis, "vision_status": "hypothesis_not_diagnosis"},
        }
        for tool in alert_tools:
            result = await self.tool_gateway.execute(
                tool,
                context,
                ToolRequest(
                    payload={**alert_payload, "jurisdiction_pack": _pack_for_tool(tool.provider_id)},
                    cache_key=f"sentinel-alert:{tool.provider_id}:{species}:{location_geo.get('state_code')}:{visual_hypothesis}",
                    cache_ttl_seconds=3600,
                    stale_if_error_seconds=86400,
                    allow_stale_cache=True,
                    estimated_cost_usd=0.0,
                    contains_exact_location=False,
                    regulatory_current_required=True,
                ),
            )
            alert_results.append(result)
            alert_source_ids.extend(self._persist_sources(context.organization_id, result.provenance))
            alert_reporting.extend(result.data.get("reporting_requirements", []))
        decision = await self.check_movement(
            context,
            origin_location_id=location_id,
            destination_location_id=location_id,
            species=species,
            plant_part="live plant",
            live_plant=True,
            purpose="regulated pest alert",
            metadata={"visual_hypothesis": visual_hypothesis, "vision_status": "hypothesis_not_diagnosis"},
        )
        decision.source_record_ids = sorted(set(decision.source_record_ids + alert_source_ids))
        decision.reporting_requirements.extend(alert_reporting)
        for result in alert_results:
            if result.status not in {"AVAILABLE", "success", "cache_hit"}:
                decision.unresolved_questions.append(f"{result.data.get('provider_id', 'pest_alert_provider')}_alert_source_unavailable")
        decision.reporting_requirements.append(
            {
                "authority": "Sentinel",
                "instruction": f"Vision hypothesis '{visual_hypothesis}' is not a diagnosis. Preserve images, location context, and plant material evidence. Do not submit an automatic report in Phase 8.",
            }
        )
        return decision

    def _decision_from_context(
        self,
        context: ToolExecutionContext,
        movement_request: MovementRequest,
        sentinel_context: SentinelContext,
        provider_results: list[ToolResult],
        unresolved: list[str],
    ) -> MovementDecision:
        status = aggregate_status(sentinel_context.applicable_rules, freshness=sentinel_context.freshness, conflicts=sentinel_context.conflicts, unresolved_questions=unresolved)
        conditions = [item for rule in sentinel_context.applicable_rules for item in rule.get("conditions", [])]
        permits = [item for rule in sentinel_context.applicable_rules for item in rule.get("permits", []) + rule.get("permit_requirements", [])]
        treatments = [item for rule in sentinel_context.applicable_rules for item in rule.get("treatments", []) + rule.get("treatment_requirements", [])]
        inspection = [item for rule in sentinel_context.applicable_rules for item in rule.get("inspection", [])]
        reporting = [item for rule in sentinel_context.applicable_rules for item in rule.get("reporting", [])]
        source_ids = sentinel_context.provenance
        authority_names = sorted({rule.get("authority") for rule in sentinel_context.applicable_rules if rule.get("authority")})
        if not authority_names:
            authority_names = sorted({result.data.get("provider_id") for result in provider_results if result.data.get("provider_id")})
        return MovementDecision(
            organization_id=context.organization_id,
            workspace_id=context.workspace_id,
            movement_request_id=movement_request.id,
            status=status,
            applicable_jurisdictions=sentinel_context.jurisdictions,
            applicable_rules=sentinel_context.applicable_rules,
            conditions=conditions,
            permit_requirements=permits,
            treatment_requirements=treatments,
            inspection_requirements=inspection,
            reporting_requirements=reporting,
            unresolved_questions=sorted(set(unresolved)),
            conflicts=sentinel_context.conflicts,
            freshness=sentinel_context.freshness,
            source_record_ids=source_ids,
            authority_statement=f"Based on current retrieved sources from {', '.join(authority_names)}. GAIA is not the legal authority.",
        )

    def _persist_sources(self, organization_id: str, provenance_records: list[ProvenanceRecord]) -> list[str]:
        source_ids = []
        for provenance in provenance_records:
            source = SourceRecord(
                organization_id=organization_id,
                provider=provenance.provider,
                source_type="regulatory",
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


def _missing_required(request: MovementRequest) -> list[str]:
    missing = []
    if not request.origin_location_id and not request.source_country:
        missing.append("origin_location_or_source_country_required")
    if not request.destination_location_id and not request.destination_country:
        missing.append("destination_location_or_destination_country_required")
    if not request.species:
        missing.append("species_required_for_regulatory_matching")
    if request.plant_part == "unknown":
        missing.append("plant_part_required")
    return missing


def _safe_geo(geo: JsonDict, fallback_country: str | None) -> JsonDict:
    return {
        "country_code": geo.get("country_code") or fallback_country,
        "state_code": geo.get("state_code"),
        "state_or_region": geo.get("state_or_region"),
        "county_or_district": geo.get("county_or_district"),
        "county_fips": geo.get("county_fips"),
        "regulatory_zones": geo.get("regulatory_zones", []),
        "quarantine_zones": geo.get("quarantine_zones", []),
        "pest_zones": geo.get("pest_zones", []),
    }


def _pack_for_tool(provider_id: str) -> str:
    if provider_id == "texas-agriculture":
        return "us_tx"
    if provider_id == "florida-fdacs":
        return "us_fl"
    return "us_federal"


def _movement_touches_us(origin_geo: JsonDict, destination_geo: JsonDict, request: MovementRequest) -> bool:
    countries = {
        origin_geo.get("country_code") or request.source_country,
        destination_geo.get("country_code") or request.destination_country,
    }
    return "US" in countries


def _geo_fingerprint(geo: JsonDict) -> str:
    zones = sorted(
        str(zone)
        for zone in (
            geo.get("regulatory_zones", [])
            + geo.get("quarantine_zones", [])
            + geo.get("pest_zones", [])
        )
    )
    return "|".join(
        [
            str(geo.get("country_code") or ""),
            str(geo.get("state_code") or ""),
            str(geo.get("county_fips") or geo.get("county_or_district") or ""),
            ",".join(zones),
        ]
    )


def _jurisdictions(origin_geo: JsonDict, destination_geo: JsonDict) -> list[JsonDict]:
    jurisdictions = []
    for label, geo in [("origin", origin_geo), ("destination", destination_geo)]:
        if not geo:
            continue
        jurisdictions.append(
            {
                "side": label,
                "country_code": geo.get("country_code"),
                "state_code": geo.get("state_code"),
                "county_or_district": geo.get("county_or_district"),
                "zones": geo.get("regulatory_zones", []) + geo.get("quarantine_zones", []) + geo.get("pest_zones", []),
            }
        )
    return jurisdictions
