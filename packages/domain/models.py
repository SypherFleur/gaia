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
EvidenceDirection = Literal["supporting", "contradictory", "uncertain", "irrelevant"]
EvidenceQuality = Literal["strong", "moderate", "limited", "mixed", "insufficient", "unknown"]
StudyType = Literal[
    "meta-analysis",
    "systematic review",
    "randomized controlled trial",
    "controlled experiment",
    "observational study",
    "field trial",
    "laboratory study",
    "review",
    "case study",
    "expert opinion",
    "unknown",
]
MovementStatus = Literal["allowed", "conditional", "restricted", "unresolved"]
MovementDecisionStatus = Literal["ALLOWED", "CONDITIONAL", "RESTRICTED", "UNRESOLVED"]
RegulatoryFreshness = Literal["CURRENT", "STALE", "EXPIRED", "UNAVAILABLE", "CONFLICT"]
PlantPart = Literal["seed", "fruit", "live plant", "cutting", "scion", "root", "soil", "growing medium", "unknown"]
MediaModality = Literal["image", "audio", "video", "document_image"]
PrivacyPrecision = Literal["exact", "approximate", "100m", "1km", "county", "district", "custom"]
ConversationState = Literal["active", "archived"]
MessageRole = Literal["user", "assistant", "system", "tool"]
GrowthStage = Literal[
    "seed",
    "germinating",
    "seedling",
    "vegetative",
    "flowering",
    "fruiting",
    "harvest",
    "dormant",
    "senescent",
    "unknown",
]
VisionAnalysisStatus = Literal["AVAILABLE", "UNAVAILABLE", "PROVIDER_ERROR", "VALIDATION_FAILED"]


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
    country_code: str | None = None
    state_or_region: str | None = None
    state_code: str | None = None
    county_or_district: str | None = None
    county_fips: str | None = None
    timezone: str | None = None
    elevation_m: float | None = None
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
    kingdom: str | None = None
    common_names: list[str] = field(default_factory=list)
    family: str | None = None
    genus: str | None = None
    species: str | None = None
    subspecies: str | None = None
    cultivar_optional: str | None = None
    crop_group: str | None = None
    edible_classification: str | None = None
    native_status: str | None = None
    introduced_status: str | None = None
    synonyms: list[JsonDict] = field(default_factory=list)
    external_source_ids: JsonDict = field(default_factory=dict)
    canonical_name_source_record_id: str | None = None
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
    lifecycle_stage: GrowthStage | str | None = None
    location_id: str | None = None
    container_or_bed: str | None = None
    growing_method: str | None = None
    biocube_reference: str | None = None
    status: str = "active"
    notes: str = ""
    tags: list[str] = field(default_factory=list)
    archived_at: str | None = None


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
    observed_facts: list[JsonDict] = field(default_factory=list)
    gaia_inferences: list[JsonDict] = field(default_factory=list)
    lifecycle_stage_observed: GrowthStage | str | None = None
    health_tags: list[str] = field(default_factory=list)
    action_id: str | None = None
    outcome_id: str | None = None


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
class VisualObservation(EntityMetadata):
    organization_id: str = ""
    visual_analysis_id: str = ""
    label: str = ""
    description: str = ""
    visibility: str = "visible"
    bounding_region: JsonDict | None = None
    confidence: float | None = None
    source_record_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class VisualHypothesis(EntityMetadata):
    organization_id: str = ""
    visual_analysis_id: str = ""
    label: str = ""
    rationale: str = ""
    confidence: float = 0.0
    status: str = "hypothesis"
    required_next_evidence: list[str] = field(default_factory=list)
    source_record_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class VisualAnalysis(EntityMetadata):
    organization_id: str = ""
    workspace_id: str = ""
    user_plant_id: str | None = None
    media_attachment_id: str = ""
    provider: str = ""
    model: str | None = None
    status: VisionAnalysisStatus | str = "AVAILABLE"
    image_quality: JsonDict = field(default_factory=dict)
    plant_candidates: list[JsonDict] = field(default_factory=list)
    visual_observations: list[JsonDict] = field(default_factory=list)
    visual_hypotheses: list[JsonDict] = field(default_factory=list)
    required_next_evidence: list[str] = field(default_factory=list)
    botanist_context: JsonDict = field(default_factory=dict)
    geo_context_id: str | None = None
    environmental_snapshot_id: str | None = None
    model_run_id: str | None = None
    source_record_ids: list[str] = field(default_factory=list)
    safety_notes: list[str] = field(default_factory=list)


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
    forecast: JsonDict = field(default_factory=dict)
    solar_radiation: JsonDict = field(default_factory=dict)
    photoperiod: JsonDict = field(default_factory=dict)
    solar_context: JsonDict = field(default_factory=dict)
    soil_context: JsonDict = field(default_factory=dict)
    soil_moisture_context: JsonDict = field(default_factory=dict)
    drought_context: JsonDict = field(default_factory=dict)
    water_context: JsonDict = field(default_factory=dict)
    season_context: JsonDict = field(default_factory=dict)
    astronomical_context: JsonDict = field(default_factory=dict)
    provider_statuses: JsonDict = field(default_factory=dict)
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
class ResearchAuthor(EntityMetadata):
    display_name: str = ""
    given_name: str | None = None
    family_name: str | None = None
    orcid: str | None = None
    source_record_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ResearchWork(EntityMetadata):
    title: str = ""
    abstract: str | None = None
    publication_year: int | None = None
    journal: str | None = None
    doi: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    provider_ids: JsonDict = field(default_factory=dict)
    publication_types: list[str] = field(default_factory=list)
    open_access_status: str = "unknown"
    retracted_status: str = "unknown"
    study_type: StudyType | str = "unknown"
    authors: list[JsonDict] = field(default_factory=list)
    evidence_policy: JsonDict = field(default_factory=dict)
    source_record_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ResearchClaim(EntityMetadata):
    organization_id: str = ""
    statement: str = ""
    subject: str = ""
    evidence_direction: EvidenceDirection | str = "uncertain"
    evidence_quality: EvidenceQuality | str = "unknown"
    evidence_grade: EvidenceGrade = "E"
    model_confidence: str | None = None
    data_freshness: str = "unknown"
    source_work_ids: list[str] = field(default_factory=list)
    source_record_ids: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    study_type: StudyType | str = "unknown"
    applicability: JsonDict = field(default_factory=dict)


