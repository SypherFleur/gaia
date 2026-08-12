from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from packages.domain import Action, SeasonPlan
from packages.domain.models import now_iso
from packages.season.calculations import growing_degree_day, hemisphere, horizon_basis, local_midday_iso, next_available, parse_date
from packages.season.types import SeasonContext, SeasonPlanRequest


JsonDict = dict[str, Any]

DEFAULT_THRESHOLDS = {
    "tomato": {"base_c": 10.0, "min_transplant_c": 10.0, "heat_stress_c": 35.0, "days_to_harvest": 75},
    "pepper": {"base_c": 10.0, "min_transplant_c": 12.0, "heat_stress_c": 35.0, "days_to_harvest": 85},
    "collard": {"base_c": 4.0, "min_transplant_c": 2.0, "heat_stress_c": 29.0, "days_to_harvest": 65},
    "citrus": {"base_c": 12.0, "min_transplant_c": 4.0, "heat_stress_c": 38.0, "days_to_harvest": 180},
}


class DeterministicSeasonPlanner:
    async def create_plan(self, request: SeasonPlanRequest, context: SeasonContext) -> tuple[SeasonPlan, list[Action]]:
        generated_on = _planning_date(request.constraints)
        start = parse_date(request.start_date) if request.start_date else generated_on
        end = parse_date(request.end_date) if request.end_date else start + timedelta(days=120)
        unavailable = list(request.constraints.get("vacation_dates", [])) + list(request.constraints.get("unavailable_dates", []))
        crops = request.crop_names or [plant.get("nickname") or plant.get("scientific_name") or "crop" for plant in context.user_plants] or ["crop"]
        location = context.location or {}
        latitude = location.get("latitude")
        hemi = hemisphere(latitude)
        timing_basis = horizon_basis(start, generated_on)
        regulatory_constraints = [item for item in context.sentinel_constraints if item.get("status") in {"RESTRICTED", "UNRESOLVED"}]
        confidence = _confidence(context, request, regulatory_constraints)
        source_basis = _planning_basis(context, generated_on, timing_basis, hemi)
        plan = SeasonPlan(
            organization_id=str(context.workspace["organization_id"]),
            workspace_id=request.workspace_id,
            location_id=request.location_id,
            name=_plan_name(request.objective, start),
            objective=request.objective,
            crop_or_plant_ids=[*request.user_plant_ids, *crops],
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            date_range={"start": start.isoformat(), "end": end.isoformat(), "timezone": request.timezone},
            planning_basis=source_basis,
            climate_basis={"timing_basis": timing_basis, "hemisphere": hemi, "not_weather_forecast": timing_basis.startswith("climate") or timing_basis.startswith("climatological")},
            forecast_basis={"timing_basis": timing_basis, "forecast_used": timing_basis in {"forecast_execution", "forecast_influenced", "current_conditions_and_local_observations"}},
            regulatory_constraints=regulatory_constraints,
            tasks=[],
            status="draft",
            confidence=confidence,
            version=1,
            generated_at=now_iso(),
        )
        actions = []
        previous_transplant_id = None
        for index, crop in enumerate(crops):
            crop_key = _crop_key(crop)
            thresholds = DEFAULT_THRESHOLDS.get(crop_key, {"base_c": 8.0, "min_transplant_c": 8.0, "heat_stress_c": 33.0, "days_to_harvest": 70})
            crop_offset = timedelta(days=index * 2)
            bed_day = next_available(start + crop_offset, unavailable)
            transplant_day = next_available(start + timedelta(days=14 + index * 3), unavailable)
            forecast_adjustment = _forecast_adjustment(transplant_day, thresholds, context.weather_forecast_context)
            if forecast_adjustment is not None:
                transplant_day = next_available(transplant_day + timedelta(days=2), unavailable)
            harvest_day = min(end, transplant_day + timedelta(days=int(thresholds["days_to_harvest"])))
            bed = _action(
                plan,
                crop,
                "prepare_bed",
                f"Prepare bed for {crop}",
                "Prepare soil, verify amendments, and confirm irrigation access.",
                bed_day,
                request.timezone,
                basis=horizon_basis(bed_day, generated_on),
            )
            transplant = _action(
                plan,
                crop,
                "transplant",
                f"Transplant {crop}",
                f"Transplant within the recommended window only if overnight lows meet the crop threshold.",
                transplant_day,
                request.timezone,
                basis=horizon_basis(transplant_day, generated_on),
                dependencies=[bed.id] + ([previous_transplant_id] if previous_transplant_id and crop_key == "pepper" else []),
                weather_sensitive=True,
                environmental_conditions=[
                    {"condition": "overnight_low_c >=", "value": thresholds["min_transplant_c"], "source": "crop_threshold"},
                    {"condition": "heat_stress_c <=", "value": thresholds["heat_stress_c"], "source": "crop_threshold"},
                ],
            )
            if forecast_adjustment is not None:
                transplant.environmental_conditions.append(forecast_adjustment)
            scout = _action(
                plan,
                crop,
                "scout",
                f"Scout {crop}",
                "Inspect leaves, stems, and new growth. Record observations rather than treating unconfirmed symptoms as diagnoses.",
                transplant_day + timedelta(days=7),
                request.timezone,
                basis=horizon_basis(transplant_day + timedelta(days=7), generated_on),
                dependencies=[transplant.id],
                recurrence={"frequency": "weekly", "count": 4, "timezone": request.timezone},
            )
            moisture = _action(
                plan,
                crop,
                "water_check",
                f"Check {crop} moisture",
                "Check root-zone moisture before irrigating. Regional modeled moisture is not a field sensor reading.",
                transplant_day + timedelta(days=2),
                request.timezone,
                basis=horizon_basis(transplant_day + timedelta(days=2), generated_on),
                dependencies=[transplant.id],
                weather_sensitive=True,
                recurrence={"frequency": "every_2_days", "semantic": "check moisture, do not automatically water", "timezone": request.timezone},
            )
            harvest = _action(
                plan,
                crop,
                "harvest",
                f"Harvest window for {crop}",
                "Harvest timing is a window based on crop biology and observed maturity, not a guaranteed exact date.",
                harvest_day,
                request.timezone,
                basis=horizon_basis(harvest_day, generated_on),
                dependencies=[transplant.id],
            )
            actions.extend([bed, transplant, moisture, scout, harvest])
            previous_transplant_id = transplant.id
        if regulatory_constraints:
            actions.insert(
                0,
                _action(
                    plan,
                    "source",
                    "inspect_pest",
                    "Resolve regulated sourcing constraints",
                    "Do not acquire or move regulated plant material until Sentinel restrictions or unresolved questions are cleared.",
                    start,
                    request.timezone,
                    basis=timing_basis,
                    regulatory_conditions=regulatory_constraints,
                    user_confirmation_required=True,
                ),
            )
        if request.include_luna:
            plan.planning_basis["luna"] = {"phase": context.luna_context.get("phase", "unknown"), "influence_on_plan": "None", "evidence_status": "Experimental"}
        plan.tasks = [_task_payload(action) for action in actions]
        return plan, actions

    async def revise_plan(self, existing_plan: SeasonPlan, updated_context: SeasonContext) -> JsonDict:
        actions = list(existing_plan.tasks)
        changed = []
        unchanged = []
        heavy_rain_dates = set(updated_context.weather_forecast_context.get("heavy_rain_dates", []))
        for action in actions:
            preferred = str(action.get("preferred_at", ""))[:10]
            if action.get("weather_sensitive") and preferred in heavy_rain_dates:
                changed.append({**action, "reason": "heavy_rain_forecast", "proposed_preferred_at": _shift_iso(str(action["preferred_at"]), days=2)})
            else:
                unchanged.append(action)
        return {
            "reason": "context_changed",
            "changed_actions": changed,
            "unchanged_actions": unchanged,
            "context_change": {"weather_forecast_context": updated_context.weather_forecast_context},
        }


