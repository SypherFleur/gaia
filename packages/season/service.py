from __future__ import annotations

from packages.domain import Action, SeasonPlanRevision
from packages.model_gateway import ModelGateway, ModelMessage, ModelRequest
from packages.persistence import GaiaRepository
from packages.season.planner import DeterministicSeasonPlanner
from packages.season.types import SeasonContext, SeasonPlanRequest
from packages.tools import ToolExecutionContext


class SeasonService:
    def __init__(
        self,
        *,
        repository: GaiaRepository,
        planner: DeterministicSeasonPlanner | None = None,
        model_gateway: ModelGateway | None = None,
        model_provider_id: str = "ollama-local",
    ) -> None:
        self.repository = repository
        self.planner = planner or DeterministicSeasonPlanner()
        self.model_gateway = model_gateway
        self.model_provider_id = model_provider_id

    async def create_plan(
        self,
        context: ToolExecutionContext,
        request: SeasonPlanRequest,
        season_context: SeasonContext,
    ) -> tuple[object, list[Action], list[str]]:
        model_run_ids = []
        if request.use_model and self.model_gateway is not None:
            model_response = await self.model_gateway.generate(
                context,
                self.model_provider_id,
                ModelRequest(
                    messages=[
                        ModelMessage(role="system", content="You may summarize planning priorities, but deterministic Season code owns dates and actions."),
                        ModelMessage(role="user", content=f"Season objective: {request.objective}"),
                    ],
                    prompt_id="gaia.season_planning.v1",
                    prompt_version="0.1.0",
                    prompt_hash="season-planning-v1-fixture",
                    response_format="text",
                    contains_private_text=True,
                    contains_exact_location=False,
                    estimated_cost_usd=0.0,
                ),
            )
            if model_response.model_run_id:
                model_run_ids.append(model_response.model_run_id)
        plan, actions = await self.planner.create_plan(request, season_context)
        if model_run_ids:
            plan.planning_basis["model_run_ids"] = model_run_ids
        persisted_plan = self.repository.create_season_plan(plan)
        persisted_actions = [self.repository.create_action(action) for action in actions]
        return persisted_plan, persisted_actions, model_run_ids

    async def revise_plan(
        self,
        context: ToolExecutionContext,
        existing_plan_id: str,
        updated_context: SeasonContext,
    ) -> SeasonPlanRevision:
        raw = self.repository.get_season_plan(context.organization_id, existing_plan_id)
        if raw is None:
            raise PermissionError("SeasonPlan is missing or inaccessible")
        existing = _season_plan_from_raw(raw)
        existing.tasks = self.repository.list_actions_for_season_plan(context.organization_id, existing_plan_id)
        revision_payload = await self.planner.revise_plan(existing, updated_context)
        revision = SeasonPlanRevision(
            organization_id=context.organization_id,
            workspace_id=context.workspace_id,
            previous_plan_id=existing_plan_id,
            reason=revision_payload["reason"],
            changed_actions=revision_payload["changed_actions"],
            unchanged_actions=revision_payload["unchanged_actions"],
            context_change=revision_payload["context_change"],
        )
        return self.repository.create_season_plan_revision(revision)

    def complete_action(
        self,
        context: ToolExecutionContext,
        action_id: str,
        status: str,
        *,
        completed_at: str,
    ) -> bool:
        return self.repository.update_action_completion(context.organization_id, action_id, status, completed_at=completed_at)


def _season_plan_from_raw(raw: dict) -> object:
    from packages.domain import SeasonPlan

    return SeasonPlan(
        id=raw["id"],
        organization_id=raw["organization_id"],
        workspace_id=raw["workspace_id"],
        name=raw.get("name", ""),
        crop_or_plant_ids=raw.get("crop_or_plant_ids", []),
        objective=raw["objective"],
        location_id=raw.get("location_id"),
        start_date=raw.get("start_date"),
        end_date=raw.get("end_date"),
        date_range=raw.get("date_range", {}),
        tasks=raw.get("tasks", []),
        planning_basis=raw.get("planning_basis", {}),
        climate_basis=raw.get("climate_basis", {}),
        forecast_basis=raw.get("forecast_basis", {}),
        regulatory_constraints=raw.get("regulatory_constraints", []),
        market_context=raw.get("market_context", []),
        status=raw.get("status", "draft"),
        confidence=raw.get("confidence", "PROVISIONAL"),
        version=raw.get("version", 1),
        supersedes_plan_id=raw.get("supersedes_plan_id"),
        generated_at=raw["generated_at"],
        retention_policy=raw.get("retention_policy", {}),
        created_at=raw["created_at"],
        updated_at=raw["updated_at"],
        deleted_at=raw.get("deleted_at"),
    )