@dataclass(slots=True)
class EvidenceSynthesis(EntityMetadata):
    organization_id: str = ""
    workspace_id: str = ""
    question: str = ""
    scope: JsonDict = field(default_factory=dict)
    supporting_claims: list[JsonDict] = field(default_factory=list)
    contradictory_claims: list[JsonDict] = field(default_factory=list)
    uncertain_claims: list[JsonDict] = field(default_factory=list)
    evidence_quality: EvidenceQuality | str = "unknown"
    model_confidence: str | None = None
    data_freshness: str = "unknown"
    uncertainty: JsonDict = field(default_factory=dict)
    applicability: JsonDict = field(default_factory=dict)
    source_work_ids: list[str] = field(default_factory=list)
    source_record_ids: list[str] = field(default_factory=list)
    model_run_ids: list[str] = field(default_factory=list)
    provenance_bundle_id: str | None = None
    export_payload: JsonDict = field(default_factory=dict)
    generated_at: str = field(default_factory=now_iso)


@dataclass(slots=True)
class ResearchCollection(EntityMetadata):
    organization_id: str = ""
    workspace_id: str = ""
    name: str = ""
    visibility: Literal["private", "institution", "public"] = "private"
    work_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ResearchAnnotation(EntityMetadata):
    organization_id: str = ""
    workspace_id: str = ""
    collection_id: str | None = None
    work_id: str = ""
    author_id: str = ""
    note: str = ""
    tags: list[str] = field(default_factory=list)
    private: bool = True


