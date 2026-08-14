from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from packages.context import ContextBundle, ContextCompiler
from packages.botany import BotanistService
from packages.domain import Conversation, EvidenceClaim, GuidancePlan, Message
from packages.model_gateway import (
    GuidancePlanValidationError,
    ModelGateway,
    ModelRequest,
    build_guidance_prompt,
    validate_guidance_plan_draft,
)
from packages.mercator import MercatorContextProvider
from packages.orchestration.guidance_graph import GuidanceWorkflowGraph
from packages.persistence import GaiaRepository
from packages.season import SeasonContextProvider, SeasonPlanRequest, SeasonService
from packages.tools import ToolExecutionContext


RouteDecision = Literal["geography", "environment", "economics", "reasoning", "season"]


@dataclass(frozen=True, slots=True)
class ChatResult:
    conversation_id: str
    user_message_id: str
    assistant_message_id: str
    route: RouteDecision | str
    content: str
    source_record_ids: list[str] = field(default_factory=list)
    context_bundle: ContextBundle | None = None
    guidance_plan_id: str | None = None
    model_run_ids: list[str] | None = None
    model_run_count: int = 0
    provider_diagnostics: dict | None = None
    structured_response: dict | None = None
    validation_error: str | None = None


class GaiaOrchestrator:
    def __init__(
        self,
        *,
        repository: GaiaRepository,
        context_compiler: ContextCompiler,
        model_gateway: ModelGateway,
        default_model_provider_id: str = "ollama-local",
        botanist: BotanistService | None = None,
        season: SeasonService | None = None,
        season_context_provider: SeasonContextProvider | None = None,
        mercator_context_provider: MercatorContextProvider | None = None,
    ) -> None:
        self.repository = repository
        self.context_compiler = context_compiler
        self.model_gateway = model_gateway
        self.default_model_provider_id = default_model_provider_id
        self.botanist = botanist
        self.season = season
        self.season_context_provider = season_context_provider
        self.mercator_context_provider = mercator_context_provider
        self.guidance_graph = GuidanceWorkflowGraph(self)

    async def handle_chat(
        self,
        context: ToolExecutionContext,
        *,
        message: str,
        location_id: str | None,
        user_plant_id: str | None = None,
        conversation_id: str | None = None,
    ) -> ChatResult:
        conversation = self._ensure_conversation(context, conversation_id, message, location_id, user_plant_id)
        user_message = self.repository.create_message(
            Message(
                organization_id=context.organization_id,
                conversation_id=conversation.id,
                role="user",
                content=message,
                metadata={"untrusted_user_input": True},
            )
        )
        return await self.guidance_graph.run(
            context=context,
            conversation_id=conversation.id,
            user_message_id=user_message.id,
            message=message,
            location_id=location_id,
            user_plant_id=user_plant_id,
        )

    def graph_summary(self) -> dict:
        return self.guidance_graph.summary().to_dict()

    async def _handle_geography(
        self,
        context: ToolExecutionContext,
        conversation_id: str,
        user_message_id: str,
        location_id: str | None,
    ) -> ChatResult:
        if location_id is None:
            return self._location_required(context, conversation_id, user_message_id, "geography")
        bundle = await self.context_compiler.build_geography_context(context, location_id)
        geo = bundle.geo_context
        place = ", ".join(part for part in [geo.county_or_district, geo.state_or_region, geo.country] if part)
        location = self.repository.get_location(context.organization_id, location_id) or {}
        qualifier = _location_qualifier(location)
        content = f"{qualifier} resolves to {place}."
        assistant_message = self.repository.create_message(
            Message(
                organization_id=context.organization_id,
                conversation_id=conversation_id,
                role="assistant",
                content=content,
                route="geography",
                source_record_ids=geo.source_record_ids,
                metadata={"model_run_count": 0, "provider_statuses": bundle.atlas.provider_statuses},
            )
        )
        return ChatResult(
            conversation_id=conversation_id,
            user_message_id=user_message_id,
            assistant_message_id=assistant_message.id,
            route="geography",
            content=content,
            source_record_ids=geo.source_record_ids,
            context_bundle=bundle,
            model_run_ids=[],
            model_run_count=0,
            provider_diagnostics={"atlas": bundle.atlas.provider_statuses},
        )

    async def _handle_economics(
        self,
        context: ToolExecutionContext,
        conversation_id: str,
        user_message_id: str,
        location_id: str | None,
        message: str,
        user_plant_id: str | None = None,
    ) -> ChatResult:
        if location_id is None:
            return self._location_required(context, conversation_id, user_message_id, "economics")
        geography_bundle = await self.context_compiler.build_geography_context(context, location_id)
        geography = geography_bundle.to_dict()["geo_context"]
        commodity = _extract_crops(message)[0]
        crop_or_taxon = {}
        if user_plant_id is not None:
            plant = self.repository.get_user_plant(context.organization_id, user_plant_id)
            entity = self.repository.get_plant_entity(plant["plant_entity_id"]) if plant else None
            crop_or_taxon = entity or {}
        result = await self.mercator_context_provider.build_context(
            context,
            commodity=commodity,
            geography=geography,
            location_id=location_id,
            crop_or_taxon=crop_or_taxon,
        )
        mercator = result.mercator_context
        price = mercator.price_observations[0] if mercator.price_observations else {}
        production = mercator.production_statistics[0] if mercator.production_statistics else {}
        content = (
            f"Mercator found dated economic context for {mercator.commodity.get('canonical_name', commodity)}. "
            f"Latest production period: {production.get('observation_period', 'unavailable')}. "
            f"Recent market report date: {price.get('report_date', 'unavailable')}. "
            "This is descriptive context, not a forecast, guarantee, or trading signal."
        )
        assistant_message = self.repository.create_message(
            Message(
                organization_id=context.organization_id,
                conversation_id=conversation_id,
                role="assistant",
                content=content,
                route="economics",
                source_record_ids=mercator.source_record_ids,
                metadata={
                    "model_run_count": 0,
                    "provider_statuses": mercator.provider_statuses,
                    "mercator_context_id": mercator.id,
                    "limitations": mercator.limitations,
                },
            )
        )
        return ChatResult(
            conversation_id=conversation_id,
            user_message_id=user_message_id,
            assistant_message_id=assistant_message.id,
            route="economics",
            content=content,
            source_record_ids=mercator.source_record_ids,
            model_run_ids=[],
            model_run_count=0,
            provider_diagnostics={"mercator": mercator.provider_statuses},
        )

    async def _handle_environment(
        self,
        context: ToolExecutionContext,
        conversation_id: str,
        user_message_id: str,
        location_id: str | None,
    ) -> ChatResult:
        if location_id is None:
            return self._location_required(context, conversation_id, user_message_id, "environment")
        bundle = await self.context_compiler.build_environmental_context(context, location_id)
        snapshot = bundle.environmental_snapshot
        geo = bundle.geo_context
        report = _environment_report(bundle)
        content = _render_environment_report(report)
        source_ids = snapshot.source_record_ids if snapshot is not None else geo.source_record_ids
        assistant_message = self.repository.create_message(
            Message(
                organization_id=context.organization_id,
                conversation_id=conversation_id,
                role="assistant",
                content=content,
                route="environment",
                source_record_ids=source_ids,
                metadata={
                    "model_run_count": 0,
                    "environment_report": report,
                    "atlas_provider_statuses": bundle.atlas.provider_statuses,
                    "terra_provider_statuses": snapshot.provider_statuses if snapshot is not None else {},
                },
            )
        )
        return ChatResult(
            conversation_id=conversation_id,
            user_message_id=user_message_id,
            assistant_message_id=assistant_message.id,
            route="environment",
            content=content,
            source_record_ids=source_ids,
            context_bundle=bundle,
            model_run_ids=[],
            model_run_count=0,
            provider_diagnostics={
                "atlas": bundle.atlas.provider_statuses,
                "terra": snapshot.provider_statuses if snapshot is not None else {},
            },
            structured_response=report,
        )

    async def _handle_reasoning(
        self,
        context: ToolExecutionContext,
        conversation_id: str,
        user_message_id: str,
        location_id: str | None,
        message: str,
        user_plant_id: str | None = None,
    ) -> ChatResult:
        if location_id is None:
            return self._location_required(context, conversation_id, user_message_id, "reasoning")
        bundle = await self.context_compiler.build_environmental_context(context, location_id)
        if user_plant_id is not None and self.botanist is not None:
            botanist_context = await self.botanist.build_context(context, user_plant_id)
            bundle = ContextBundle(
                geo_context=bundle.geo_context,
                environmental_snapshot=bundle.environmental_snapshot,
                atlas=bundle.atlas,
                terra=bundle.terra,
                botanist_context=botanist_context,
                model_run_count=bundle.model_run_count,
            )
        context_dict = bundle.to_dict()
        source_record_ids = context_dict["source_record_ids"]
        prompt = build_guidance_prompt(message, context_dict)
        self.repository.upsert_prompt_harness(prompt.harness)
        model_request = ModelRequest(
            messages=prompt.messages,
            prompt_id=prompt.prompt_id,
            prompt_version=prompt.semantic_version,
            prompt_hash=prompt.prompt_hash,
            response_format="json",
            temperature=0.2,
            max_output_tokens=1200,
            metadata={"route": "reasoning", "context_source_count": len(source_record_ids)},
            contains_private_text=True,
            contains_exact_location=False,
            estimated_cost_usd=0.0,
        )
        model_response = await self.model_gateway.generate(context, self.default_model_provider_id, model_request)
        if model_response.status != "success":
            return self._safe_failure(
                context,
                conversation_id,
                user_message_id,
                bundle,
                model_response.model_run_id,
                model_response.error or "model_generation_failed",
            )
        try:
            draft = validate_guidance_plan_draft(model_response.content)
        except GuidancePlanValidationError as exc:
            return self._safe_failure(
                context,
                conversation_id,
                user_message_id,
                bundle,
                model_response.model_run_id,
                str(exc),
            )

        claim_text = _primary_claim(draft)
        evidence_claim = self.repository.create_evidence_claim(
            EvidenceClaim(
                organization_id=context.organization_id,
                claim_text=claim_text,
                evidence_grade="C",
                confidence=float(draft.get("uncertainty", {}).get("confidence", 0.62) or 0.62),
                source_record_ids=source_record_ids,
            )
        )
        guidance_plan = self.repository.create_guidance_plan(
            GuidancePlan(
                organization_id=context.organization_id,
                workspace_id=context.workspace_id,
                conversation_id=conversation_id,
                subject=draft["subject"],
                situation=draft["situation"],
                recommendations=draft["recommendations"],
                actions=draft["actions"],
                timing=draft["timing"],
                resources=draft["resources"],
                evidence_claim_ids=[evidence_claim.id],
                risks=draft["risks"],
                uncertainty=draft["uncertainty"],
                measurements_to_take=draft["measurements_to_take"],
                follow_up=draft["follow_up"],
                geo_context_id=bundle.geo_context.id,
                environmental_snapshot_id=bundle.environmental_snapshot.id if bundle.environmental_snapshot else None,
                user_plant_id=user_plant_id,
                model_run_ids=[model_response.model_run_id] if model_response.model_run_id else [],
            )
        )
        content = _render_guidance_plan(guidance_plan)
        assistant_message = self.repository.create_message(
            Message(
                organization_id=context.organization_id,
                conversation_id=conversation_id,
                role="assistant",
                content=content,
                route="reasoning",
                model_run_id=model_response.model_run_id,
                guidance_plan_id=guidance_plan.id,
                source_record_ids=source_record_ids,
                metadata={
                    "model": model_response.model,
                    "provider_id": model_response.provider_id,
                    "validated_guidance_plan": True,
                    "trusted_source_ids_attached_by": "gaia_orchestrator",
                },
            )
        )
        return ChatResult(
            conversation_id=conversation_id,
            user_message_id=user_message_id,
            assistant_message_id=assistant_message.id,
            route="reasoning",
            content=content,
            source_record_ids=source_record_ids,
            context_bundle=bundle,
            guidance_plan_id=guidance_plan.id,
            model_run_ids=[model_response.model_run_id] if model_response.model_run_id else [],
            model_run_count=1 if model_response.model_run_id else 0,
            provider_diagnostics={
                "model": {"provider_id": model_response.provider_id, "model": model_response.model},
                "atlas": bundle.atlas.provider_statuses,
                "terra": bundle.environmental_snapshot.provider_statuses if bundle.environmental_snapshot else {},
            },
        )

    async def _handle_season(
        self,
        context: ToolExecutionContext,
        conversation_id: str,
        user_message_id: str,
        location_id: str | None,
        message: str,
    ) -> ChatResult:
        if location_id is None:
            return self._location_required(context, conversation_id, user_message_id, "season")
        crops = _extract_crops(message)
        request = SeasonPlanRequest(
            workspace_id=context.workspace_id,
            location_id=location_id,
            objective=message,
            crop_names=crops,
            start_date="2026-09-15",
            end_date="2026-12-15",
            constraints={"planning_date": "2026-08-11"},
            timezone="America/Chicago",
        )
        season_context = await self.season_context_provider.build(context, request, include_mercator=_asks_for_economics(message))
        plan, actions, model_run_ids = await self.season.create_plan(context, request, season_context)
        content = f"{plan.name}: {len(actions)} actions created. Confidence: {plan.confidence}. Calendar writes require preview and confirmation."
        assistant_message = self.repository.create_message(
            Message(
                organization_id=context.organization_id,
                conversation_id=conversation_id,
                role="assistant",
                content=content,
                route="season",
                metadata={"season_plan_id": plan.id, "action_count": len(actions), "model_run_count": len(model_run_ids)},
            )
        )
        return ChatResult(
            conversation_id=conversation_id,
            user_message_id=user_message_id,
            assistant_message_id=assistant_message.id,
            route="season",
            content=content,
            model_run_ids=model_run_ids,
            model_run_count=len(model_run_ids),
            provider_diagnostics={"season": {"plan_id": plan.id, "action_count": len(actions)}},
        )

    def _safe_failure(
        self,
        context: ToolExecutionContext,
        conversation_id: str,
        user_message_id: str,
        bundle: ContextBundle,
        model_run_id: str | None,
        reason: str,
    ) -> ChatResult:
        content = "I could not safely validate a GuidancePlan from the model output, so I did not save a plan."
        assistant_message = self.repository.create_message(
            Message(
                organization_id=context.organization_id,
                conversation_id=conversation_id,
                role="assistant",
                content=content,
                route="reasoning_validation_failed",
                model_run_id=model_run_id,
                source_record_ids=bundle.to_dict()["source_record_ids"],
                metadata={"validation_error": reason, "guidance_plan_persisted": False},
            )
        )
        return ChatResult(
            conversation_id=conversation_id,
            user_message_id=user_message_id,
            assistant_message_id=assistant_message.id,
            route="reasoning_validation_failed",
            content=content,
            source_record_ids=bundle.to_dict()["source_record_ids"],
            context_bundle=bundle,
            guidance_plan_id=None,
            model_run_ids=[model_run_id] if model_run_id else [],
            model_run_count=1 if model_run_id else 0,
            validation_error=reason,
        )

    def _location_required(
        self,
        context: ToolExecutionContext,
        conversation_id: str,
        user_message_id: str,
        attempted_route: str,
    ) -> ChatResult:
        content = (
            "No active real location is set. Use browser geolocation with permission, enter a location, "
            "or select a saved location before GAIA resolves local guidance."
        )
        assistant_message = self.repository.create_message(
            Message(
                organization_id=context.organization_id,
                conversation_id=conversation_id,
                role="assistant",
                content=content,
                route="location_required",
                metadata={"attempted_route": attempted_route, "model_run_count": 0},
            )
        )
        return ChatResult(
            conversation_id=conversation_id,
            user_message_id=user_message_id,
            assistant_message_id=assistant_message.id,
            route="location_required",
            content=content,
            source_record_ids=[],
            model_run_ids=[],
            model_run_count=0,
            provider_diagnostics={"location": {"status": "missing", "attempted_route": attempted_route}},
        )

    def _ensure_conversation(
        self,
        context: ToolExecutionContext,
        conversation_id: str | None,
        message: str,
        location_id: str | None,
        user_plant_id: str | None,
    ) -> Conversation:
        if conversation_id is not None:
            raw = self.repository.get_conversation(context.organization_id, conversation_id)
            if raw is None:
                raise PermissionError("Conversation is missing or inaccessible")
            return Conversation(
                id=raw["id"],
                organization_id=raw["organization_id"],
                workspace_id=raw["workspace_id"],
                user_id=raw["user_id"],
                title=raw["title"],
                location_id=raw["location_id"],
                user_plant_id=raw.get("user_plant_id"),
                state=raw["state"],
                last_message_at=raw["last_message_at"],
            )
        title = message.strip().splitlines()[0][:80] or "GAIA conversation"
        return self.repository.create_conversation(
            Conversation(
                organization_id=context.organization_id,
                workspace_id=context.workspace_id,
                user_id=context.user_id,
                title=title,
                location_id=location_id,
                user_plant_id=user_plant_id,
            )
        )


