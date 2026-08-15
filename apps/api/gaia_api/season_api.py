from __future__ import annotations

from dataclasses import asdict

from packages.calendar_gateway import CalendarWorkflowService
from packages.season import SeasonContext, SeasonContextProvider, SeasonPlanRequest, SeasonService
from packages.tools import ToolExecutionContext


async def post_season_plan(
    season: SeasonService,
    context_provider: SeasonContextProvider,
    context: ToolExecutionContext,
    *,
    workspace_id: str,
    location_id: str | None,
    objective: str,
    crop_names: list[str],
    start_date: str | None,
    end_date: str | None,
    constraints: dict | None = None,
    timezone: str = "UTC",
    sentinel_constraints: list[dict] | None = None,
    scholar_evidence: list[dict] | None = None,
    weather_forecast_context: dict | None = None,
    use_model: bool = False,
    include_mercator: bool = False,
) -> dict:
    request = SeasonPlanRequest(
        workspace_id=workspace_id,
        location_id=location_id,
        objective=objective,
        crop_names=crop_names,
        start_date=start_date,
        end_date=end_date,
        constraints=constraints or {},
        timezone=timezone,
        use_model=use_model,
    )
    season_context = await context_provider.build(
        context,
        request,
        sentinel_constraints=sentinel_constraints,
        scholar_evidence=scholar_evidence,
        weather_forecast_context=weather_forecast_context,
        include_mercator=include_mercator,
    )
    plan, actions, model_run_ids = await season.create_plan(context, request, season_context)
    return {"season_plan": asdict(plan), "actions": [asdict(action) for action in actions], "model_run_ids": model_run_ids}


async def post_season_revision(
    season: SeasonService,
    context: ToolExecutionContext,
    *,
    season_plan_id: str,
    updated_context: SeasonContext,
) -> dict:
    revision = await season.revise_plan(context, season_plan_id, updated_context)
    return asdict(revision)


def post_calendar_preview(
    calendar: CalendarWorkflowService,
    context: ToolExecutionContext,
    *,
    season_plan_id: str,
    calendar_binding_id: str,
) -> dict:
    return asdict(calendar.preview_events(context, season_plan_id=season_plan_id, calendar_binding_id=calendar_binding_id))


async def post_calendar_commit(
    calendar: CalendarWorkflowService,
    context: ToolExecutionContext,
    *,
    preview_id: str,
) -> dict:
    return await calendar.commit_preview(context, preview_id=preview_id)
