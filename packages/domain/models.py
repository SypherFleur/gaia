from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4


JsonDict = dict[str, Any]

OrganizationType = Literal["personal", "community", "university", "government", "business", "ngo"]
MembershipRole = Literal["owner", "admin", "researcher", "extension_agent", "grower", "viewer"]
ObservationSource = Literal["user", "sensor", "imported"]
EvidenceGrade = Literal["A", "B", "C", "D", "E"]
MovementStatus = Literal["allowed", "conditional", "restricted", "unresolved"]
MediaModality = Literal["image", "audio", "video", "document_image"]
PrivacyPrecision = Literal["exact", "approximate", "100m", "1km", "county", "district", "custom"]


def new_id() -> str:
    return str(uuid4())


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class EntityMetadata:
    id: str = field(default_factory=new_id)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    deleted_at: str | None = None
    retention_policy: JsonDict = field(default_factory=dict)


@dataclass(slots=True)
class Organization(EntityMetadata):
    name: str = ""
    slug: str = ""
    type: OrganizationType = "personal"
    deployment_mode: str = "local"
    default_country: str = "US"
    default_units: str = "mixed"
    data_retention_policy: JsonDict = field(default_factory=dict)


@dataclass(slots=True)
class User(EntityMetadata):
    external_auth_id: str = ""
    display_name: str = ""
    locale: str = "en-US"
    timezone: str = "UTC"
    default_units: str = "mixed"


@dataclass(slots=True)
class Membership(EntityMetadata):
    organization_id: str = ""
    user_id: str = ""
    role: MembershipRole = "viewer"
    permissions: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Workspace(EntityMetadata):
    organization_id: str = ""
    name: str = ""
    purpose: str = ""
    default_location_id: str | None = None
    knowledge_policy: JsonDict = field(default_factory=dict)


@dataclass(slots=True)
class Location(EntityMetadata):
    organization_id: str = ""
    label: str = ""
    latitude: float | None = None
    longitude: float | None = None
    elevation_m: float | None = None
    accuracy_m: float | None = None
    privacy_precision: PrivacyPrecision = "approximate"
    exact_coordinates_authorized: bool = False
    timezone: str = "UTC"
    country_code: str = "US"
    admin1: str | None = None
    admin2: str | None = None
    county_fips: str | None = None


@dataclass(slots=True)
class GeoContext(EntityMetadata):
    organization_id: str = ""
    location_id: str = ""
    generated_at: str = field(default_factory=now_iso)
    country: str | None = None
    state_or_region: str | None = None
    county_or_district: str | None = None
    county_fips: str | None = None
    hardiness_zone: str | None = None
    ecoregion: str | None = None
    watershed: str | None = None
    climate_zone: str | None = None
    regulatory_zones: list[str] = field(default_factory=list)
    quarantine_zones: list[str] = field(default_factory=list)
    pest_zones: list[str] = field(default_factory=list)
    economic_regions: list[str] = field(default_factory=list)
    source_record_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PlantEntity(EntityMetadata):
    scientific_name: str = ""
    canonical_taxon_id: str | None = None
    common_names: list[str] = field(default_factory=list)
    family: str | None = None
    genus: str | None = None
    species: str | None = None
    subspecies: str | None = None
    cultivar_optional: str | None = None
    crop_group: str | None = None
    source_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class UserPlant(EntityMetadata):
    organization_id: str = ""
    workspace_id: str = ""
    plant_entity_id: str = ""
    nickname: str = ""
    cultivar: str | None = None
    planted_at: str | None = None
    acquired_at: str | None = None
    lifecycle_stage: str | None = None
    location_id: str | None = None
    container_or_bed: str | None = None
    status: str = "active"


@dataclass(slots=True)
class Observation(EntityMetadata):
    organization_id: str = ""
    workspace_id: str = ""
    user_plant_id: str = ""
    observed_at: str = field(default_factory=now_iso)
    author_id: str = ""
    text: str = ""
    images: list[str] = field(default_factory=list)
    audio: list[str] = field(default_factory=list)
    video: list[str] = field(default_factory=list)
    measurements: JsonDict = field(default_factory=dict)
    weather_snapshot_id: str | None = None
    source: ObservationSource = "user"


@dataclass(slots=True)
class MediaAttachment(EntityMetadata):
    organization_id: str = ""
    workspace_id: str = ""
    observation_id: str | None = None
    modality: MediaModality = "image"
    storage_uri: str = ""
    content_type: str = ""
    byte_size: int = 0
    metadata: JsonDict = field(default_factory=dict)


@dataclass(slots=True)
class EnvironmentalSnapshot(EntityMetadata):
    organization_id: str = ""
    location_id: str = ""
    observed_or_valid_at: str = field(default_factory=now_iso)
    retrieved_at: str = field(default_factory=now_iso)
    temperature: JsonDict = field(default_factory=dict)
    humidity: JsonDict = field(default_factory=dict)
    precipitation: JsonDict = field(default_factory=dict)
    wind: JsonDict = field(default_factory=dict)
    pressure: JsonDict = field(default_factory=dict)
    solar_radiation: JsonDict = field(default_factory=dict)
    photoperiod: JsonDict = field(default_factory=dict)
    soil_context: JsonDict = field(default_factory=dict)
    soil_moisture_context: JsonDict = field(default_factory=dict)
    drought_context: JsonDict = field(default_factory=dict)
    water_context: JsonDict = field(default_factory=dict)
    source_record_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class EvidenceClaim(EntityMetadata):
    organization_id: str = ""
    claim_text: str = ""
    evidence_grade: EvidenceGrade = "E"
    confidence: float = 0.0
    source_record_ids: list[str] = field(default_factory=list)
    contradictory_source_ids: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=now_iso)