def classify_route(message: str) -> RouteDecision:
    text = message.lower()
    if (
        "plan my" in text
        or "fall garden" in text
        or "add this to my calendar" in text
        or "calendar" in text
        or ("should i plant" in text and _asks_for_economics(message))
        or ("good crop" in text and ("grow" in text or "season" in text))
    ):
        return "season"
    if _asks_for_economics(message):
        return "economics"
    if "county" in text or "hardiness zone" in text or "where am i" in text:
        return "geography"
    if _asks_for_environment(message):
        return "environment"
    return "reasoning"


def _extract_crops(message: str) -> list[str]:
    text = message.lower()
    crops = []
    for crop in ["tomatoes", "peppers", "collards", "tomato", "pepper", "collard", "citrus"]:
        if crop in text:
            crops.append({"tomatoes": "tomato", "peppers": "pepper", "collards": "collard"}.get(crop, crop))
    return list(dict.fromkeys(crops)) or ["crop"]


def _asks_for_economics(message: str) -> bool:
    text = message.lower()
    return any(term in text for term in ["market", "price", "prices", "production", "economically", "economic", "supply-chain", "supply chain", "wholesale"])


def _asks_for_environment(message: str) -> bool:
    text = message.lower()
    if "good for planting" in text:
        return True
    if any(term in text for term in ["what should i do", "what do i do", "what should we do", "what should i consider", "recommend", "advice"]):
        return False
    return any(
        term in text
        for term in [
            "environmental condition",
            "environmental conditions",
            "growing condition",
            "growing conditions",
            "weather",
            "conditions outside",
            "outside conditions",
            "how hot",
            "how cold",
            "temperature",
            "humidity",
            "rain",
            "wind",
            "soil",
            "day length",
            "daylight",
            "photoperiod",
            "solar radiation",
        ]
    )