@dataclass(slots=True)
class GuidancePlan(EntityMetadata):
    organization_id: str = ""
    conversation_id: str | None = None
    workspace_id: str = ""
    user_plant_id: str | None = None
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
class MovementRequest(EntityMetadata):
    organization_id: str = ""
    workspace_id: str = ""
    origin_location_id: str | None = None
    destination_location_id: str | None = None
    planned_date: str | None = None
    species: str | None = None
    cultivar: str | None = None
    plant_part: PlantPart | str = "unknown"
    live_plant: bool = False
    soil_attached: bool = False
    growing_media: str | None = None
    quantity: int | None = None
    purpose: str | None = None
    commercial_or_personal: str = "personal"
    source_country: str | None = None
    destination_country: str | None = None
    metadata: JsonDict = field(default_factory=dict)


@dataclass(slots=True)
class MovementDecision(EntityMetadata):
    organization_id: str = ""
    workspace_id: str = ""
    movement_request_id: str = ""
    status: MovementDecisionStatus | str = "UNRESOLVED"
    applicable_jurisdictions: list[JsonDict] = field(default_factory=list)
    applicable_rules: list[JsonDict] = field(default_factory=list)
    conditions: list[JsonDict] = field(default_factory=list)
    permit_requirements: list[JsonDict] = field(default_factory=list)
    treatment_requirements: list[JsonDict] = field(default_factory=list)
    inspection_requirements: list[JsonDict] = field(default_factory=list)
    reporting_requirements: list[JsonDict] = field(default_factory=list)
    unresolved_questions: list[str] = field(default_factory=list)
    conflicts: list[JsonDict] = field(default_factory=list)
    checked_at: str = field(default_factory=now_iso)
    freshness: RegulatoryFreshness | str = "UNAVAILABLE"
    source_record_ids: list[str] = field(default_factory=list)
    model_run_ids: list[str] = field(default_factory=list)
    authority_statement: str = ""


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
class Conversation(EntityMetadata):
    organization_id: str = ""
    workspace_id: str = ""
    user_id: str = ""
    title: str = ""
    location_id: str | None = None
    user_plant_id: str | None = None
    state: ConversationState = "active"
    last_message_at: str | None = None


@dataclass(slots=True)
class PlantProfile(EntityMetadata):
    organization_id: str = ""
    plant_entity_id: str = ""
    version: int = 1
    taxonomy: JsonDict = field(default_factory=dict)
    common_names: list[str] = field(default_factory=list)
    crop_group: str | None = None
    growth_habit: str | None = None
    lifecycle: str | None = None
    temperature_context: JsonDict = field(default_factory=dict)
    water_context: JsonDict = field(default_factory=dict)
    soil_context: JsonDict = field(default_factory=dict)
    light_context: JsonDict = field(default_factory=dict)
    season_context: JsonDict = field(default_factory=dict)
    known_pest_links: list[JsonDict] = field(default_factory=list)
    known_disease_links: list[JsonDict] = field(default_factory=list)
    germplasm_links: list[JsonDict] = field(default_factory=list)
    field_provenance: JsonDict = field(default_factory=dict)
    conflicts: list[JsonDict] = field(default_factory=list)
    source_record_ids: list[str] = field(default_factory=list)
    confidence: JsonDict = field(default_factory=dict)
    completeness: float = 0.0


@dataclass(slots=True)
class Message(EntityMetadata):
    organization_id: str = ""
    conversation_id: str = ""
    role: MessageRole = "user"
    content: str = ""
    content_type: str = "text"
    route: str | None = None
    model_run_id: str | None = None
    guidance_plan_id: str | None = None
    source_record_ids: list[str] = field(default_factory=list)
    metadata: JsonDict = field(default_factory=dict)


@dataclass(slots=True)
class PromptHarness(EntityMetadata):
    prompt_id: str = ""
    semantic_version: str = ""
    prompt_hash: str = ""
    intended_task: str = ""
    model_compatibility: list[str] = field(default_factory=list)
    output_schema: JsonDict = field(default_factory=dict)
    evaluation_score: float | None = None
    active: bool = True


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
    prompt_id: str | None = None
    prompt_hash: str | None = None
    request_hash: str | None = None
    response_hash: str | None = None
    status: str = "success"
    error: str | None = None
