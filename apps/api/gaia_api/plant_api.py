from __future__ import annotations

from dataclasses import asdict

from packages.botany import BotanistService
from packages.domain import Observation, UserPlant
from packages.domain.models import now_iso
from packages.persistence import GaiaRepository
from packages.tools import ToolExecutionContext


async def get_plants(repository: GaiaRepository, context: ToolExecutionContext) -> list[dict]:
    return repository.list_user_plants(context.organization_id, context.workspace_id)


async def post_plant(
    repository: GaiaRepository,
    botanist: BotanistService,
    context: ToolExecutionContext,
    *,
    taxon_query: str,
    nickname: str,
    cultivar: str | None = None,
    planted_at: str | None = None,
    acquired_at: str | None = None,
    lifecycle_stage: str = "unknown",
    location_id: str | None = None,
    growing_method: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    lookup = await botanist.resolve_taxon(context, taxon_query)
    if lookup.plant_entity is None:
        return {"status": lookup.status, "warnings": lookup.warnings, "alternatives": lookup.data.get("alternatives", [])}
    profile = botanist.build_plant_profile(context.organization_id, lookup.plant_entity)
    user_plant = repository.create_user_plant(
        UserPlant(
            organization_id=context.organization_id,
            workspace_id=context.workspace_id,
            plant_entity_id=lookup.plant_entity.id,
            nickname=nickname,
            cultivar=cultivar,
            planted_at=planted_at,
            acquired_at=acquired_at,
            lifecycle_stage=lifecycle_stage,
            location_id=location_id,
            growing_method=growing_method,
            tags=tags or [],
        )
    )
    return {
        "status": "created",
        "plant": asdict(user_plant),
        "plant_entity": asdict(lookup.plant_entity),
        "plant_profile": asdict(profile),
        "source_record_ids": lookup.source_record_ids,
    }


async def get_plant(repository: GaiaRepository, context: ToolExecutionContext, user_plant_id: str) -> dict | None:
    plant = repository.get_user_plant(context.organization_id, user_plant_id)
    if plant is None:
        return None
    entity = repository.get_plant_entity(plant["plant_entity_id"])
    profile = repository.get_latest_plant_profile(context.organization_id, plant["plant_entity_id"])
    latest = repository.list_observations(context.organization_id, user_plant_id)[:1]
    return {"plant": plant, "plant_entity": entity, "plant_profile": profile, "last_observation": latest[0] if latest else None}


async def patch_plant(repository: GaiaRepository, context: ToolExecutionContext, user_plant_id: str, updates: dict) -> dict | None:
    plant = repository.get_user_plant(context.organization_id, user_plant_id)
    if plant is None:
        return None
    allowed = {"nickname", "cultivar", "lifecycle_stage", "container_or_bed", "growing_method", "notes", "tags", "status"}
    for key, value in updates.items():
        if key not in allowed:
            continue
        repository.connection.execute(
            f"UPDATE user_plants SET {key} = ?, updated_at = ? WHERE organization_id = ? AND id = ? AND deleted_at IS NULL",
            (_json_if_needed(value), now_iso(), context.organization_id, user_plant_id),
        )
    repository.connection.commit()
    return repository.get_user_plant(context.organization_id, user_plant_id)


async def delete_plant(repository: GaiaRepository, context: ToolExecutionContext, user_plant_id: str) -> bool:
    return repository.soft_delete("user_plants", context.organization_id, user_plant_id)


async def post_observation(
    repository: GaiaRepository,
    context: ToolExecutionContext,
    user_plant_id: str,
    *,
    text: str,
    observed_facts: list[dict] | None = None,
    gaia_inferences: list[dict] | None = None,
    lifecycle_stage_observed: str | None = None,
    health_tags: list[str] | None = None,
    measurements: dict | None = None,
    attachment_references: list[str] | None = None,
    environmental_snapshot_id: str | None = None,
) -> dict:
    observation = repository.create_observation(
        Observation(
            organization_id=context.organization_id,
            workspace_id=context.workspace_id,
            user_plant_id=user_plant_id,
            author_id=context.user_id,
            text=text,
            images=attachment_references or [],
            measurements=measurements or {},
            weather_snapshot_id=environmental_snapshot_id,
            observed_facts=observed_facts or [],
            gaia_inferences=gaia_inferences or [],
            lifecycle_stage_observed=lifecycle_stage_observed,
            health_tags=health_tags or [],
        )
    )
    return asdict(observation)


async def get_observations(repository: GaiaRepository, context: ToolExecutionContext, user_plant_id: str) -> list[dict]:
    return repository.list_observations(context.organization_id, user_plant_id)


async def get_taxa_search(botanist: BotanistService, context: ToolExecutionContext, query: str) -> dict:
    lookup = await botanist.resolve_taxon(context, query)
    return {
        "status": lookup.status,
        "plant_entity": asdict(lookup.plant_entity) if lookup.plant_entity else None,
        "alternatives": lookup.data.get("alternatives", []),
        "warnings": lookup.warnings,
        "source_record_ids": lookup.source_record_ids,
    }


async def get_taxon(repository: GaiaRepository, plant_entity_id: str) -> dict | None:
    return repository.get_plant_entity(plant_entity_id)


async def get_germplasm_search(botanist: BotanistService, context: ToolExecutionContext, query: str, *, limit: int = 10) -> dict:
    result = await botanist.search_germplasm(context, query, limit=limit)
    return result.data


def _json_if_needed(value):
    import json

    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return value
