from __future__ import annotations

from dataclasses import asdict

from packages.persistence import GaiaRepository
from packages.sentinel import SentinelService
from packages.tools import ToolExecutionContext


async def post_movement_check(
    sentinel: SentinelService,
    context: ToolExecutionContext,
    *,
    origin_location_id: str | None,
    destination_location_id: str | None,
    species: str | None,
    plant_part: str = "unknown",
    live_plant: bool = False,
    soil_attached: bool = False,
    planned_date: str | None = None,
    purpose: str | None = None,
    source_country: str | None = None,
    destination_country: str | None = None,
) -> dict:
    decision = await sentinel.check_movement(
        context,
        origin_location_id=origin_location_id,
        destination_location_id=destination_location_id,
        species=species,
        plant_part=plant_part,
        live_plant=live_plant,
        soil_attached=soil_attached,
        planned_date=planned_date,
        purpose=purpose,
        source_country=source_country,
        destination_country=destination_country,
    )
    return asdict(decision)


async def get_movement(repository: GaiaRepository, context: ToolExecutionContext, movement_decision_id: str) -> dict | None:
    return repository.get_movement_decision(context.organization_id, movement_decision_id)


async def get_active_regulations(repository: GaiaRepository, context: ToolExecutionContext) -> list[dict]:
    rows = repository.connection.execute(
        """
        SELECT * FROM regulation_rules
        WHERE deleted_at IS NULL
        ORDER BY jurisdiction_pack, authority, id
        """
    ).fetchall()
    return [dict(row) for row in rows]


async def get_regulation_zones(repository: GaiaRepository, context: ToolExecutionContext) -> list[dict]:
    rows = repository.connection.execute(
        """
        SELECT * FROM sentinel_zone_features
        WHERE deleted_at IS NULL
        ORDER BY jurisdiction_pack, zone_type, name
        """
    ).fetchall()
    return [dict(row) for row in rows]


async def get_pest_alerts(sentinel: SentinelService, context: ToolExecutionContext, *, species: str | None, location_id: str | None, visual_hypothesis: str) -> dict:
    decision = await sentinel.regulated_pest_context(context, species=species, location_id=location_id, visual_hypothesis=visual_hypothesis)
    return asdict(decision)

