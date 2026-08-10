from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

from packages.domain import (
    Action,
    CalendarBinding,
    EnvironmentalSnapshot,
    EvidenceClaim,
    GeoContext,
    GuidancePlan,
    Location,
    MediaAttachment,
    Membership,
    ModelRun,
    MovementCheck,
    Observation,
    Organization,
    Outcome,
    PlantEntity,
    RegulationRule,
    SeasonPlan,
    User,
    UserPlant,
    Workspace,
    SourceRecord,
)
from packages.domain.models import now_iso


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = ROOT / "migrations"

JsonDict = dict[str, Any]


class TenantAccessError(PermissionError):
    pass


def connect_in_memory() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_schema(connection: sqlite3.Connection) -> None:
    for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
        connection.executescript(migration.read_text(encoding="utf-8"))
    connection.commit()


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _row_to_dict(row: sqlite3.Row | None) -> JsonDict | None:
    if row is None:
        return None
    return dict(row)


def _decode_json_fields(record: JsonDict, fields: Iterable[str]) -> JsonDict:
    for field in fields:
        if field in record and isinstance(record[field], str):
            record[field] = json.loads(record[field])
    return record


class GaiaRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create_organization(self, organization: Organization) -> Organization:
        self.connection.execute(
            """
            INSERT INTO organizations (
                id, name, slug, type, deployment_mode, default_country, default_units,
                data_retention_policy, retention_policy, created_at, updated_at, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization.id,
                organization.name,
                organization.slug,
                organization.type,
                organization.deployment_mode,
                organization.default_country,
                organization.default_units,
                _json(organization.data_retention_policy),
                _json(organization.retention_policy),
                organization.created_at,
                organization.updated_at,
                organization.deleted_at,
            ),
        )
        self.connection.commit()
        return organization

    def create_user(self, user: User) -> User:
        self.connection.execute(
            """
            INSERT INTO users (
                id, external_auth_id, display_name, locale, timezone, default_units,
                retention_policy, created_at, updated_at, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user.id,
                user.external_auth_id,
                user.display_name,
                user.locale,
                user.timezone,
                user.default_units,
                _json(user.retention_policy),
                user.created_at,
                user.updated_at,
                user.deleted_at,
            ),
        )
        self.connection.commit()
        return user

    def create_membership(self, membership: Membership) -> Membership:
        self.connection.execute(
            """
            INSERT INTO memberships (
                id, organization_id, user_id, role, permissions, retention_policy,
                created_at, updated_at, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                membership.id,
                membership.organization_id,
                membership.user_id,
                membership.role,
                _json(membership.permissions),
                _json(membership.retention_policy),
                membership.created_at,
                membership.updated_at,
                membership.deleted_at,
            ),
        )
        self.connection.commit()
        return membership

    def create_workspace(self, workspace: Workspace) -> Workspace:
        self._require_organization(workspace.organization_id)
        self.connection.execute(
            """
            INSERT INTO workspaces (
                id, organization_id, name, purpose, default_location_id, knowledge_policy,
                retention_policy, created_at, updated_at, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                workspace.id,
                workspace.organization_id,
                workspace.name,
                workspace.purpose,
                workspace.default_location_id,
                _json(workspace.knowledge_policy),
                _json(workspace.retention_policy),
                workspace.created_at,
                workspace.updated_at,
                workspace.deleted_at,
            ),
        )
        self.connection.commit()
        return workspace

    def create_location(self, location: Location) -> Location:
        self._require_organization(location.organization_id)
        self.connection.execute(
            """
            INSERT INTO locations (
                id, organization_id, label, latitude, longitude, elevation_m, accuracy_m,
                privacy_precision, exact_coordinates_authorized, timezone, country_code,
                admin1, admin2, county_fips, retention_policy, created_at, updated_at, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                location.id,
                location.organization_id,
                location.label,
                location.latitude,
                location.longitude,
                location.elevation_m,
                location.accuracy_m,
                location.privacy_precision,
                1 if location.exact_coordinates_authorized else 0,
                location.timezone,
                location.country_code,
                location.admin1,
                location.admin2,
                location.county_fips,
                _json(location.retention_policy),
                location.created_at,
                location.updated_at,
                location.deleted_at,
            ),
        )
        self.connection.commit()
        return location

    def create_geo_context(self, geo_context: GeoContext) -> GeoContext:
        self._require_location(geo_context.organization_id, geo_context.location_id)
        self.connection.execute(
            """
            INSERT INTO geo_contexts (
                id, organization_id, location_id, generated_at, country, state_or_region,
                county_or_district, county_fips, hardiness_zone, ecoregion, watershed,
                climate_zone, regulatory_zones, quarantine_zones, pest_zones,
                economic_regions, source_record_ids, retention_policy, created_at, updated_at, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                geo_context.id,
                geo_context.organization_id,
                geo_context.location_id,
                geo_context.generated_at,
                geo_context.country,
                geo_context.state_or_region,
                geo_context.county_or_district,
                geo_context.county_fips,
                geo_context.hardiness_zone,
                geo_context.ecoregion,
                geo_context.watershed,
                geo_context.climate_zone,
                _json(geo_context.regulatory_zones),
                _json(geo_context.quarantine_zones),
                _json(geo_context.pest_zones),
                _json(geo_context.economic_regions),
                _json(geo_context.source_record_ids),
                _json(geo_context.retention_policy),
                geo_context.created_at,
                geo_context.updated_at,
                geo_context.deleted_at,
            ),
        )
        self.connection.commit()
        return geo_context

    def create_plant_entity(self, plant_entity: PlantEntity) -> PlantEntity:
        self.connection.execute(
            """
            INSERT INTO plant_entities (
                id, scientific_name, canonical_taxon_id, common_names, family, genus,
                species, subspecies, cultivar_optional, crop_group, source_ids,
                retention_policy, created_at, updated_at, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plant_entity.id,
                plant_entity.scientific_name,
                plant_entity.canonical_taxon_id,
                _json(plant_entity.common_names),
                plant_entity.family,
                plant_entity.genus,
                plant_entity.species,
                plant_entity.subspecies,
                plant_entity.cultivar_optional,
                plant_entity.crop_group,
                _json(plant_entity.source_ids),
                _json(plant_entity.retention_policy),
                plant_entity.created_at,
                plant_entity.updated_at,
                plant_entity.deleted_at,
            ),
        )
        self.connection.commit()
        return plant_entity

    def create_user_plant(self, user_plant: UserPlant) -> UserPlant:
        self._require_workspace(user_plant.organization_id, user_plant.workspace_id)
        if user_plant.location_id is not None:
            self._require_location(user_plant.organization_id, user_plant.location_id)
        self.connection.execute(
            """
            INSERT INTO user_plants (
                id, organization_id, workspace_id, plant_entity_id, nickname, cultivar,
                planted_at, acquired_at, lifecycle_stage, location_id, container_or_bed,
                status, retention_policy, created_at, updated_at, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_plant.id,
                user_plant.organization_id,
                user_plant.workspace_id,
                user_plant.plant_entity_id,
                user_plant.nickname,
                user_plant.cultivar,
                user_plant.planted_at,
                user_plant.acquired_at,
                user_plant.lifecycle_stage,
                user_plant.location_id,
                user_plant.container_or_bed,
                user_plant.status,
                _json(user_plant.retention_policy),
                user_plant.created_at,
                user_plant.updated_at,
                user_plant.deleted_at,
            ),
        )
        self.connection.commit()
        return user_plant

    def create_environmental_snapshot(self, snapshot: EnvironmentalSnapshot) -> EnvironmentalSnapshot:
        self._require_location(snapshot.organization_id, snapshot.location_id)
        values = asdict(snapshot)
        for key in [
            "temperature",
            "humidity",
            "precipitation",
            "wind",
            "pressure",
            "solar_radiation",
            "photoperiod",
            "soil_context",
            "soil_moisture_context",
            "drought_context",
            "water_context",
            "source_record_ids",
            "retention_policy",
        ]:
            values[key] = _json(values[key])
        self._insert_from_dict("environmental_snapshots", values)
        return snapshot

    def create_observation(self, observation: Observation) -> Observation:
        self._require_workspace(observation.organization_id, observation.workspace_id)
        self._require_user_plant(observation.organization_id, observation.user_plant_id)
        self.connection.execute(
            """
            INSERT INTO observations (
                id, organization_id, workspace_id, user_plant_id, observed_at, author_id,
                text, images, audio, video, measurements, weather_snapshot_id, source,
                retention_policy, created_at, updated_at, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                observation.id,
                observation.organization_id,
                observation.workspace_id,
                observation.user_plant_id,
                observation.observed_at,
                observation.author_id,
                observation.text,
                _json(observation.images),
                _json(observation.audio),
                _json(observation.video),
                _json(observation.measurements),
                observation.weather_snapshot_id,
                observation.source,
                _json(observation.retention_policy),
                observation.created_at,
                observation.updated_at,
                observation.deleted_at,
            ),
        )
        self.connection.commit()
        return observation

    def create_media_attachment(self, media: MediaAttachment) -> MediaAttachment:
        self._require_workspace(media.organization_id, media.workspace_id)
        if media.observation_id is not None:
            self._require_observation(media.organization_id, media.observation_id)
        self.connection.execute(
            """
            INSERT INTO media_attachments (
                id, organization_id, workspace_id, observation_id, modality, storage_uri,
                content_type, byte_size, metadata, retention_policy, created_at, updated_at, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                media.id,
                media.organization_id,
                media.workspace_id,
                media.observation_id,
                media.modality,
                media.storage_uri,
                media.content_type,
                media.byte_size,
                _json(media.metadata),
                _json(media.retention_policy),
                media.created_at,
                media.updated_at,
                media.deleted_at,
            ),
        )
        self.connection.commit()
        return media

    def create_source_record(self, source_record: SourceRecord) -> SourceRecord:
        if source_record.organization_id is not None:
            self._require_organization(source_record.organization_id)
        values = asdict(source_record)
        values["retention_policy"] = _json(values["retention_policy"])
        self._insert_from_dict("source_records", values)
        return source_record

    def create_evidence_claim(self, evidence_claim: EvidenceClaim) -> EvidenceClaim:
        self._require_organization(evidence_claim.organization_id)
        values = asdict(evidence_claim)
        for key in ["source_record_ids", "contradictory_source_ids", "retention_policy"]:
            values[key] = _json(values[key])
        self._insert_from_dict("evidence_claims", values)
        return evidence_claim

    def create_model_run(self, model_run: ModelRun) -> ModelRun:
        self._require_organization(model_run.organization_id)
        values = asdict(model_run)
        for key in ["input_modalities", "tool_calls", "retention_policy"]:
            values[key] = _json(values[key])
        self._insert_from_dict("model_runs", values)
        return model_run

    def create_guidance_plan(self, guidance_plan: GuidancePlan) -> GuidancePlan:
        self._require_workspace(guidance_plan.organization_id, guidance_plan.workspace_id)
        if guidance_plan.geo_context_id is not None:
            self._require_geo_context(guidance_plan.organization_id, guidance_plan.geo_context_id)
        if guidance_plan.environmental_snapshot_id is not None:
            self._require_environmental_snapshot(
                guidance_plan.organization_id,
                guidance_plan.environmental_snapshot_id,
            )
        for evidence_claim_id in guidance_plan.evidence_claim_ids:
            self._require_evidence_claim(guidance_plan.organization_id, evidence_claim_id)
        for model_run_id in guidance_plan.model_run_ids:
            self._require_model_run(guidance_plan.organization_id, model_run_id)

        values = asdict(guidance_plan)
        for key in [
            "recommendations",
            "actions",
            "timing",
            "resources",
            "evidence_claim_ids",
            "risks",
            "uncertainty",
            "measurements_to_take",
            "follow_up",
            "model_run_ids",
            "retention_policy",
        ]:
            values[key] = _json(values[key])
        self._insert_from_dict("guidance_plans", values)

        for evidence_claim_id in guidance_plan.evidence_claim_ids:
            self.connection.execute(
                """
                INSERT INTO guidance_plan_evidence_claims
                    (guidance_plan_id, evidence_claim_id, organization_id)
                VALUES (?, ?, ?)
                """,
                (guidance_plan.id, evidence_claim_id, guidance_plan.organization_id),
            )
        for model_run_id in guidance_plan.model_run_ids:
            self.connection.execute(
                """
                INSERT INTO guidance_plan_model_runs
                    (guidance_plan_id, model_run_id, organization_id)
                VALUES (?, ?, ?)
                """,
                (guidance_plan.id, model_run_id, guidance_plan.organization_id),
            )
        self.connection.commit()
        return guidance_plan

    def create_action(self, action: Action) -> Action:
        self._require_guidance_plan(action.organization_id, action.guidance_plan_id)
        values = asdict(action)
        for key in ["dependencies", "retention_policy"]:
            values[key] = _json(values[key])
        self._insert_from_dict("actions", values)
        return action

    def create_outcome(self, outcome: Outcome) -> Outcome:
        self._require_action(outcome.organization_id, outcome.action_id)
        self._require_user_plant(outcome.organization_id, outcome.user_plant_id)
        values = asdict(outcome)
        for key in ["measurements", "attachments", "retention_policy"]:
            values[key] = _json(values[key])
        self._insert_from_dict("outcomes", values)
        return outcome

    def create_regulation_rule(self, regulation_rule: RegulationRule) -> RegulationRule:
        values = asdict(regulation_rule)
        for key in [
            "origin_scope",
            "destination_scope",
            "conditions",
            "permit_requirements",
            "treatment_requirements",
            "retention_policy",
        ]:
            values[key] = _json(values[key])
        self._insert_from_dict("regulation_rules", values)
        return regulation_rule

    def create_movement_check(self, movement_check: MovementCheck) -> MovementCheck:
        self._require_geo_context(movement_check.organization_id, movement_check.origin_geo_context_id)
        self._require_geo_context(movement_check.organization_id, movement_check.destination_geo_context_id)
        values = asdict(movement_check)
        for key in ["applicable_rule_ids", "caveats", "source_record_ids", "retention_policy"]:
            values[key] = _json(values[key])
        self._insert_from_dict("movement_checks", values)
        return movement_check

    def create_season_plan(self, season_plan: SeasonPlan) -> SeasonPlan:
        self._require_workspace(season_plan.organization_id, season_plan.workspace_id)
        if season_plan.location_id is not None:
            self._require_location(season_plan.organization_id, season_plan.location_id)
        values = asdict(season_plan)
        for key in [
            "crop_or_plant_ids",
            "date_range",
            "tasks",
            "climate_basis",
            "forecast_basis",
            "regulatory_constraints",
            "market_context",
            "retention_policy",
        ]:
            values[key] = _json(values[key])
        self._insert_from_dict("season_plans", values)
        return season_plan

    def create_calendar_binding(self, calendar_binding: CalendarBinding) -> CalendarBinding:
        self._require_membership(calendar_binding.organization_id, calendar_binding.user_id)
        values = asdict(calendar_binding)
        for key in ["scopes", "retention_policy"]:
            values[key] = _json(values[key])
        self._insert_from_dict("calendar_bindings", values)
        return calendar_binding

    def get_workspace(self, organization_id: str, workspace_id: str) -> JsonDict | None:
        return self._get_tenant_row("workspaces", organization_id, workspace_id, ["knowledge_policy", "retention_policy"])

    def get_user_plant(self, organization_id: str, user_plant_id: str) -> JsonDict | None:
        return self._get_tenant_row("user_plants", organization_id, user_plant_id, ["retention_policy"])

    def get_observation(self, organization_id: str, observation_id: str) -> JsonDict | None:
        return self._get_tenant_row(
            "observations",
            organization_id,
            observation_id,
            ["images", "audio", "video", "measurements", "retention_policy"],
        )

    def get_media_attachment(self, organization_id: str, media_id: str) -> JsonDict | None:
        return self._get_tenant_row("media_attachments", organization_id, media_id, ["metadata", "retention_policy"])

    def get_guidance_plan(self, organization_id: str, guidance_plan_id: str) -> JsonDict | None:
        return self._get_tenant_row(
            "guidance_plans",
            organization_id,
            guidance_plan_id,
            [
                "recommendations",
                "actions",
                "timing",
                "resources",
                "evidence_claim_ids",
                "risks",
                "uncertainty",
                "measurements_to_take",
                "follow_up",
                "model_run_ids",
                "retention_policy",
            ],
        )

    def get_action(self, organization_id: str, action_id: str) -> JsonDict | None:
        return self._get_tenant_row("actions", organization_id, action_id, ["dependencies", "retention_policy"])

    def guidance_plan_evidence_links(self, organization_id: str, guidance_plan_id: str) -> list[JsonDict]:
        rows = self.connection.execute(
            """
            SELECT guidance_plan_id, evidence_claim_id, organization_id
            FROM guidance_plan_evidence_claims
            WHERE organization_id = ? AND guidance_plan_id = ?
            ORDER BY evidence_claim_id
            """,
            (organization_id, guidance_plan_id),
        ).fetchall()
        return [dict(row) for row in rows]

    def update_workspace_name(self, organization_id: str, workspace_id: str, name: str) -> bool:
        result = self.connection.execute(
            """
            UPDATE workspaces
            SET name = ?, updated_at = ?
            WHERE organization_id = ? AND id = ? AND deleted_at IS NULL
            """,
            (name, now_iso(), organization_id, workspace_id),
        )
        self.connection.commit()
        return result.rowcount == 1

    def soft_delete(self, table: str, organization_id: str, entity_id: str) -> bool:
        allowed_tables = {
            "workspaces",
            "locations",
            "geo_contexts",
            "user_plants",
            "observations",
            "media_attachments",
            "environmental_snapshots",
            "evidence_claims",
            "guidance_plans",
            "model_runs",
            "actions",
            "outcomes",
            "movement_checks",
            "season_plans",
            "calendar_bindings",
        }
        if table not in allowed_tables:
            raise ValueError(f"Soft delete not supported for {table}")
        result = self.connection.execute(
            f"""
            UPDATE {table}
            SET deleted_at = ?, updated_at = ?
            WHERE organization_id = ? AND id = ? AND deleted_at IS NULL
            """,
            (now_iso(), now_iso(), organization_id, entity_id),
        )
        self.connection.commit()
        return result.rowcount == 1

    def _insert_from_dict(self, table: str, values: JsonDict) -> None:
        columns = list(values)
        placeholders = ", ".join("?" for _ in columns)
        column_sql = ", ".join(columns)
        self.connection.execute(
            f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})",
            tuple(values[column] for column in columns),
        )
        self.connection.commit()

    def _get_tenant_row(
        self,
        table: str,
        organization_id: str,
        entity_id: str,
        json_fields: Iterable[str],
    ) -> JsonDict | None:
        row = self.connection.execute(
            f"SELECT * FROM {table} WHERE organization_id = ? AND id = ? AND deleted_at IS NULL",
            (organization_id, entity_id),
        ).fetchone()
        record = _row_to_dict(row)
        if record is None:
            return None
        return _decode_json_fields(record, json_fields)

    def _require_organization(self, organization_id: str) -> None:
        row = self.connection.execute(
            "SELECT id FROM organizations WHERE id = ? AND deleted_at IS NULL",
            (organization_id,),
        ).fetchone()
        if row is None:
            raise TenantAccessError("Organization is missing or inaccessible")

    def _require_membership(self, organization_id: str, user_id: str) -> None:
        row = self.connection.execute(
            """
            SELECT id FROM memberships
            WHERE organization_id = ? AND user_id = ? AND deleted_at IS NULL
            """,
            (organization_id, user_id),
        ).fetchone()
        if row is None:
            raise TenantAccessError("Membership is missing or inaccessible for this organization")

    def _require_workspace(self, organization_id: str, workspace_id: str) -> None:
        if self.get_workspace(organization_id, workspace_id) is None:
            raise TenantAccessError("Workspace is missing or inaccessible for this organization")

    def _require_location(self, organization_id: str, location_id: str) -> None:
        if self._get_tenant_row("locations", organization_id, location_id, ["retention_policy"]) is None:
            raise TenantAccessError("Location is missing or inaccessible for this organization")

    def _require_geo_context(self, organization_id: str, geo_context_id: str) -> None:
        if self._get_tenant_row(
            "geo_contexts",
            organization_id,
            geo_context_id,
            [
                "regulatory_zones",
                "quarantine_zones",
                "pest_zones",
                "economic_regions",
                "source_record_ids",
                "retention_policy",
            ],
        ) is None:
            raise TenantAccessError("GeoContext is missing or inaccessible for this organization")

    def _require_environmental_snapshot(self, organization_id: str, snapshot_id: str) -> None:
        if self._get_tenant_row(
            "environmental_snapshots",
            organization_id,
            snapshot_id,
            [
                "temperature",
                "humidity",
                "precipitation",
                "wind",
                "pressure",
                "solar_radiation",
                "photoperiod",
                "soil_context",
                "soil_moisture_context",
                "drought_context",
                "water_context",
                "source_record_ids",
                "retention_policy",
            ],
        ) is None:
            raise TenantAccessError("EnvironmentalSnapshot is missing or inaccessible")

    def _require_user_plant(self, organization_id: str, user_plant_id: str) -> None:
        if self.get_user_plant(organization_id, user_plant_id) is None:
            raise TenantAccessError("UserPlant is missing or inaccessible for this organization")

    def _require_observation(self, organization_id: str, observation_id: str) -> None:
        if self.get_observation(organization_id, observation_id) is None:
            raise TenantAccessError("Observation is missing or inaccessible for this organization")

    def _require_guidance_plan(self, organization_id: str, guidance_plan_id: str) -> None:
        if self.get_guidance_plan(organization_id, guidance_plan_id) is None:
            raise TenantAccessError("GuidancePlan is missing or inaccessible")

    def _require_action(self, organization_id: str, action_id: str) -> None:
        if self.get_action(organization_id, action_id) is None:
            raise TenantAccessError("Action is missing or inaccessible")

    def _require_evidence_claim(self, organization_id: str, evidence_claim_id: str) -> None:
        if self._get_tenant_row(
            "evidence_claims",
            organization_id,
            evidence_claim_id,
            ["source_record_ids", "contradictory_source_ids", "retention_policy"],
        ) is None:
            raise TenantAccessError("EvidenceClaim is missing or inaccessible")

    def _require_model_run(self, organization_id: str, model_run_id: str) -> None:
        if self._get_tenant_row(
            "model_runs",
            organization_id,
            model_run_id,
            ["input_modalities", "tool_calls", "retention_policy"],
        ) is None:
            raise TenantAccessError("ModelRun is missing or inaccessible")