def _planning_date(constraints: JsonDict) -> date:
    if constraints.get("planning_date"):
        return parse_date(str(constraints["planning_date"]))
    return datetime.now(UTC).date()


def _plan_name(objective: str, start: date) -> str:
    title = objective.strip().rstrip(".")
    if len(title) > 60:
        title = title[:57].rstrip() + "..."
    return title or f"Season plan starting {start.isoformat()}"


def _crop_key(crop: str) -> str:
    text = crop.lower()
    if "tomato" in text or "lycopersicum" in text:
        return "tomato"
    if "pepper" in text:
        return "pepper"
    if "collard" in text:
        return "collard"
    if "citrus" in text:
        return "citrus"
    return text.split()[0] if text.split() else "crop"


def _confidence(context: SeasonContext, request: SeasonPlanRequest, regulatory_constraints: list[JsonDict]) -> str:
    if regulatory_constraints:
        return "PROVISIONAL"
    score = 0
    score += 1 if context.geo_context else 0
    score += 1 if context.environmental_snapshot else 0
    score += 1 if request.crop_names or context.crop_entities or context.user_plants else 0
    score += 1 if request.location_id else 0
    if request.constraints.get("cultivar_unknown"):
        score -= 1
    if score >= 4:
        return "HIGH"
    if score >= 2:
        return "MODERATE"
    return "LOW"