def _environment_report(bundle: ContextBundle) -> dict:
    geo = bundle.geo_context
    snapshot = bundle.environmental_snapshot
    report = {
        "type": "environment_report",
        "location": _location_report(geo),
        "temperature": _measurement_report(snapshot.temperature if snapshot is not None else {}),
        "precipitation_probability": _measurement_report(snapshot.precipitation if snapshot is not None else {}),
        "humidity": _measurement_report(snapshot.humidity if snapshot is not None else {}),
        "wind": _wind_report(snapshot.wind if snapshot is not None else {}),
        "alerts": (snapshot.forecast.get("alerts") if snapshot is not None and isinstance(snapshot.forecast, dict) else []) or [],
        "photoperiod": _measurement_report(snapshot.photoperiod if snapshot is not None else {}, decimals=1),
        "solar_radiation": _measurement_report(snapshot.solar_radiation if snapshot is not None else {}),
        "soil_context": _context_status_report(snapshot.soil_context if snapshot is not None else {}),
        "soil_moisture_context": _context_status_report(snapshot.soil_moisture_context if snapshot is not None else {}),
        "water_context": _context_status_report(snapshot.water_context if snapshot is not None else {}),
        "drought_context": _context_status_report(snapshot.drought_context if snapshot is not None else {}),
        "retrieved_at": snapshot.retrieved_at if snapshot is not None else None,
        "valid_at": snapshot.observed_or_valid_at if snapshot is not None else None,
        "sources": {
            "source_record_ids": sorted(set(geo.source_record_ids) | set(snapshot.source_record_ids if snapshot is not None else [])),
            "atlas_provider_statuses": bundle.atlas.provider_statuses,
            "terra_provider_statuses": snapshot.provider_statuses if snapshot is not None else {},
        },
    }
    return _strip_none(report)


