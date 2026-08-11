from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

from packages.domain import (
    Action,
    CalendarBinding,
    Conversation,
    EnvironmentalSnapshot,
    EvidenceClaim,
    GeoContext,
    GuidancePlan,
    Location,
    MediaAttachment,
    Message,
    Membership,
    ModelRun,
    MovementCheck,
    MovementDecision,
    MovementRequest,
    Observation,
    Organization,
    Outcome,
    PlantEntity,
    PlantProfile,
    PromptHarness,
    RegulationRule,
    ResearchAnnotation,
    ResearchAuthor,
    ResearchClaim,
    ResearchCollection,
    ResearchWork,
    SeasonPlan,
    User,
    UserPlant,
    VisualAnalysis,
    Workspace,
    EvidenceSynthesis,
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
                id, organization_id, location_id, generated_at, country, country_code,
                state_or_region, state_code, county_or_district, county_fips, timezone,
                elevation_m, hardiness_zone, ecoregion, watershed, climate_zone,
                regulatory_zones, quarantine_zones, pest_zones,
                economic_regions, source_record_ids, retention_policy, created_at, updated_at, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                geo_context.id,
                geo_context.organization_id,
                geo_context.location_id,
                geo_context.generated_at,
                geo_context.country,
                geo_context.country_code,
                geo_context.state_or_region,
                geo_context.state_code,
                geo_context.county_or_district,
                geo_context.county_fips,
                geo_context.timezone,
                geo_context.elevation_m,
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
        values = asdict(plant_entity)
        for key in ["common_names", "synonyms", "external_source_ids", "source_ids", "retention_policy"]:
            values[key] = _json(values[key])
        self._insert_from_dict("plant_entities", values)
        return plant_entity

    def create_user_plant(self, user_plant: UserPlant) -> UserPlant:
        self._require_workspace(user_plant.organization_id, user_plant.workspace_id)
        self._require_plant_entity(user_plant.plant_entity_id)
        if user_plant.location_id is not None:
            self._require_location(user_plant.organization_id, user_plant.location_id)
        values = asdict(user_plant)
        for key in ["tags", "retention_policy"]:
            values[key] = _json(values[key])
        self._insert_from_dict("user_plants", values)
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
            "forecast",
            "solar_radiation",
            "photoperiod",
            "solar_context",
            "soil_context",
            "soil_moisture_context",
            "drought_context",
            "water_context",
            "season_context",
            "astronomical_context",
            "provider_statuses",
            "source_record_ids",
            "retention_policy",
        ]:
            values[key] = _json(values[key])
        self._insert_from_dict("environmental_snapshots", values)
        return snapshot

    def create_observation(self, observation: Observation) -> Observation:
        self._require_workspace(observation.organization_id, observation.workspace_id)
        self._require_user_plant(observation.organization_id, observation.user_plant_id)
        values = asdict(observation)
        for key in [
            "images",
            "audio",
            "video",
            "measurements",
            "observed_facts",
            "gaia_inferences",
            "health_tags",
            "retention_policy",
        ]:
            values[key] = _json(values[key])
        self._insert_from_dict("observations", values)
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

    def create_visual_analysis(self, visual_analysis: VisualAnalysis) -> VisualAnalysis:
        self._require_workspace(visual_analysis.organization_id, visual_analysis.workspace_id)
        self._require_media_attachment(visual_analysis.organization_id, visual_analysis.media_attachment_id)
        if visual_analysis.user_plant_id is not None:
            self._require_user_plant(visual_analysis.organization_id, visual_analysis.user_plant_id)
        if visual_analysis.geo_context_id is not None:
            self._require_geo_context(visual_analysis.organization_id, visual_analysis.geo_context_id)
        if visual_analysis.environmental_snapshot_id is not None:
            self._require_environmental_snapshot(visual_analysis.organization_id, visual_analysis.environmental_snapshot_id)
        if visual_analysis.model_run_id is not None:
            self._require_model_run(visual_analysis.organization_id, visual_analysis.model_run_id)
        values = asdict(visual_analysis)
        for key in [
            "image_quality",
            "plant_candidates",
            "visual_observations",
            "visual_hypotheses",
            "required_next_evidence",
            "botanist_context",
            "source_record_ids",
            "safety_notes",
            "retention_policy",
        ]:
            values[key] = _json(values[key])
        self._insert_from_dict("visual_analyses", values)
        return visual_analysis

    def create_plant_profile(self, plant_profile: PlantProfile) -> PlantProfile:
        self._require_organization(plant_profile.organization_id)
        self._require_plant_entity(plant_profile.plant_entity_id)
        values = asdict(plant_profile)
        for key in [
            "taxonomy",
            "common_names",
            "temperature_context",
            "water_context",
            "soil_context",
            "light_context",
            "season_context",
            "known_pest_links",
            "known_disease_links",
            "germplasm_links",
            "field_provenance",
            "conflicts",
            "source_record_ids",
            "confidence",
            "retention_policy",
        ]:
            values[key] = _json(values[key])
        self._insert_from_dict("plant_profiles", values)
        return plant_profile

    def create_source_record(self, source_record: SourceRecord) -> SourceRecord:
        if source_record.organization_id is not None:
            self._require_organization(source_record.organization_id)
        values = asdict(source_record)
        values["retention_policy"] = _json(values["retention_policy"])
        self._insert_from_dict("source_records", values)
        return source_record

    def create_research_author(self, author: ResearchAuthor) -> ResearchAuthor:
        values = asdict(author)
        for key in ["source_record_ids", "retention_policy"]:
            values[key] = _json(values[key])
        self._insert_from_dict("research_authors", values)
        return author

    def upsert_research_work(self, work: ResearchWork) -> ResearchWork:
        existing = self.find_research_work(doi=work.doi, pmid=work.pmid, pmcid=work.pmcid, provider_ids=work.provider_ids)
        if existing is not None:
            return ResearchWork(
                id=existing["id"],
                title=existing["title"],
                abstract=existing.get("abstract"),
                publication_year=existing.get("publication_year"),
                journal=existing.get("journal"),
                doi=existing.get("doi"),
                pmid=existing.get("pmid"),
                pmcid=existing.get("pmcid"),
                provider_ids=existing.get("provider_ids", {}),
                publication_types=existing.get("publication_types", []),
                open_access_status=existing.get("open_access_status", "unknown"),
                retracted_status=existing.get("retracted_status", "unknown"),
                study_type=existing.get("study_type", "unknown"),
                authors=existing.get("authors", []),
                evidence_policy=existing.get("evidence_policy", {}),
                source_record_ids=existing.get("source_record_ids", []),
                retention_policy=existing.get("retention_policy", {}),
                created_at=existing["created_at"],
                updated_at=existing["updated_at"],
                deleted_at=existing.get("deleted_at"),
            )
        values = asdict(work)
        for key in ["provider_ids", "publication_types", "authors", "evidence_policy", "source_record_ids", "retention_policy"]:
            values[key] = _json(values[key])
        self._insert_from_dict("research_works", values)
        return work

    def create_research_claim(self, claim: ResearchClaim) -> ResearchClaim:
        self._require_organization(claim.organization_id)
        values = asdict(claim)
        for key in ["source_work_ids", "source_record_ids", "limitations", "applicability", "retention_policy"]:
            values[key] = _json(values[key])
        self._insert_from_dict("research_claims", values)
        return claim

    def create_evidence_synthesis(self, synthesis: EvidenceSynthesis) -> EvidenceSynthesis:
        self._require_workspace(synthesis.organization_id, synthesis.workspace_id)
        for model_run_id in synthesis.model_run_ids:
            self._require_model_run(synthesis.organization_id, model_run_id)
        values = asdict(synthesis)
        for key in [
            "scope",
            "supporting_claims",
            "contradictory_claims",
            "uncertain_claims",
            "uncertainty",
            "applicability",
            "source_work_ids",
            "source_record_ids",
            "model_run_ids",
            "export_payload",
            "retention_policy",
        ]:
            values[key] = _json(values[key])
        self._insert_from_dict("evidence_syntheses", values)
        return synthesis

    def create_research_collection(self, collection: ResearchCollection) -> ResearchCollection:
        self._require_workspace(collection.organization_id, collection.workspace_id)
        values = asdict(collection)
        for key in ["work_ids", "retention_policy"]:
            values[key] = _json(values[key])
        self._insert_from_dict("research_collections", values)
        return collection

    def create_research_annotation(self, annotation: ResearchAnnotation) -> ResearchAnnotation:
        self._require_workspace(annotation.organization_id, annotation.workspace_id)
        if annotation.collection_id is not None:
            self._require_research_collection(annotation.organization_id, annotation.collection_id)
        self._require_research_work(annotation.work_id)
        self._require_membership(annotation.organization_id, annotation.author_id)
        values = asdict(annotation)
        values["private"] = 1 if annotation.private else 0
        for key in ["tags", "retention_policy"]:
            values[key] = _json(values[key])
        self._insert_from_dict("research_annotations", values)
        return annotation

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
        if guidance_plan.conversation_id is not None:
            self._require_conversation(guidance_plan.organization_id, guidance_plan.conversation_id)
        if guidance_plan.user_plant_id is not None:
            self._require_user_plant(guidance_plan.organization_id, guidance_plan.user_plant_id)
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

    def create_movement_request(self, movement_request: MovementRequest) -> MovementRequest:
        self._require_workspace(movement_request.organization_id, movement_request.workspace_id)
        if movement_request.origin_location_id is not None:
            self._require_location(movement_request.organization_id, movement_request.origin_location_id)
        if movement_request.destination_location_id is not None:
            self._require_location(movement_request.organization_id, movement_request.destination_location_id)
        values = asdict(movement_request)
        values["live_plant"] = 1 if movement_request.live_plant else 0
        values["soil_attached"] = 1 if movement_request.soil_attached else 0
        for key in ["metadata", "retention_policy"]:
            values[key] = _json(values[key])
        self._insert_from_dict("movement_requests", values)
        return movement_request

    def create_movement_decision(self, movement_decision: MovementDecision) -> MovementDecision:
        self._require_workspace(movement_decision.organization_id, movement_decision.workspace_id)
        self._require_movement_request(movement_decision.organization_id, movement_decision.movement_request_id)
        for model_run_id in movement_decision.model_run_ids:
            self._require_model_run(movement_decision.organization_id, model_run_id)
        values = asdict(movement_decision)
        for key in [
            "applicable_jurisdictions",
            "applicable_rules",
            "conditions",
            "permit_requirements",
            "treatment_requirements",
            "inspection_requirements",
            "reporting_requirements",
            "unresolved_questions",
            "conflicts",
            "source_record_ids",
            "model_run_ids",
            "retention_policy",
        ]:
            values[key] = _json(values[key])
        self._insert_from_dict("movement_decisions", values)
        return movement_decision

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

    def create_prompt_harness(self, prompt_harness: PromptHarness) -> PromptHarness:
        values = asdict(prompt_harness)
        values["active"] = 1 if prompt_harness.active else 0
        for key in ["model_compatibility", "output_schema", "retention_policy"]:
            values[key] = _json(values[key])
        self._insert_from_dict("prompt_harnesses", values)
        return prompt_harness

    def upsert_prompt_harness(self, prompt_harness: PromptHarness) -> PromptHarness:
        existing = self.connection.execute(
            """
            SELECT id FROM prompt_harnesses
            WHERE prompt_id = ? AND semantic_version = ? AND prompt_hash = ?
            """,
            (prompt_harness.prompt_id, prompt_harness.semantic_version, prompt_harness.prompt_hash),
        ).fetchone()
        if existing is not None:
            return prompt_harness
        return self.create_prompt_harness(prompt_harness)

    def create_conversation(self, conversation: Conversation) -> Conversation:
        self._require_workspace(conversation.organization_id, conversation.workspace_id)
        self._require_membership(conversation.organization_id, conversation.user_id)
        if conversation.location_id is not None:
            self._require_location(conversation.organization_id, conversation.location_id)
        if conversation.user_plant_id is not None:
            self._require_user_plant(conversation.organization_id, conversation.user_plant_id)
        values = asdict(conversation)
        values["retention_policy"] = _json(values["retention_policy"])
        self._insert_from_dict("conversations", values)
        return conversation

    def create_message(self, message: Message) -> Message:
        self._require_conversation(message.organization_id, message.conversation_id)
        if message.model_run_id is not None:
            self._require_model_run(message.organization_id, message.model_run_id)
        if message.guidance_plan_id is not None:
            self._require_guidance_plan(message.organization_id, message.guidance_plan_id)
        values = asdict(message)
        for key in ["source_record_ids", "metadata", "retention_policy"]:
            values[key] = _json(values[key])
        self._insert_from_dict("messages", values)
        self.connection.execute(
            """
            UPDATE conversations
            SET last_message_at = ?, updated_at = ?
            WHERE organization_id = ? AND id = ? AND deleted_at IS NULL
            """,
            (message.created_at, now_iso(), message.organization_id, message.conversation_id),
        )
        self.connection.commit()
        return message

    def get_workspace(self, organization_id: str, workspace_id: str) -> JsonDict | None:
        return self._get_tenant_row("workspaces", organization_id, workspace_id, ["knowledge_policy", "retention_policy"])

    def get_location(self, organization_id: str, location_id: str) -> JsonDict | None:
        return self._get_tenant_row("locations", organization_id, location_id, ["retention_policy"])

    def get_plant_entity(self, plant_entity_id: str) -> JsonDict | None:
        row = self.connection.execute(
            "SELECT * FROM plant_entities WHERE id = ? AND deleted_at IS NULL",
            (plant_entity_id,),
        ).fetchone()
        record = _row_to_dict(row)
        if record is None:
            return None
        return _decode_json_fields(record, ["common_names", "synonyms", "external_source_ids", "source_ids", "retention_policy"])

    def find_plant_entity_by_taxon_id(self, canonical_taxon_id: str) -> JsonDict | None:
        row = self.connection.execute(
            "SELECT * FROM plant_entities WHERE canonical_taxon_id = ? AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 1",
            (canonical_taxon_id,),
        ).fetchone()
        record = _row_to_dict(row)
        if record is None:
            return None
        return _decode_json_fields(record, ["common_names", "synonyms", "external_source_ids", "source_ids", "retention_policy"])

    def list_user_plants(self, organization_id: str, workspace_id: str) -> list[JsonDict]:
        self._require_workspace(organization_id, workspace_id)
        rows = self.connection.execute(
            """
            SELECT up.*, pe.scientific_name, pe.common_names
            FROM user_plants up
            JOIN plant_entities pe ON pe.id = up.plant_entity_id
            WHERE up.organization_id = ? AND up.workspace_id = ? AND up.deleted_at IS NULL
            ORDER BY up.created_at DESC, up.id
            """,
            (organization_id, workspace_id),
        ).fetchall()
        records = []
        for row in rows:
            record = dict(row)
            record = _decode_json_fields(record, ["tags", "common_names", "retention_policy"])
            records.append(record)
        return records

    def get_geo_context(self, organization_id: str, geo_context_id: str) -> JsonDict | None:
        return self._get_tenant_row(
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
        )

    def get_environmental_snapshot(self, organization_id: str, snapshot_id: str) -> JsonDict | None:
        return self._get_tenant_row(
            "environmental_snapshots",
            organization_id,
            snapshot_id,
            [
                "temperature",
                "humidity",
                "precipitation",
                "wind",
                "pressure",
                "forecast",
                "solar_radiation",
                "photoperiod",
                "solar_context",
                "soil_context",
                "soil_moisture_context",
                "drought_context",
                "water_context",
                "season_context",
                "astronomical_context",
                "provider_statuses",
                "source_record_ids",
                "retention_policy",
            ],
        )

    def get_user_plant(self, organization_id: str, user_plant_id: str) -> JsonDict | None:
        return self._get_tenant_row("user_plants", organization_id, user_plant_id, ["tags", "retention_policy"])

    def get_observation(self, organization_id: str, observation_id: str) -> JsonDict | None:
        return self._get_tenant_row(
            "observations",
            organization_id,
            observation_id,
            ["images", "audio", "video", "measurements", "observed_facts", "gaia_inferences", "health_tags", "retention_policy"],
        )

    def list_observations(self, organization_id: str, user_plant_id: str) -> list[JsonDict]:
        self._require_user_plant(organization_id, user_plant_id)
        rows = self.connection.execute(
            """
            SELECT * FROM observations
            WHERE organization_id = ? AND user_plant_id = ? AND deleted_at IS NULL
            ORDER BY observed_at DESC, id
            """,
            (organization_id, user_plant_id),
        ).fetchall()
        return [
            _decode_json_fields(
                dict(row),
                ["images", "audio", "video", "measurements", "observed_facts", "gaia_inferences", "health_tags", "retention_policy"],
            )
            for row in rows
        ]

    def get_latest_plant_profile(self, organization_id: str, plant_entity_id: str) -> JsonDict | None:
        row = self.connection.execute(
            """
            SELECT * FROM plant_profiles
            WHERE organization_id = ? AND plant_entity_id = ? AND deleted_at IS NULL
            ORDER BY version DESC, created_at DESC
            LIMIT 1
            """,
            (organization_id, plant_entity_id),
        ).fetchone()
        record = _row_to_dict(row)
        if record is None:
            return None
        return _decode_json_fields(
            record,
            [
                "taxonomy",
                "common_names",
                "temperature_context",
                "water_context",
                "soil_context",
                "light_context",
                "season_context",
                "known_pest_links",
                "known_disease_links",
                "germplasm_links",
                "field_provenance",
                "conflicts",
                "source_record_ids",
                "confidence",
                "retention_policy",
            ],
        )

    def get_media_attachment(self, organization_id: str, media_id: str) -> JsonDict | None:
        return self._get_tenant_row("media_attachments", organization_id, media_id, ["metadata", "retention_policy"])

    def get_visual_analysis(self, organization_id: str, visual_analysis_id: str) -> JsonDict | None:
        return self._get_tenant_row(
            "visual_analyses",
            organization_id,
            visual_analysis_id,
            [
                "image_quality",
                "plant_candidates",
                "visual_observations",
                "visual_hypotheses",
                "required_next_evidence",
                "botanist_context",
                "source_record_ids",
                "safety_notes",
                "retention_policy",
            ],
        )

    def list_visual_analyses_for_plant(self, organization_id: str, user_plant_id: str) -> list[JsonDict]:
        self._require_user_plant(organization_id, user_plant_id)
        rows = self.connection.execute(
            """
            SELECT * FROM visual_analyses
            WHERE organization_id = ? AND user_plant_id = ? AND deleted_at IS NULL
            ORDER BY created_at DESC, id
            """,
            (organization_id, user_plant_id),
        ).fetchall()
        return [
            _decode_json_fields(
                dict(row),
                [
                    "image_quality",
                    "plant_candidates",
                    "visual_observations",
                    "visual_hypotheses",
                    "required_next_evidence",
                    "botanist_context",
                    "source_record_ids",
                    "safety_notes",
                    "retention_policy",
                ],
            )
            for row in rows
        ]

    def get_research_work(self, work_id: str) -> JsonDict | None:
        row = self.connection.execute(
            "SELECT * FROM research_works WHERE id = ? AND deleted_at IS NULL",
            (work_id,),
        ).fetchone()
        record = _row_to_dict(row)
        if record is None:
            return None
        return _decode_json_fields(
            record,
            ["provider_ids", "publication_types", "authors", "evidence_policy", "source_record_ids", "retention_policy"],
        )

    def find_research_work(
        self,
        *,
        doi: str | None = None,
        pmid: str | None = None,
        pmcid: str | None = None,
        provider_ids: JsonDict | None = None,
    ) -> JsonDict | None:
        for column, value in [("doi", doi), ("pmid", pmid), ("pmcid", pmcid)]:
            if value:
                row = self.connection.execute(
                    f"SELECT * FROM research_works WHERE {column} = ? AND deleted_at IS NULL LIMIT 1",
                    (value,),
                ).fetchone()
                record = _row_to_dict(row)
                if record is not None:
                    return _decode_json_fields(
                        record,
                        ["provider_ids", "publication_types", "authors", "evidence_policy", "source_record_ids", "retention_policy"],
                    )
        for provider, external_id in (provider_ids or {}).items():
            if not external_id:
                continue
            rows = self.connection.execute("SELECT * FROM research_works WHERE deleted_at IS NULL").fetchall()
            for row in rows:
                record = _decode_json_fields(
                    dict(row),
                    ["provider_ids", "publication_types", "authors", "evidence_policy", "source_record_ids", "retention_policy"],
                )
                if record.get("provider_ids", {}).get(provider) == external_id:
                    return record
        return None

    def list_research_works(self, work_ids: list[str]) -> list[JsonDict]:
        works = []
        for work_id in work_ids:
            work = self.get_research_work(work_id)
            if work is not None:
                works.append(work)
        return works

    def get_evidence_synthesis(self, organization_id: str, synthesis_id: str) -> JsonDict | None:
        return self._get_tenant_row(
            "evidence_syntheses",
            organization_id,
            synthesis_id,
            [
                "scope",
                "supporting_claims",
                "contradictory_claims",
                "uncertain_claims",
                "uncertainty",
                "applicability",
                "source_work_ids",
                "source_record_ids",
                "model_run_ids",
                "export_payload",
                "retention_policy",
            ],
        )

    def get_movement_request(self, organization_id: str, movement_request_id: str) -> JsonDict | None:
        record = self._get_tenant_row("movement_requests", organization_id, movement_request_id, ["metadata", "retention_policy"])
        if record is not None:
            record["live_plant"] = bool(record["live_plant"])
            record["soil_attached"] = bool(record["soil_attached"])
        return record

    def get_movement_decision(self, organization_id: str, movement_decision_id: str) -> JsonDict | None:
        return self._get_tenant_row(
            "movement_decisions",
            organization_id,
            movement_decision_id,
            [
                "applicable_jurisdictions",
                "applicable_rules",
                "conditions",
                "permit_requirements",
                "treatment_requirements",
                "inspection_requirements",
                "reporting_requirements",
                "unresolved_questions",
                "conflicts",
                "source_record_ids",
                "model_run_ids",
                "retention_policy",
            ],
        )

    def list_movement_decisions_for_request(self, organization_id: str, movement_request_id: str) -> list[JsonDict]:
        self._require_movement_request(organization_id, movement_request_id)
        rows = self.connection.execute(
            """
            SELECT * FROM movement_decisions
            WHERE organization_id = ? AND movement_request_id = ? AND deleted_at IS NULL
            ORDER BY checked_at DESC, id
            """,
            (organization_id, movement_request_id),
        ).fetchall()
        return [
            _decode_json_fields(
                dict(row),
                [
                    "applicable_jurisdictions",
                    "applicable_rules",
                    "conditions",
                    "permit_requirements",
                    "treatment_requirements",
                    "inspection_requirements",
                    "reporting_requirements",
                    "unresolved_questions",
                    "conflicts",
                    "source_record_ids",
                    "model_run_ids",
                    "retention_policy",
                ],
            )
            for row in rows
        ]

    def get_research_collection(self, organization_id: str, collection_id: str) -> JsonDict | None:
        return self._get_tenant_row("research_collections", organization_id, collection_id, ["work_ids", "retention_policy"])

    def list_research_annotations(self, organization_id: str, workspace_id: str) -> list[JsonDict]:
        self._require_workspace(organization_id, workspace_id)
        rows = self.connection.execute(
            """
            SELECT * FROM research_annotations
            WHERE organization_id = ? AND workspace_id = ? AND deleted_at IS NULL
            ORDER BY created_at DESC, id
            """,
            (organization_id, workspace_id),
        ).fetchall()
        records = []
        for row in rows:
            record = dict(row)
            record["private"] = bool(record["private"])
            records.append(_decode_json_fields(record, ["tags", "retention_policy"]))
        return records

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

    def get_model_run(self, organization_id: str, model_run_id: str) -> JsonDict | None:
        return self._get_tenant_row(
            "model_runs",
            organization_id,
            model_run_id,
            ["input_modalities", "tool_calls", "retention_policy"],
        )

    def get_prompt_harness(self, prompt_id: str, semantic_version: str, prompt_hash: str) -> JsonDict | None:
        row = self.connection.execute(
            """
            SELECT * FROM prompt_harnesses
            WHERE prompt_id = ? AND semantic_version = ? AND prompt_hash = ? AND deleted_at IS NULL
            """,
            (prompt_id, semantic_version, prompt_hash),
        ).fetchone()
        record = _row_to_dict(row)
        if record is None:
            return None
        record["active"] = bool(record["active"])
        return _decode_json_fields(record, ["model_compatibility", "output_schema", "retention_policy"])

    def get_conversation(self, organization_id: str, conversation_id: str) -> JsonDict | None:
        return self._get_tenant_row("conversations", organization_id, conversation_id, ["retention_policy"])

    def list_conversations(self, organization_id: str, workspace_id: str) -> list[JsonDict]:
        self._require_workspace(organization_id, workspace_id)
        rows = self.connection.execute(
            """
            SELECT * FROM conversations
            WHERE organization_id = ? AND workspace_id = ? AND deleted_at IS NULL
            ORDER BY COALESCE(last_message_at, created_at) DESC, id
            """,
            (organization_id, workspace_id),
        ).fetchall()
        return [_decode_json_fields(dict(row), ["retention_policy"]) for row in rows]

    def list_messages(self, organization_id: str, conversation_id: str) -> list[JsonDict]:
        self._require_conversation(organization_id, conversation_id)
        rows = self.connection.execute(
            """
            SELECT * FROM messages
            WHERE organization_id = ? AND conversation_id = ? AND deleted_at IS NULL
            ORDER BY created_at, id
            """,
            (organization_id, conversation_id),
        ).fetchall()
        return [
            _decode_json_fields(dict(row), ["source_record_ids", "metadata", "retention_policy"])
            for row in rows
        ]

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
            "movement_requests",
            "movement_decisions",
            "season_plans",
            "calendar_bindings",
            "conversations",
            "messages",
            "plant_profiles",
            "visual_analyses",
            "research_claims",
            "evidence_syntheses",
            "research_collections",
            "research_annotations",
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
        if self.get_geo_context(organization_id, geo_context_id) is None:
            raise TenantAccessError("GeoContext is missing or inaccessible for this organization")

    def _require_environmental_snapshot(self, organization_id: str, snapshot_id: str) -> None:
        if self.get_environmental_snapshot(organization_id, snapshot_id) is None:
            raise TenantAccessError("EnvironmentalSnapshot is missing or inaccessible")

    def _require_user_plant(self, organization_id: str, user_plant_id: str) -> None:
        if self.get_user_plant(organization_id, user_plant_id) is None:
            raise TenantAccessError("UserPlant is missing or inaccessible for this organization")

    def _require_plant_entity(self, plant_entity_id: str) -> None:
        if self.get_plant_entity(plant_entity_id) is None:
            raise TenantAccessError("PlantEntity is missing or inaccessible")

    def _require_observation(self, organization_id: str, observation_id: str) -> None:
        if self.get_observation(organization_id, observation_id) is None:
            raise TenantAccessError("Observation is missing or inaccessible for this organization")

    def _require_media_attachment(self, organization_id: str, media_id: str) -> None:
        if self.get_media_attachment(organization_id, media_id) is None:
            raise TenantAccessError("MediaAttachment is missing or inaccessible for this organization")

    def _require_guidance_plan(self, organization_id: str, guidance_plan_id: str) -> None:
        if self.get_guidance_plan(organization_id, guidance_plan_id) is None:
            raise TenantAccessError("GuidancePlan is missing or inaccessible")

    def _require_conversation(self, organization_id: str, conversation_id: str) -> None:
        if self.get_conversation(organization_id, conversation_id) is None:
            raise TenantAccessError("Conversation is missing or inaccessible")

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
        if self.get_model_run(organization_id, model_run_id) is None:
            raise TenantAccessError("ModelRun is missing or inaccessible")

    def _require_research_work(self, work_id: str) -> None:
        if self.get_research_work(work_id) is None:
            raise TenantAccessError("ResearchWork is missing or inaccessible")

    def _require_research_collection(self, organization_id: str, collection_id: str) -> None:
        if self.get_research_collection(organization_id, collection_id) is None:
            raise TenantAccessError("ResearchCollection is missing or inaccessible")

    def _require_movement_request(self, organization_id: str, movement_request_id: str) -> None:
        if self.get_movement_request(organization_id, movement_request_id) is None:
            raise TenantAccessError("MovementRequest is missing or inaccessible")