def _planning_basis(context: SeasonContext, generated_on: date, timing_basis: str, hemi: str) -> JsonDict:
    geo_sources = (context.geo_context or {}).get("source_record_ids", [])
    env_sources = (context.environmental_snapshot or {}).get("source_record_ids", [])
    regulatory_sources = [source for item in context.sentinel_constraints for source in item.get("source_record_ids", [])]
    research_sources = [source for item in context.scholar_evidence for source in item.get("source_record_ids", [])]
    return {
        "climate_sources": env_sources,
        "forecast_sources": env_sources if "forecast" in timing_basis else [],
        "plant_sources": [source for profile in context.plant_profiles for source in profile.get("source_record_ids", [])],
        "regulatory_sources": regulatory_sources,
        "research_sources": research_sources,
        "geo_sources": geo_sources,
        "context_timestamp": now_iso(),
        "generated_on": generated_on.isoformat(),
        "timing_basis": timing_basis,
        "hemisphere": hemi,
    }


def _action(
    plan: SeasonPlan,
    crop: str,
    action_type: str,
    title: str,
    instructions: str,
    day: date,
    timezone: str,
    *,
    basis: str,
    dependencies: list[str] | None = None,
    weather_sensitive: bool = False,
    environmental_conditions: list[JsonDict] | None = None,
    regulatory_conditions: list[JsonDict] | None = None,
    recurrence: JsonDict | None = None,
    user_confirmation_required: bool = False,
) -> Action:
    preferred = local_midday_iso(day, timezone)
    return Action(
        organization_id=plan.organization_id,
        season_plan_id=plan.id,
        plant_or_crop_id=crop,
        title=title,
        instructions=f"{instructions} Timing basis: {basis}.",
        action_type=action_type,
        earliest_at=local_midday_iso(day - timedelta(days=2), timezone),
        preferred_at=preferred,
        latest_at=local_midday_iso(day + timedelta(days=2), timezone),
        deadline=local_midday_iso(day + timedelta(days=2), timezone),
        duration_minutes=30,
        recurrence=recurrence or {},
        dependencies=dependencies or [],
        weather_sensitive=weather_sensitive,
        environmental_conditions=environmental_conditions or [],
        regulatory_conditions=regulatory_conditions or [],
        user_confirmation_required=user_confirmation_required,
        completion_status="NOT_STARTED",
    )


def _forecast_adjustment(day: date, thresholds: JsonDict, forecast: JsonDict) -> JsonDict | None:
    lows = forecast.get("daily_low_c", {})
    heavy_rain_dates = set(forecast.get("heavy_rain_dates", []))
    value = lows.get(day.isoformat())
    if value is not None and float(value) < float(thresholds["min_transplant_c"]):
        return {"condition": "forecast_low_below_threshold", "value": value, "action": "shift_or_protect"}
    if day.isoformat() in heavy_rain_dates:
        return {"condition": "heavy_rain_forecast", "action": "consider_revision"}
    return None


def _task_payload(action: Action) -> JsonDict:
    payload = asdict(action)
    payload["evidence_role"] = "season_action"
    return payload


def _shift_iso(value: str, *, days: int) -> str:
    dt = datetime.fromisoformat(value)
    return (dt + timedelta(days=days)).isoformat()


def season_gdd_summary(t_min_c: float, t_max_c: float, crop: str) -> JsonDict:
    key = _crop_key(crop)
    thresholds = DEFAULT_THRESHOLDS.get(key, {"base_c": 8.0})
    return {
        "crop": crop,
        "base_c": thresholds["base_c"],
        "gdd_c": growing_degree_day(t_min_c, t_max_c, float(thresholds["base_c"])),
        "formula": "max(((max(t_min, base) + t_max) / 2) - base, 0); upper clipping omitted unless crop config supplies it",
        "units": "C",
    }