def _location_report(geo) -> dict:
    return _strip_none(
        {
            "label": _location_name(geo),
            "country_code": geo.country_code,
            "state_or_region": geo.state_or_region,
            "state_code": geo.state_code,
            "county_or_district": geo.county_or_district,
            "county_fips": geo.county_fips,
            "timezone": geo.timezone,
        }
    )


def _location_name(geo) -> str:
    area = geo.county_or_district or geo.state_or_region or geo.country or "this location"
    if geo.county_or_district and geo.state_or_region:
        return f"{geo.county_or_district}, {geo.state_or_region}"
    return area


def _measurement_report(measurement: dict, *, decimals: int | None = None) -> dict:
    if not isinstance(measurement, dict) or not measurement:
        return {"status": "unavailable"}
    value = measurement.get("value")
    if value is None:
        return {"status": "unavailable"}
    if isinstance(value, float) and decimals is not None:
        value = round(value, decimals)
    return _strip_none(
        {
            "status": "available",
            "value": value,
            "unit": measurement.get("unit"),
            "evidence_type": measurement.get("evidence_type"),
            "parameter": measurement.get("parameter"),
        }
    )


def _wind_report(wind: dict) -> dict:
    if not isinstance(wind, dict) or not wind:
        return {"status": "unavailable"}
    speed = wind.get("speed")
    direction = wind.get("direction")
    if speed is None and direction is None:
        return {"status": "unavailable"}
    return _strip_none({"status": "available", "speed": speed, "direction": direction, "unit": wind.get("unit"), "evidence_type": wind.get("evidence_type")})