@dataclass(slots=True)
class GuidancePlan(EntityMetadata):
    organization_id: str = ""
    conversation_id: str | None = None
    workspace_id: str = ""
    subject: str = ""
    situation: str = ""
    recommendations: list[JsonDict] = field(default_factory=list)
    actions: list[JsonDict] = field(default_factory=list)
    timing: list[JsonDict] = field(default_factory=list)
    resources: list[JsonDict] = field(default_factory=list)
    evidence_claim_ids: list[str] = field(default_factory=list)
    risks: list[JsonDict] = field(default_factory=list)
    uncertainty: JsonDict = field(default_factory=dict)
    measurements_to_take: list[JsonDict] = field(default_factory=list)
    follow_up: list[JsonDict] = field(default_factory=list)
    geo_context_id: str | None = None
    environmental_snapshot_id: str | None = None
    model_run_ids: list[str] = field(default_factory=list)
    provenance_bundle_id: str | None = None


@dataclass(slots=True)
class Action(EntityMetadata):
    organization_id: str = ""
    guidance_plan_id: str = ""
    title: str = ""
    instructions: str = ""
    earliest_at: str | None = None
    preferred_at: str | None = None
    deadline: str | None = None
    dependencies: list[str] = field(default_factory=list)
    weather_sensitive: bool = False
    user_confirmation_required: bool = False
    completion_status: str = "pending"
    completed_at: str | None = None


@dataclass(slots=True)
class Outcome(EntityMetadata):
    organization_id: str = ""
    action_id: str = ""
    user_plant_id: str = ""
    observed_at: str = field(default_factory=now_iso)
    result: str = ""
    measurements: JsonDict = field(default_factory=dict)
    user_rating: int | None = None
    attachments: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RegulationRule(EntityMetadata):
    jurisdiction_pack: str = ""
    authority: str = ""
    authority_level: str = ""
    subject_type: str = ""
    regulated_article: str = ""
    pest_or_disease: str | None = None
    geometry_or_area_reference: str | None = None
    origin_scope: JsonDict = field(default_factory=dict)
    destination_scope: JsonDict = field(default_factory=dict)
    conditions: list[JsonDict] = field(default_factory=list)
    permit_requirements: list[JsonDict] = field(default_factory=list)
    treatment_requirements: list[JsonDict] = field(default_factory=list)
    effective_from: str | None = None
    effective_to: str | None = None
    source_record_id: str | None = None
    last_verified_at: str | None = None


@dataclass(slots=True)
class MovementCheck(EntityMetadata):
    organization_id: str = ""
    origin_geo_context_id: str = ""
    destination_geo_context_id: str = ""
    article: str = ""
    species: str | None = None
    plant_part: str | None = None
    soil_attached: bool = False
    purpose: str | None = None
    planned_date: str | None = None
    status: MovementStatus = "unresolved"
    applicable_rule_ids: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    source_record_ids: list[str] = field(default_factory=list)
    checked_at: str = field(default_factory=now_iso)


@dataclass(slots=True)
class SeasonPlan(EntityMetadata):
    organization_id: str = ""
    workspace_id: str = ""
    crop_or_plant_ids: list[str] = field(default_factory=list)
    objective: str = ""
    location_id: str | None = None
    date_range: JsonDict = field(default_factory=dict)
    tasks: list[JsonDict] = field(default_factory=list)
    climate_basis: JsonDict = field(default_factory=dict)
    forecast_basis: JsonDict = field(default_factory=dict)
    regulatory_constraints: list[JsonDict] = field(default_factory=list)
    market_context: list[JsonDict] = field(default_factory=list)
    generated_at: str = field(default_factory=now_iso)


@dataclass(slots=True)
class CalendarBinding(EntityMetadata):
    organization_id: str = ""
    user_id: str = ""
    provider: str = ""
    external_calendar_id: str = ""
    encrypted_credential_reference: str = ""
    scopes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SourceRecord(EntityMetadata):
    organization_id: str | None = None
    provider: str = ""
    source_type: str = ""
    canonical_url: str | None = None
    external_record_id: str | None = None
    title: str = ""
    authority: str | None = None
    retrieved_at: str = field(default_factory=now_iso)
    observed_at: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    license: str = "unknown"
    attribution: str | None = None
    content_hash: str | None = None
    raw_snapshot_reference: str | None = None


@dataclass(slots=True)
class ModelRun(EntityMetadata):
    organization_id: str = ""
    provider: str = ""
    model: str = ""
    model_version: str | None = None
    local_or_remote: Literal["local", "remote"] = "local"
    input_modalities: list[str] = field(default_factory=list)
    input_tokens_or_units: int = 0
    output_tokens_or_units: int = 0
    elapsed_ms: int = 0
    cost_usd: float = 0.0
    tool_calls: list[JsonDict] = field(default_factory=list)
    prompt_version: str | None = None