def _context_status_report(context: dict) -> dict:
    if not isinstance(context, dict) or not context:
        return {"status": "unavailable"}
    status = str(context.get("status") or "").upper()
    if status in {"UNAVAILABLE", "DENIED", "FAILED", "PROVIDER_ERROR"}:
        return _strip_none({"status": "unavailable", "reason": context.get("semantic_note") or context.get("denial_reason") or status.lower()})
    if "map_unit" in context:
        return _strip_none({"status": "available", "map_unit": context.get("map_unit"), "semantic_note": context.get("semantic_note")})
    return _strip_none({"status": "available", "summary": context.get("semantic_note") or context.get("summary")})


def _render_environment_report(report: dict) -> str:
    location = report.get("location", {})
    lines = [f"Current growing conditions for {location.get('label') or 'this location'}:", ""]
    lines.append(f"Temperature: {_measurement_line(report.get('temperature'))}")
    lines.append(f"Rain chance: {_measurement_line(report.get('precipitation_probability'))}")
    lines.append(f"Wind: {_wind_line(report.get('wind'))}")
    lines.append(f"Day length: {_photoperiod_line(report.get('photoperiod'))}")
    lines.append(f"Humidity: {_measurement_line(report.get('humidity'))}")
    lines.append(f"Solar radiation: {_measurement_line(report.get('solar_radiation'))}")
    lines.append(f"Soil moisture: {_context_line(report.get('soil_moisture_context'))}")
    lines.append(f"Soil context: {_context_line(report.get('soil_context'))}")
    lines.append(f"Water context: {_context_line(report.get('water_context'))}")
    constraint = _environment_constraint(report)
    if constraint:
        lines.extend(["", constraint])
    return "\n".join(lines)


def _measurement_line(measurement: dict | None) -> str:
    if not isinstance(measurement, dict) or measurement.get("status") != "available":
        return "unavailable"
    value = measurement.get("value")
    unit = measurement.get("unit")
    return f"{value} {unit}".strip()


def _wind_line(wind: dict | None) -> str:
    if not isinstance(wind, dict) or wind.get("status") != "available":
        return "unavailable"
    direction = wind.get("direction")
    speed = wind.get("speed")
    if direction and speed:
        return f"{direction} at {speed}"
    return str(speed or direction)


def _photoperiod_line(measurement: dict | None) -> str:
    if not isinstance(measurement, dict) or measurement.get("status") != "available":
        return "unavailable"
    return f"about {_measurement_line(measurement)}"


def _context_line(context: dict | None) -> str:
    if not isinstance(context, dict) or context.get("status") != "available":
        return "unavailable"
    return str(context.get("map_unit") or context.get("summary") or context.get("semantic_note") or "available")


def _environment_constraint(report: dict) -> str | None:
    temperature = report.get("temperature", {})
    value = temperature.get("value") if isinstance(temperature, dict) else None
    unit = str(temperature.get("unit") or "").upper() if isinstance(temperature, dict) else ""
    if isinstance(value, (int, float)) and ((unit == "F" and value >= 90) or (unit == "C" and value >= 32)):
        return "The heat is the main immediate growing constraint."
    return None


def _strip_none(value):
    if isinstance(value, dict):
        return {key: _strip_none(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [_strip_none(item) for item in value if item is not None]
    return value


def _measurement_text(measurement: dict) -> str:
    if not measurement:
        return "unavailable"
    value = measurement.get("value")
    unit = measurement.get("unit")
    evidence_type = measurement.get("evidence_type")
    if value is None:
        return "unavailable"
    return f"{value} {unit or ''} ({evidence_type or 'unknown evidence'}).".strip()


def _primary_claim(draft: dict) -> str:
    recommendations = draft.get("recommendations") or []
    if recommendations and isinstance(recommendations[0], dict):
        return str(recommendations[0].get("summary") or draft["subject"])
    return str(draft["subject"])


def _render_guidance_plan(plan: GuidancePlan) -> str:
    first_recommendation = plan.recommendations[0] if plan.recommendations else {}
    summary = first_recommendation.get("summary") if isinstance(first_recommendation, dict) else str(first_recommendation)
    action = plan.actions[0].get("title") if plan.actions and isinstance(plan.actions[0], dict) else "Review the plan details."
    return f"{plan.subject}: {summary}\nAction: {action}\nConfidence: {plan.uncertainty.get('level', 'uncertain')}"


def _location_qualifier(location: dict) -> str:
    source_kind = str(location.get("source_kind") or "saved")
    label = str(location.get("label") or "location")
    if source_kind == "device":
        return f"Your device-approved location ({label})"
    if source_kind == "manual":
        return f"Your manually entered location ({label})"
    if source_kind == "demo_fixture" or location.get("is_demo"):
        return f"Your selected demo fixture location ({label}), not current device location,"
    return f"Your selected saved location ({label})"
