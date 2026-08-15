from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Literal

from packages.audit import AuditLog, UsageLedger
from packages.botany import (
    BotanistService,
    DisabledGermplasmProvider,
    DisabledTaxonomyProvider,
    FixtureGBIFProvider,
    FixtureGenesysProvider,
    GBIFApiAdapter,
    GBIFTaxonomyTool,
    GenesysGermplasmTool,
    GenesysPGRAdapter,
    KewPOWOApiAdapter,
    KewPOWOTaxonomyTool,
)
from packages.cache import SQLiteCacheBackend
from packages.calendar_gateway import CalendarCreateEventTool, CalendarWorkflowService, FixtureCalendarProvider
from packages.context import ContextCompiler
from packages.cost import CostFirewall, FinancialPolicy, ProviderCostPolicy
from packages.domain import (
    CalendarBinding,
    GuidancePlan,
    Location,
    Membership,
    Observation,
    Organization,
    ResearchProject,
    SeasonPlan,
    SourceRecord,
    User,
    Workspace,
)
from packages.domain.models import new_id, now_iso
from packages.environment import TerraService
from packages.environment.fixture_adapters import FixtureNASAPowerProvider, FixtureNWSProvider, FixtureUSDASoilProvider, FixtureUSGSWaterProvider
from packages.environment.live_adapters import NASAPowerApiAdapter, NWSApiAdapter, USDASoilDataAccessAdapter
from packages.environment.providers import DisabledClimateProvider, DisabledSoilSurveyProvider, DisabledWaterProvider, DisabledWeatherProvider
from packages.environment.tools import NASAPowerClimateTool, NWSForecastTool, USDASoilSurveyTool, USGSWaterSitesTool
from packages.geospatial import AtlasService, CensusGeocoderAdapter, CensusGeographyTool
from packages.geospatial.providers import (
    AdminResolution,
    AtlasZone,
    DisabledHardinessProvider,
    DisabledRegulatoryGeometryProvider,
    DisabledWatershedProvider,
    FixtureHardinessProvider,
    FixtureWatershedProvider,
    ProviderStatus,
    RegulatoryZoneResolution,
)
from packages.mercator import (
    AMSMarketReportTool,
    AMSSupplyChainTool,
    AMSMyMarketNewsProvider,
    DisabledEconomicProvider,
    FixtureAMSProvider,
    FixtureNASSProvider,
    MercatorContextProvider,
    NASSQuickStatsProvider,
    NASSProductionTool,
    NASSRegionalContextTool,
)
from packages.model_gateway import FixtureGuidanceModelProvider, ModelGateway, OllamaModelProvider
from packages.orchestration import GaiaOrchestrator
from packages.persistence import GaiaRepository, connect_in_memory, initialize_schema
from packages.policy import DataEgressPolicy
from packages.providers import (
    AuthenticationRequirement,
    BillingClass,
    CachePolicy,
    FreshnessClass,
    HealthStatus,
    LicenseMetadata,
    ProviderQuotaPolicy,
    ProviderRecord,
    ProviderRegistry,
    ProviderType,
    QuotaManager,
)
from packages.provenance import ProvenanceRecord, content_hash
from packages.research import DisabledResearchProvider, EuropePMCFetchTool, EuropePMCSearchTool, FixtureResearchProvider, FixtureScholarModelProvider, ScholarService
from packages.research.europe_pmc import EuropePMCAdapter
from packages.season import DeterministicSeasonPlanner, SeasonContextProvider, SeasonService
from packages.sentinel import (
    APHIS_CITRUS_URL,
    APHIS_IMPORT_URL,
    FDACS_CITRUS_QUARANTINE_URL,
    FDACS_IMPORT_REGULATIONS_URL,
    FDACS_PLANT_INSPECTION_URL,
    FixtureAPHISProvider,
    FixtureFloridaFDACSProvider,
    FixtureTexasAgricultureProvider,
    JurisdictionPack,
    JurisdictionPackMetadata,
    JurisdictionPackRegistry,
    ReadOnlyRegulatoryPageAdapter,
    RegulationMovementRulesTool,
    RegulationPestAlertsTool,
    SentinelService,
    TEXAS_CITRUS_URL,
    TEXAS_GREENING_URL,
    USStateJurisdictionPack,
)
from packages.status import CostStatusService
from packages.tools import ToolExecutionContext, ToolGateway
from packages.vision import DisabledVisionProvider, FixtureVisionProvider, OllamaLlavaVisionProvider, VisionAnalysisTool, VisionService


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SQLITE_URL = "sqlite:///./local_data/gaia.sqlite3"
DEFAULT_ALPHA_HOST = "127.0.0.1"
DEFAULT_ALPHA_PORT = 8765

ProviderMode = Literal["fixture", "live", "disabled", "local"]


@dataclass(frozen=True, slots=True)
class AlphaProviderModes:
    atlas_geography: ProviderMode = "fixture"
    nws: ProviderMode = "fixture"
    nasa_power: ProviderMode = "fixture"
    usda_soil: ProviderMode = "fixture"
    usgs_water: ProviderMode = "fixture"
    gbif: ProviderMode = "fixture"
    kew_powo: ProviderMode = "disabled"
    genesys_pgr: ProviderMode = "fixture"
    europe_pmc: ProviderMode = "fixture"
    aphis: ProviderMode = "fixture"
    texas_agriculture: ProviderMode = "fixture"
    florida_fdacs: ProviderMode = "fixture"
    usda_nass: ProviderMode = "fixture"
    usda_ams: ProviderMode = "fixture"
    plantnet: ProviderMode = "disabled"
    google_calendar: ProviderMode = "disabled"
    text_model: ProviderMode = "local"
    vision_model: ProviderMode = "local"

    @classmethod
    def from_environment(cls, *, fixture_defaults: bool = False) -> "AlphaProviderModes":
        defaults = _fixture_provider_defaults() if fixture_defaults else _normal_provider_defaults()
        return cls(
            atlas_geography=_mode("GAIA_ATLAS_GEOGRAPHY_MODE", defaults["atlas_geography"]),
            nws=_mode("GAIA_NWS_MODE", defaults["nws"]),
            nasa_power=_mode("GAIA_NASA_POWER_MODE", defaults["nasa_power"]),
            usda_soil=_mode("GAIA_USDA_SOIL_MODE", defaults["usda_soil"]),
            usgs_water=_mode("GAIA_USGS_WATER_MODE", defaults["usgs_water"]),
            gbif=_mode("GAIA_GBIF_MODE", defaults["gbif"]),
            kew_powo=_mode("GAIA_KEW_POWO_MODE", defaults["kew_powo"]),
            genesys_pgr=_mode("GAIA_GENESYS_MODE", defaults["genesys_pgr"]),
            europe_pmc=_mode("GAIA_EUROPE_PMC_MODE", defaults["europe_pmc"]),
            aphis=_mode("GAIA_APHIS_MODE", defaults["aphis"]),
            texas_agriculture=_mode("GAIA_TEXAS_AGRICULTURE_MODE", defaults["texas_agriculture"]),
            florida_fdacs=_mode("GAIA_FLORIDA_FDACS_MODE", defaults["florida_fdacs"]),
            usda_nass=_mode("GAIA_NASS_MODE", defaults["usda_nass"]),
            usda_ams=_mode("GAIA_AMS_MODE", defaults["usda_ams"]),
            plantnet=_mode("GAIA_PLANTNET_MODE", defaults["plantnet"]),
            google_calendar=_mode("GAIA_GOOGLE_CALENDAR_MODE", defaults["google_calendar"]),
            text_model=_mode("GAIA_TEXT_MODEL_MODE", defaults["text_model"]),
            vision_model=_mode("GAIA_VISION_MODEL_MODE", defaults["vision_model"]),
        )

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(slots=True)
class GaiaRuntime:
    connection: sqlite3.Connection
    repository: GaiaRepository
    registry: ProviderRegistry
    usage_ledger: UsageLedger
    audit_log: AuditLog
    tool_gateway: ToolGateway
    model_gateway: ModelGateway
    atlas: AtlasService
    terra: TerraService
    context_compiler: ContextCompiler
    botanist: BotanistService
    vision: VisionService
    vision_tool: VisionAnalysisTool
    scholar: ScholarService
    sentinel: SentinelService
    season: SeasonService
    season_context_provider: SeasonContextProvider
    calendar: CalendarWorkflowService
    mercator: MercatorContextProvider
    orchestrator: GaiaOrchestrator
    organization_id: str
    user_id: str
    workspace_id: str
    primary_location_id: str | None
    calendar_binding_id: str
    location_aliases: dict[str, str]
    provider_modes: AlphaProviderModes
    database_url: str = DEFAULT_SQLITE_URL
    sovereign: bool = False
    fixture_defaults: bool = False
    text_model: str = "llama3.1:latest"
    vision_model: str = "llava:latest"
    live_regulatory_probes: dict[str, object] = field(default_factory=dict)

    def context(self, *, request_id: str = "cli") -> ToolExecutionContext:
        return ToolExecutionContext(
            request_id=request_id,
            organization_id=self.organization_id,
            user_id=self.user_id,
            workspace_id=self.workspace_id,
            permissions=frozenset({"tool.read", "regulation.read", "vision.analyze", "model.chat", "calendar.create"}),
            data_egress_policy=DataEgressPolicy.sovereign_default() if self.sovereign else DataEgressPolicy(),
            deployment_mode="sovereign" if self.sovereign else "local",
        )

    def close(self) -> None:
        self.connection.close()


def create_runtime(
    database_url: str | None = None,
    *,
    sovereign: bool = False,
    provider_modes: AlphaProviderModes | None = None,
) -> GaiaRuntime:
    database = database_url or DEFAULT_SQLITE_URL
    fixture_defaults = _fixture_defaults_for_runtime(database)
    modes = provider_modes or AlphaProviderModes.from_environment(fixture_defaults=fixture_defaults)
    connection = connect_sqlite_url(database)
    initialize_schema_if_empty(connection)
    repository = GaiaRepository(connection)
    identity = ensure_development_identity(repository, sovereign=sovereign, fixture_defaults=fixture_defaults)

    registry = build_provider_registry(modes)
    usage_ledger = UsageLedger(connection)
    audit_log = AuditLog(connection)
    cost_firewall = CostFirewall(FinancialPolicy())
    tool_gateway = ToolGateway(
        connection=connection,
        registry=registry,
        cost_firewall=cost_firewall,
        quota_manager=QuotaManager(connection),
        cache_backend=SQLiteCacheBackend(connection),
        usage_ledger=usage_ledger,
        audit_log=audit_log,
    )

    atlas_live = modes.atlas_geography == "live"
    atlas = AtlasService(
        repository,
        CLIGeographyProvider(fixture=fixture_defaults),
        FixtureWatershedProvider() if fixture_defaults else DisabledWatershedProvider(),
        FixtureHardinessProvider() if fixture_defaults else DisabledHardinessProvider(),
        CLIRegulatoryGeometryProvider(fixture=fixture_defaults) if fixture_defaults else DisabledRegulatoryGeometryProvider(),
        tool_gateway=tool_gateway if atlas_live else None,
        geography_tool=CensusGeographyTool(
            CensusGeocoderAdapter(user_agent=os.environ.get("CENSUS_USER_AGENT") or "GAIA Local Alpha/0.1")
        )
        if atlas_live
        else None,
    )
    terra = TerraService(
        repository,
        tool_gateway,
        NWSForecastTool(_nws_provider(modes)),
        NASAPowerClimateTool(_nasa_power_provider(modes)),
        USDASoilSurveyTool(_soil_provider(modes)),
        USGSWaterSitesTool(_water_provider(modes)),
    )
    context_compiler = ContextCompiler(repository, atlas, terra)

    model_gateway = ModelGateway(
        connection=connection,
        registry=registry,
        providers={"ollama-local": _text_model_provider(modes)},
        cost_firewall=cost_firewall,
        usage_ledger=usage_ledger,
        audit_log=audit_log,
    )

    botanist = BotanistService(
        repository,
        tool_gateway,
        GBIFTaxonomyTool(_gbif_provider(modes)),
        GenesysGermplasmTool(_genesys_provider(modes)),
        taxonomy_supplement_tools=[KewPOWOTaxonomyTool(_kew_provider(modes))],
    )
    vision_tool = VisionAnalysisTool(_vision_provider(modes), provider_id=_vision_provider_id(modes))
    vision = VisionService(repository=repository, tool_gateway=tool_gateway, context_compiler=context_compiler, botanist=botanist)

    research_provider = _research_provider(modes)
    scholar_model_gateway = model_gateway if modes.text_model == "local" else ModelGateway(
        connection=connection,
        registry=registry,
        providers={"ollama-local": FixtureScholarModelProvider()},
        cost_firewall=cost_firewall,
        usage_ledger=usage_ledger,
        audit_log=audit_log,
    )
    scholar = ScholarService(
        repository=repository,
        tool_gateway=tool_gateway,
        search_tool=EuropePMCSearchTool(research_provider),
        fetch_tool=EuropePMCFetchTool(research_provider),
        model_gateway=scholar_model_gateway,
        botanist=botanist,
        context_compiler=context_compiler,
    )

    aphis = _aphis_provider(modes)
    texas = _texas_regulatory_provider(modes)
    florida = _florida_regulatory_provider(modes)
    live_regulatory_probes = _live_regulatory_probes(modes)
    pack_registry = JurisdictionPackRegistry(
        [
            JurisdictionPack(JurisdictionPackMetadata("us_federal", "0.1.0", "U.S. federal", "US", ["usda_aphis"], enabled=True), aphis),
            USStateJurisdictionPack(JurisdictionPackMetadata("us_tx", "0.1.0", "Texas", "US", ["tx_agriculture"], enabled=True), texas, state_code="TX"),
            USStateJurisdictionPack(JurisdictionPackMetadata("us_fl", "0.1.0", "Florida", "US", ["fl_fdacs_dpi"], enabled=True), florida, state_code="FL"),
        ]
    )
    sentinel = SentinelService(
        repository=repository,
        tool_gateway=tool_gateway,
        context_compiler=context_compiler,
        federal_tool=RegulationMovementRulesTool(aphis, "aphis"),
        texas_tool=RegulationMovementRulesTool(texas, "texas-agriculture"),
        jurisdiction_registry=pack_registry,
        alert_tools=[
            RegulationPestAlertsTool(aphis, "aphis"),
            RegulationPestAlertsTool(texas, "texas-agriculture"),
            RegulationPestAlertsTool(florida, "florida-fdacs"),
        ],
    )

    mercator = MercatorContextProvider(
        repository=repository,
        tool_gateway=tool_gateway,
        nass_production_tool=NASSProductionTool(_nass_provider(modes)),
        nass_region_tool=NASSRegionalContextTool(_nass_provider(modes)),
        ams_market_tool=AMSMarketReportTool(_ams_provider(modes)),
        ams_supply_chain_tool=AMSSupplyChainTool(_ams_provider(modes)),
    )
    season_context_provider = SeasonContextProvider(repository=repository, context_compiler=context_compiler, mercator_context_provider=mercator)
    season = SeasonService(repository=repository, planner=DeterministicSeasonPlanner(), model_gateway=model_gateway)
    calendar_provider = FixtureCalendarProvider(unavailable=modes.google_calendar == "disabled")
    calendar = CalendarWorkflowService(
        repository=repository,
        tool_gateway=tool_gateway,
        create_tool=CalendarCreateEventTool(calendar_provider, "fixture-calendar"),
    )
    orchestrator = GaiaOrchestrator(
        repository=repository,
        context_compiler=context_compiler,
        model_gateway=model_gateway,
        botanist=botanist,
        season=season,
        season_context_provider=season_context_provider,
        mercator_context_provider=mercator,
    )

    return GaiaRuntime(
        connection=connection,
        repository=repository,
        registry=registry,
        usage_ledger=usage_ledger,
        audit_log=audit_log,
        tool_gateway=tool_gateway,
        model_gateway=model_gateway,
        atlas=atlas,
        terra=terra,
        context_compiler=context_compiler,
        botanist=botanist,
        vision=vision,
        vision_tool=vision_tool,
        scholar=scholar,
        sentinel=sentinel,
        season=season,
        season_context_provider=season_context_provider,
        calendar=calendar,
        mercator=mercator,
        orchestrator=orchestrator,
        organization_id=identity["organization_id"],
        user_id=identity["user_id"],
        workspace_id=identity["workspace_id"],
        primary_location_id=identity["primary_location_id"],
        calendar_binding_id=identity["calendar_binding_id"],
        location_aliases=identity["location_aliases"],
        provider_modes=modes,
        database_url=database,
        sovereign=sovereign,
        fixture_defaults=fixture_defaults,
        text_model=os.environ.get("GAIA_OLLAMA_MODEL", "llama3.1:latest"),
        vision_model=os.environ.get("GAIA_LLAVA_MODEL", "llava:latest"),
        live_regulatory_probes=live_regulatory_probes,
    )


def ensure_development_identity(repository: GaiaRepository, *, sovereign: bool = False, fixture_defaults: bool = False) -> dict:
    organization = _find_one(repository.connection, "organizations", "slug", "gaia-local-alpha")
    if organization is None:
        try:
            organization_obj = repository.create_organization(
                Organization(name="GAIA Local Alpha", slug="gaia-local-alpha", deployment_mode="sovereign" if sovereign else "local")
            )
            organization_id = organization_obj.id
        except sqlite3.IntegrityError:
            organization = _find_one(repository.connection, "organizations", "slug", "gaia-local-alpha")
            if organization is None:
                raise
            organization_id = organization["id"]
    else:
        organization_id = organization["id"]

    user = _find_user(repository.connection, "development:jason")
    if user is None:
        try:
            user_obj = repository.create_user(User(external_auth_id="development:jason", display_name="Jason Development Identity", timezone="America/Chicago"))
            user_id = user_obj.id
        except sqlite3.IntegrityError:
            user = _find_user(repository.connection, "development:jason")
            if user is None:
                raise
            user_id = user["id"]
    else:
        user_id = user["id"]

    if _membership(repository.connection, organization_id, user_id) is None:
        try:
            repository.create_membership(
                Membership(
                    organization_id=organization_id,
                    user_id=user_id,
                    role="owner",
                    permissions=["tool.read", "regulation.read", "vision.analyze", "model.chat", "calendar.create"],
                )
            )
        except sqlite3.IntegrityError:
            if _membership(repository.connection, organization_id, user_id) is None:
                raise

    workspace = _workspace(repository.connection, organization_id, "Alpha Workspace")
    if workspace is None:
        workspace_obj = repository.create_workspace(Workspace(organization_id=organization_id, name="Alpha Workspace", purpose="manual local alpha"))
        workspace_id = workspace_obj.id
    else:
        workspace_id = workspace["id"]

    if fixture_defaults:
        aliases = seed_cli_locations(repository, organization_id)
        primary_location_id = aliases["tx-austin"]
        repository.set_workspace_default_location(organization_id, workspace_id, primary_location_id)
    else:
        aliases = {}
        primary_location_id = _active_real_location_id(repository, organization_id, workspace_id)
        repository.set_workspace_default_location(organization_id, workspace_id, primary_location_id)

    calendar_binding = _calendar_binding(repository.connection, organization_id, user_id)
    if calendar_binding is None:
        try:
            binding = repository.create_calendar_binding(
                CalendarBinding(
                    organization_id=organization_id,
                    user_id=user_id,
                    provider="fixture-calendar",
                    external_calendar_id="fixture-primary",
                    encrypted_credential_reference="fixture-local-alpha",
                    credential_reference="fixture-local-alpha",
                    scopes=["calendar.create"],
                    status="connected",
                )
            )
            calendar_binding_id = binding.id
        except sqlite3.IntegrityError:
            calendar_binding = _calendar_binding(repository.connection, organization_id, user_id)
            if calendar_binding is None:
                raise
            calendar_binding_id = calendar_binding["id"]
    else:
        calendar_binding_id = calendar_binding["id"]

    return {
        "organization_id": organization_id,
        "user_id": user_id,
        "workspace_id": workspace_id,
        "primary_location_id": primary_location_id,
        "calendar_binding_id": calendar_binding_id,
        "location_aliases": aliases,
    }


def seed_cli_locations(repository: GaiaRepository, organization_id: str) -> dict[str, str]:
    records = {
        "tx-austin": Location(organization_id=organization_id, label="Austin garden", latitude=30.2672, longitude=-97.7431, privacy_precision="1km", exact_coordinates_authorized=True, timezone="America/Chicago", country_code="US", admin1="TX", admin2="Travis County", county_fips="48453", source_kind="demo_fixture", source_label="GAIA CLI demo alias", is_demo=True),
        "tx-houston": Location(organization_id=organization_id, label="Houston, TX", latitude=29.7604, longitude=-95.3698, privacy_precision="1km", exact_coordinates_authorized=True, timezone="America/Chicago", country_code="US", admin1="TX", admin2="Harris County", county_fips="48201", source_kind="demo_fixture", source_label="GAIA CLI demo alias", is_demo=True),
        "tx-hidalgo": Location(organization_id=organization_id, label="Hidalgo County, TX", latitude=26.1, longitude=-98.2, privacy_precision="1km", exact_coordinates_authorized=True, timezone="America/Chicago", country_code="US", admin1="TX", admin2="Hidalgo County", county_fips="48215", source_kind="demo_fixture", source_label="GAIA CLI demo alias", is_demo=True),
        "fl-orlando": Location(organization_id=organization_id, label="Orlando, FL", latitude=28.5383, longitude=-81.3792, privacy_precision="1km", exact_coordinates_authorized=True, timezone="America/New_York", country_code="US", admin1="FL", admin2="Orange County", county_fips="12095", source_kind="demo_fixture", source_label="GAIA CLI demo alias", is_demo=True),
        "fl-broward": Location(organization_id=organization_id, label="Broward County, FL", latitude=26.1901, longitude=-80.3659, privacy_precision="1km", exact_coordinates_authorized=True, timezone="America/New_York", country_code="US", admin1="FL", admin2="Broward County", county_fips="12011", source_kind="demo_fixture", source_label="GAIA CLI demo alias", is_demo=True),
        "ga-atlanta": Location(organization_id=organization_id, label="Atlanta, GA", latitude=33.7490, longitude=-84.3880, privacy_precision="1km", exact_coordinates_authorized=True, timezone="America/New_York", country_code="US", admin1="GA", admin2="Fulton County", county_fips="13121", source_kind="demo_fixture", source_label="GAIA CLI demo alias", is_demo=True),
        "ca-los-angeles": Location(organization_id=organization_id, label="Los Angeles, CA", latitude=34.0522, longitude=-118.2437, privacy_precision="1km", exact_coordinates_authorized=True, timezone="America/Los_Angeles", country_code="US", admin1="CA", admin2="Los Angeles County", county_fips="06037", source_kind="demo_fixture", source_label="GAIA CLI demo alias", is_demo=True),
    }
    aliases = {}
    for alias, location in records.items():
        existing = _location(repository.connection, organization_id, location.label)
        if existing:
            aliases[alias] = existing["id"]
            repository.connection.execute(
                """
                UPDATE locations
                SET source_kind = ?, source_label = ?, is_demo = ?, updated_at = ?
                WHERE id = ? AND organization_id = ?
                """,
                ("demo_fixture", "GAIA CLI demo alias", 1, now_iso(), existing["id"], organization_id),
            )
            repository.connection.commit()
        else:
            aliases[alias] = repository.create_location(location).id
    return aliases


def existing_cli_location_aliases(repository: GaiaRepository, organization_id: str) -> dict[str, str]:
    aliases = {}
    for alias, label in _demo_location_labels().items():
        existing = _location(repository.connection, organization_id, label)
        if existing:
            aliases[alias] = existing["id"]
    return aliases


def _demo_location_labels() -> dict[str, str]:
    return {
        "tx-austin": "Austin garden",
        "tx-houston": "Houston, TX",
        "tx-hidalgo": "Hidalgo County, TX",
        "fl-orlando": "Orlando, FL",
        "fl-broward": "Broward County, FL",
        "ga-atlanta": "Atlanta, GA",
        "ca-los-angeles": "Los Angeles, CA",
    }


def _active_real_location_id(repository: GaiaRepository, organization_id: str, workspace_id: str) -> str | None:
    workspace = repository.get_workspace(organization_id, workspace_id)
    candidate_id = workspace.get("default_location_id") if workspace else None
    if candidate_id:
        location = repository.get_location(organization_id, candidate_id)
        if location and not bool(location.get("is_demo")) and location.get("source_kind") in {"device", "manual", "saved"}:
            return candidate_id
    rows = repository.connection.execute(
        """
        SELECT id FROM locations
        WHERE organization_id = ? AND deleted_at IS NULL
          AND is_demo = 0 AND source_kind IN ('device', 'manual', 'saved')
        ORDER BY source_kind = 'device' DESC, verified_at DESC, updated_at DESC
        LIMIT 1
        """,
        (organization_id,),
    ).fetchone()
    return rows["id"] if rows else None


def seed_demo(runtime: GaiaRuntime) -> dict:
    from apps.api.gaia_api.plant_api import post_observation, post_plant
    from apps.api.gaia_api.season_api import post_season_plan

    import asyncio

    context = runtime.context(request_id="seed-demo")
    if "tx-austin" not in runtime.location_aliases:
        runtime.location_aliases.update(seed_cli_locations(runtime.repository, runtime.organization_id))
    demo_workspace_id = ensure_demo_workspace(runtime.repository, runtime.organization_id)
    runtime.workspace_id = demo_workspace_id
    demo_location_id = runtime.location_aliases["tx-austin"]
    runtime.primary_location_id = demo_location_id
    runtime.repository.set_workspace_default_location(runtime.organization_id, demo_workspace_id, demo_location_id)
    context = runtime.context(request_id="seed-demo")
    existing_plants = runtime.repository.list_user_plants(runtime.organization_id, runtime.workspace_id)
    tomato = next((plant for plant in existing_plants if plant["nickname"] == "Cherokee Purple Tomato"), None)
    if tomato is None:
        created = asyncio.run(
            post_plant(
                runtime.repository,
                runtime.botanist,
                context,
                taxon_query="Solanum lycopersicum",
                nickname="Cherokee Purple Tomato",
                cultivar="Cherokee Purple",
                lifecycle_stage="vegetative",
                location_id=demo_location_id,
                growing_method="raised bed",
                tags=["demo", "tomato"],
            )
        )
        tomato = created["plant"]
    observations = runtime.repository.list_observations(runtime.organization_id, tomato["id"])
    if not observations:
        asyncio.run(
            post_observation(
                runtime.repository,
                context,
                tomato["id"],
                text="Lower leaves show mild yellowing; plant is otherwise upright after watering.",
                observed_facts=[{"label": "lower leaf yellowing", "source": "manual seed observation"}],
                lifecycle_stage_observed="vegetative",
                health_tags=["watch"],
            )
        )
    if not runtime.repository.list_research_projects(runtime.organization_id, runtime.workspace_id):
        runtime.repository.create_research_project(
            ResearchProject(
                organization_id=runtime.organization_id,
                workspace_id=runtime.workspace_id,
                title="Tomato manual alpha research",
                research_question="What evidence should guide Cherokee Purple Tomato care in a Texas garden?",
                status="ACTIVE",
                tags=["demo", "tomato"],
            )
        )
    if not runtime.repository.list_season_plans(runtime.organization_id, runtime.workspace_id):
        asyncio.run(
            post_season_plan(
                runtime.season,
                runtime.season_context_provider,
                context,
                workspace_id=runtime.workspace_id,
                location_id=demo_location_id,
                objective="Create a fall care plan for Cherokee Purple Tomato.",
                crop_names=["tomato"],
                start_date="2026-09-15",
                end_date="2026-12-15",
                timezone="America/Chicago",
            )
        )
    if _guidance_plan_count(runtime) == 0:
        runtime.repository.create_guidance_plan(
            GuidancePlan(
                organization_id=runtime.organization_id,
                workspace_id=runtime.workspace_id,
                user_plant_id=tomato["id"],
                subject="Seeded Cherokee Purple Tomato guidance",
                situation="Manual alpha seed data provides a starter plant, observation, and season context.",
                recommendations=[{"summary": "Inspect leaf yellowing and keep evidence separate from diagnosis.", "confidence": 0.6}],
                actions=[{"title": "Add a current photo before changing treatment.", "instructions": "Use Vision to capture visible evidence first."}],
                timing=[{"window": "today", "basis": "manual alpha seed"}],
                uncertainty={"level": "medium", "reasons": ["Starter guidance is fixture-backed seed data."]},
            )
        )
    return persistence_summary(runtime)


def ensure_demo_workspace(repository: GaiaRepository, organization_id: str) -> str:
    workspace = _workspace(repository.connection, organization_id, "Demo Workspace")
    if workspace is not None:
        return workspace["id"]
    created = repository.create_workspace(
        Workspace(
            organization_id=organization_id,
            name="Demo Workspace",
            purpose="explicit demo fixtures",
            knowledge_policy={"fixture_isolation": True, "demo_only": True},
        )
    )
    return created.id


def persistence_summary(runtime: GaiaRuntime) -> dict:
    plants = runtime.repository.list_user_plants(runtime.organization_id, runtime.workspace_id)
    observations = []
    for plant in plants:
        observations.extend(runtime.repository.list_observations(runtime.organization_id, plant["id"]))
    return {
        "status": "ok",
        "organization_id": runtime.organization_id,
        "workspace_id": runtime.workspace_id,
        "plant_count": len(plants),
        "observation_count": len(observations),
        "season_plan_count": len(runtime.repository.list_season_plans(runtime.organization_id, runtime.workspace_id)),
        "guidance_plan_count": _guidance_plan_count(runtime),
        "primary_location_id": runtime.primary_location_id,
        "database": runtime.database_url,
    }


async def set_active_location(
    runtime: GaiaRuntime,
    *,
    location_id: str | None = None,
    label: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    accuracy_m: float | None = None,
    source_kind: str = "manual",
) -> dict:
    if location_id:
        location = runtime.repository.get_location(runtime.organization_id, location_id)
        if location is None:
            raise PermissionError("Location is missing or inaccessible")
        if not _runtime_allows_demo_locations(runtime) and (bool(location.get("is_demo")) or location.get("source_kind") == "demo_fixture"):
            raise ValueError("demo_location_unavailable_in_normal_runtime")
    else:
        if latitude is None or longitude is None:
            raise ValueError("latitude_and_longitude_required")
        if source_kind not in {"device", "manual", "saved"}:
            raise ValueError("active_location_must_be_device_manual_or_saved")
        source_label = {
            "device": "browser geolocation permission",
            "manual": "user-entered location",
            "saved": "user-saved real location",
        }[source_kind]
        default_label = {
            "device": "Device location",
            "manual": "Manual location",
            "saved": "Saved location",
        }[source_kind]
        candidate = Location(
            organization_id=runtime.organization_id,
            label=label or default_label,
            latitude=latitude,
            longitude=longitude,
            accuracy_m=accuracy_m,
            privacy_precision="1km",
            exact_coordinates_authorized=source_kind == "device",
            timezone="UTC",
            country_code="US",
            source_kind=source_kind,
            source_label=source_label,
            is_demo=False,
            verified_at=now_iso(),
        )
        atlas_result = await runtime.atlas.build_geo_context(
            candidate,
            persist=False,
            context=runtime.context(request_id="atlas-active-location"),
        )
        geo = atlas_result.geo_context
        if not geo.state_code or not geo.county_or_district:
            raise ValueError("location_resolution_unavailable")
        location_obj = replace(
            candidate,
            timezone=geo.timezone or candidate.timezone,
            country_code=geo.country_code or candidate.country_code,
            admin1=geo.state_code,
            admin2=geo.county_or_district,
            county_fips=geo.county_fips,
            elevation_m=geo.elevation_m,
        )
        location = asdict(runtime.repository.create_location(location_obj))
        runtime.repository.create_geo_context(geo)
    runtime.repository.set_workspace_default_location(runtime.organization_id, runtime.workspace_id, location["id"])
    runtime.primary_location_id = location["id"]
    return {"status": "ok", "active_location": runtime.repository.get_location(runtime.organization_id, location["id"])}


def locations_payload(runtime: GaiaRuntime) -> dict:
    active = runtime.repository.get_location(runtime.organization_id, runtime.primary_location_id) if runtime.primary_location_id else None
    locations = runtime.repository.list_locations(runtime.organization_id)
    if not _runtime_allows_demo_locations(runtime):
        locations = [location for location in locations if _is_real_location(location)]
        if active is not None and not _is_real_location(active):
            active = None
    return {
        "active_location_id": active["id"] if active else None,
        "active_location": active,
        "locations": locations,
        "location_aliases": runtime.location_aliases if _runtime_allows_demo_locations(runtime) else {},
        "semantics": {
            "device": "Browser geolocation granted by the user for this local alpha session.",
            "manual": "Coordinates or place entered by the user.",
            "saved": "A real saved location selected by the user.",
            "demo_fixture": "Explicit demo/test location; never current device location.",
        },
    }


def _runtime_allows_demo_locations(runtime: GaiaRuntime) -> bool:
    if runtime.fixture_defaults:
        return True
    workspace = runtime.repository.get_workspace(runtime.organization_id, runtime.workspace_id) or {}
    return workspace.get("name") == "Demo Workspace" or bool((workspace.get("knowledge_policy") or {}).get("demo_only"))


def _is_real_location(location: dict) -> bool:
    return not bool(location.get("is_demo")) and location.get("source_kind") in {"device", "manual", "saved"}


def public_geography_for_location(runtime: GaiaRuntime, location_id: str | None) -> dict:
    if not location_id:
        return {}
    location = runtime.repository.get_location(runtime.organization_id, location_id)
    if not location:
        return {}
    return {
        key: value
        for key, value in {
            "country_code": location.get("country_code"),
            "state_code": location.get("admin1"),
            "county_or_district": location.get("admin2"),
            "county_fips": location.get("county_fips"),
        }.items()
        if value is not None
    }


def architecture_summary(runtime: GaiaRuntime) -> dict:
    return {
        "status": "ok",
        "orchestration": {
            "active_layer": "LangGraph GuidancePlan workflow" if runtime.orchestrator.graph_summary()["engine"] == "langgraph" else "LangGraph-compatible GuidancePlan workflow",
            "legacy_custom_orchestrator_preserved": True,
            "graph": runtime.orchestrator.graph_summary(),
            "routing": "deterministic route classification before model selection",
        },
        "guardrails": {
            "tool_calls": ["Tool Gateway", "Cost Firewall", "quota/cache", "provenance", "tenant/workspace checks", "egress policy", "audit/usage ledger"],
            "model_calls": ["Model Gateway", "Cost Firewall", "local/allowed providers only", "GuidancePlan validation", "audit/usage ledger"],
            "calendar_writes": "preview/commit approval gate preserved",
            "paid_paths": "disabled; no automatic paid provider, model, overage, telemetry, or storage path enabled",
        },
        "specialists": ["Atlas", "Terra", "Botanist", "Vision", "Scholar", "Sentinel", "Season", "Mercator"],
        "provider_modes": runtime.provider_modes.to_dict(),
        "location": locations_payload(runtime),
        "cash": cost_status(runtime),
    }


def source_inventory_rows(runtime: GaiaRuntime) -> list[dict]:
    modes = runtime.provider_modes.to_dict()
    stored_counts = _source_record_counts(runtime)
    rows = []
    for provider in runtime.registry.all():
        mode = provider_mode_for_provider(provider.provider_id, modes)
        if not provider.enabled:
            mode = "disabled"
        source_state = _source_state(provider.provider_id, mode)
        rows.append(
            {
                "provider_id": provider.provider_id,
                "display_name": provider.display_name,
                "source_type": provider.provider_type.value,
                "mode": mode,
                "source_state": source_state,
                "remote": provider.remote,
                "billing_class": provider.billing_class.value,
                "authentication": provider.authentication_requirement.value,
                "stored_source_records": stored_counts.get(provider.provider_id, 0),
                "terms_url": provider.license_metadata.terms_url,
                "license": provider.license_metadata.license,
                "attribution_required": provider.license_metadata.attribution_required,
                "smoke_tested": _source_smoke_tested(provider.provider_id, mode),
                "cash_status": "$0 automatic spend",
            }
        )
    rows.extend(_atlas_source_rows(runtime, stored_counts))
    return rows


def source_reconciliation_report(runtime: GaiaRuntime) -> dict:
    rows = source_inventory_rows(runtime)
    by_state: dict[str, int] = {}
    for row in rows:
        by_state[row["source_state"]] = by_state.get(row["source_state"], 0) + 1
    return {
        "status": "ok",
        "generated_at": now_iso(),
        "summary": by_state,
        "architecture": architecture_summary(runtime)["orchestration"],
        "rows": rows,
        "normal_runtime_rule": "live/free or fresh cache where supported; disabled/unavailable otherwise; fixtures only in tests or explicit demo mode",
        "cash_status": cost_status(runtime),
    }


def _source_record_counts(runtime: GaiaRuntime) -> dict[str, int]:
    rows = runtime.connection.execute(
        """
        SELECT provider, COUNT(*) AS count
        FROM source_records
        WHERE organization_id = ? AND deleted_at IS NULL
        GROUP BY provider
        """,
        (runtime.organization_id,),
    ).fetchall()
    return {row["provider"]: int(row["count"]) for row in rows}


def _source_state(provider_id: str, mode: str) -> str:
    if provider_id == "kew-powo" and mode == "disabled":
        return "documented-only"
    if mode == "live":
        return "live"
    if mode == "fixture":
        return "fixture"
    if mode == "local":
        return "local"
    return "disabled"


def _source_smoke_tested(provider_id: str, mode: str) -> bool:
    if mode == "fixture":
        return True
    return provider_id in {"nws", "nasa-power", "gbif", "europe-pmc", "aphis", "florida-fdacs"} and mode == "live"


def _atlas_source_rows(runtime: GaiaRuntime, stored_counts: dict[str, int]) -> list[dict]:
    return [
        {
            "provider_id": "gaia-local-admin-geography",
            "display_name": "GAIA local admin geography",
            "source_type": "GEOSPATIAL",
            "mode": "local",
            "source_state": "local",
            "remote": False,
            "billing_class": "LOCAL",
            "authentication": "LOCAL_ONLY",
            "stored_source_records": stored_counts.get("gaia-local-admin-geography", 0),
            "terms_url": None,
            "license": "local-deterministic",
            "attribution_required": False,
            "smoke_tested": True,
            "cash_status": "$0 automatic spend",
        }
    ]


def cost_status(runtime: GaiaRuntime) -> dict:
    status = CostStatusService(runtime.registry, runtime.usage_ledger, FinancialPolicy()).status()
    status["automatic_paid_usage_enabled"] = False
    status["automatic_overage_enabled"] = False
    status["reserve_remaining"] = status["configured_reserve"] - status["total_development_cash_spent"]
    return status


def runtime_status(runtime: GaiaRuntime, *, host: str = DEFAULT_ALPHA_HOST, port: int = DEFAULT_ALPHA_PORT) -> dict:
    return {
        "status": "ok",
        "name": "GAIA Local Alpha",
        "ui_url": f"http://{host}:{port}/",
        "api_url": f"http://{host}:{port}/api/v1",
        "database": "SQLite" if runtime.database_url.startswith("sqlite:///") else runtime.database_url,
        "database_url": runtime.database_url,
        "text_model": _runtime_text_model_label(runtime),
        "vision_model": _runtime_vision_model_label(runtime),
        "provider_modes": runtime.provider_modes.to_dict(),
        "spend_policy": "$0 automatic paid usage",
        "cash_spent": 0.0,
        "reserve": 20.0,
        "telemetry": os.environ.get("GAIA_TELEMETRY_MODE", "disabled"),
        "sovereign_mode": runtime.sovereign,
        "git_commit": _git_commit(),
        "development_identity": {
            "label": "Development Identity",
            "user_id": runtime.user_id,
            "organization_id": runtime.organization_id,
            "workspace_id": runtime.workspace_id,
        },
    }


def _runtime_text_model_label(runtime: GaiaRuntime) -> str:
    if runtime.provider_modes.text_model == "local":
        return runtime.text_model
    if runtime.provider_modes.text_model == "disabled":
        return "disabled"
    return "fixture-guidance-local"


def _runtime_vision_model_label(runtime: GaiaRuntime) -> str:
    if runtime.provider_modes.vision_model == "local":
        return runtime.vision_model
    if runtime.provider_modes.vision_model == "disabled":
        return "disabled"
    return "fixture-vision-local"


def provider_mode_for_provider(provider_id: str, modes: dict[str, str]) -> str:
    mapping = {
        "nasa-power": "nasa_power",
        "usda-nrcs-sda": "usda_soil",
        "usgs-water": "usgs_water",
        "kew-powo": "kew_powo",
        "genesys-pgr": "genesys_pgr",
        "europe-pmc": "europe_pmc",
        "texas-agriculture": "texas_agriculture",
        "florida-fdacs": "florida_fdacs",
        "usda-nass": "usda_nass",
        "usda-ams": "usda_ams",
        "google-calendar": "google_calendar",
        "ollama-local": "text_model",
        "ollama-llava-local": "vision_model",
    }
    return modes.get(mapping.get(provider_id, provider_id), "fixture")


def provider_health_rows(runtime: GaiaRuntime) -> list[dict]:
    modes = runtime.provider_modes.to_dict()
    rows = []
    for provider in runtime.registry.all():
        mode = provider_mode_for_provider(provider.provider_id, modes)
        if not provider.enabled:
            mode = "disabled"
        row = {
            "provider_id": provider.provider_id,
            "enabled": provider.enabled,
            "mode": mode,
            "remote": provider.remote,
            "health": HealthStatus.DISABLED.value if not provider.enabled else runtime.tool_gateway.health_monitor.status(provider.provider_id).value,
            "billing_class": provider.billing_class.value,
            "hard_monthly_usd": provider.cost_policy.hard_monthly_usd,
            "allow_overage": provider.cost_policy.allow_overage,
        }
        if provider.provider_id in runtime.live_regulatory_probes:
            row["live_probe"] = "read_only_official_pages"
            row["decision_source"] = "live_provenance_only_rules_unresolved"
        rows.append(row)
    return rows


def doctor_report(runtime: GaiaRuntime, *, host: str = DEFAULT_ALPHA_HOST, port: int = DEFAULT_ALPHA_PORT) -> dict:
    checks = [
        # sys.executable works on every platform; the Windows `py` launcher does not exist elsewhere.
        _command_check("Python", [sys.executable, "--version"]),
        _command_check("Node", ["node", "--version"]),
        _command_check("npm", ["npm", "--version"]),
        _command_check("Git", ["git", "--version"]),
        _docker_check(),
        _db_check(runtime),
        _ollama_check(runtime),
        _provider_mode_check(runtime),
        _cost_policy_check(runtime),
        _storage_check(),
        _reachability_check("UI", f"http://{host}:{port}/"),
        _reachability_check("API", f"http://{host}:{port}/api/v1/status"),
    ]
    worst = "ok"
    if any(check["state"] == "FAIL" for check in checks):
        worst = "fail"
    return {
        "status": worst,
        "checks": checks,
        "database": runtime.database_url,
        "sovereign_mode": runtime.sovereign,
        "provider_modes": runtime.provider_modes.to_dict(),
        "paid_providers_enabled": cost_status(runtime)["paid_providers_enabled"],
        "automatic_paid_usage_enabled": False,
        "automatic_overage_enabled": False,
        "private_egress_enabled": not runtime.sovereign,
        "remote_model_egress_enabled": False,
        "available_location_aliases": sorted(runtime.location_aliases),
    }


def connect_sqlite_url(database_url: str) -> sqlite3.Connection:
    if database_url in {":memory:", "sqlite:///:memory:"}:
        return connect_in_memory()
    if not database_url.startswith("sqlite:///"):
        raise ValueError("Only sqlite:/// database URLs are supported by the local alpha runtime.")
    raw_path = database_url.removeprefix("sqlite:///")
    path = Path(raw_path)
    if not path.is_absolute():
        path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_schema_if_empty(connection: sqlite3.Connection) -> None:
    row = connection.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type = 'table' AND name = 'organizations'
        LIMIT 1
        """
    ).fetchone()
    if row is None:
        initialize_schema(connection)
    ensure_runtime_schema(connection)


def ensure_runtime_schema(connection: sqlite3.Connection) -> None:
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(locations)").fetchall()}
    additions = {
        "source_kind": "ALTER TABLE locations ADD COLUMN source_kind TEXT NOT NULL DEFAULT 'saved'",
        "source_label": "ALTER TABLE locations ADD COLUMN source_label TEXT",
        "is_demo": "ALTER TABLE locations ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0",
        "verified_at": "ALTER TABLE locations ADD COLUMN verified_at TEXT",
    }
    for column, statement in additions.items():
        if column not in columns:
            connection.execute(statement)
    connection.commit()


def build_provider_registry(modes: AlphaProviderModes) -> ProviderRegistry:
    return ProviderRegistry(
        [
            _provider("census-geocoder", "U.S. Census Bureau Geocoder", ProviderType.GEOGRAPHY, "U.S. Census Bureau", modes.atlas_geography, FreshnessClass.LONG, "US"),
            _provider("nws", "National Weather Service", ProviderType.WEATHER, "NOAA/NWS", modes.nws, FreshnessClass.SHORT, "US"),
            _provider("nasa-power", "NASA POWER", ProviderType.CLIMATE, "NASA", modes.nasa_power, FreshnessClass.MEDIUM),
            _provider("usda-nrcs-sda", "USDA NRCS Soil Data Access", ProviderType.SOIL, "USDA NRCS", modes.usda_soil, FreshnessClass.LONG, "US"),
            _provider("usgs-water", "USGS Water", ProviderType.WATER, "USGS", modes.usgs_water, FreshnessClass.REALTIME, "US"),
            _provider("gbif", "GBIF", ProviderType.TAXONOMY, "GBIF", modes.gbif, FreshnessClass.LONG),
            _provider(
                "kew-powo",
                "Kew POWO / WCVP",
                ProviderType.TAXONOMY,
                "Royal Botanic Gardens, Kew",
                modes.kew_powo,
                FreshnessClass.LONG,
                license_metadata=LicenseMetadata(
                    terms_url="https://www.kew.org/about-us/terms-and-conditions",
                    license="Kew terms and dataset-specific rights",
                    commercial_use="review terms before product use",
                    redistribution="dataset-specific",
                    caching="respect terms, attribution, and traffic limits",
                    derivative_use="allowed only within terms and source licenses",
                    model_training="not enabled by GAIA",
                    attribution_required=True,
                    review_notes="POWO/WCVP source family is first-class but disabled by default until access path is explicitly approved.",
                ),
            ),
            _provider("genesys-pgr", "Genesys PGR", ProviderType.GERMPLASM, "Genesys PGR", modes.genesys_pgr, FreshnessClass.LONG, authentication=AuthenticationRequirement.OAUTH),
            _provider("europe-pmc", "Europe PMC", ProviderType.RESEARCH, "Europe PMC", modes.europe_pmc, FreshnessClass.MEDIUM),
            _provider("aphis", "APHIS", ProviderType.REGULATION, "USDA APHIS", modes.aphis, FreshnessClass.REGULATORY_CURRENT, "US"),
            _provider("texas-agriculture", "Texas Department of Agriculture", ProviderType.REGULATION, "Texas Department of Agriculture", modes.texas_agriculture, FreshnessClass.REGULATORY_CURRENT, "US/TX"),
            _provider("florida-fdacs", "Florida FDACS", ProviderType.REGULATION, "FDACS Division of Plant Industry", modes.florida_fdacs, FreshnessClass.REGULATORY_CURRENT, "US/FL"),
            _provider("usda-nass", "USDA NASS Quick Stats", ProviderType.MARKET, "USDA NASS", modes.usda_nass, FreshnessClass.MEDIUM, "US", authentication=AuthenticationRequirement.OPTIONAL_API_KEY),
            _provider("usda-ams", "USDA AMS MyMarketNews", ProviderType.MARKET, "USDA AMS", modes.usda_ams, FreshnessClass.SHORT, "US", authentication=AuthenticationRequirement.OPTIONAL_API_KEY),
            _provider("fixture-calendar", "Fixture Calendar", ProviderType.CALENDAR, "local", "fixture", FreshnessClass.STATIC, remote=False, authentication=AuthenticationRequirement.LOCAL_ONLY),
            _provider("google-calendar", "Google Calendar", ProviderType.CALENDAR, "Google", modes.google_calendar, FreshnessClass.SHORT, authentication=AuthenticationRequirement.OAUTH),
            _provider("plantnet", "Pl@ntNet", ProviderType.VISION, "Pl@ntNet", modes.plantnet, FreshnessClass.SHORT, authentication=AuthenticationRequirement.REQUIRED_API_KEY),
            _provider("ollama-local", "Local Ollama", ProviderType.MODEL, "local", modes.text_model, FreshnessClass.STATIC, remote=False, authentication=AuthenticationRequirement.LOCAL_ONLY),
            _provider("ollama-llava-local", "Local Ollama LLaVA", ProviderType.VISION, "local", modes.vision_model, FreshnessClass.STATIC, remote=False, authentication=AuthenticationRequirement.LOCAL_ONLY),
            _provider("fixture-vision-local", "Fixture Vision", ProviderType.VISION, "local", "fixture" if modes.vision_model == "fixture" else "disabled", FreshnessClass.STATIC, remote=False, authentication=AuthenticationRequirement.LOCAL_ONLY),
            _manual_paid_provider(),
        ]
    )


def _provider(
    provider_id: str,
    display_name: str,
    provider_type: ProviderType,
    authority: str,
    mode: ProviderMode,
    freshness_class: FreshnessClass,
    geographic_scope: str = "global",
    *,
    remote: bool = True,
    authentication: AuthenticationRequirement = AuthenticationRequirement.NONE,
    license_metadata: LicenseMetadata | None = None,
) -> ProviderRecord:
    enabled = mode != "disabled"
    billing = BillingClass.LOCAL if not remote else BillingClass.FREE
    return ProviderRecord(
        provider_id=provider_id,
        display_name=display_name,
        provider_type=provider_type,
        authority=authority,
        enabled=enabled,
        billing_class=billing,
        cost_policy=ProviderCostPolicy(provider_id=provider_id, billing_class=billing.value, hard_monthly_usd=0.0, allow_overage=False),
        quota_policy=ProviderQuotaPolicy(daily_requests=100),
        authentication_requirement=authentication,
        geographic_scope=geographic_scope,
        cache_policy=CachePolicy(freshness_class=freshness_class, ttl_seconds=3600, stale_if_error_seconds=86400),
        license_metadata=license_metadata or LicenseMetadata(),
        attribution=authority,
        health_status=HealthStatus.UNKNOWN if enabled else HealthStatus.DISABLED,
        remote=remote and mode == "live",
    )


def _manual_paid_provider() -> ProviderRecord:
    return ProviderRecord(
        provider_id="future-paid-provider",
        display_name="Future Paid Provider",
        provider_type=ProviderType.MODEL,
        authority="manual future provider",
        enabled=False,
        billing_class=BillingClass.MANUAL_PAID,
        cost_policy=ProviderCostPolicy(provider_id="future-paid-provider", billing_class="MANUAL_PAID", hard_monthly_usd=0.0, allow_overage=False),
        quota_policy=ProviderQuotaPolicy(daily_requests=0),
        authentication_requirement=AuthenticationRequirement.REQUIRED_API_KEY,
        geographic_scope="future",
        cache_policy=CachePolicy(FreshnessClass.SHORT),
        license_metadata=LicenseMetadata(),
        attribution="manual future provider",
        health_status=HealthStatus.DISABLED,
        remote=True,
    )


class CLIGeographyProvider:
    def __init__(self, *, fixture: bool = True) -> None:
        self.fixture = fixture
        self.provider_id = "fixture-cli-geography" if fixture else "gaia-local-admin-geography"

    async def resolve_admin(self, latitude: float, longitude: float, at_time: str | None = None) -> AdminResolution:
        if 33.5 <= latitude <= 35.5 and -119.0 <= longitude <= -117.0:
            return self._admin("California", "CA", "Los Angeles County", "06037", "America/Los_Angeles")
        if 30.0 <= latitude <= 34.9 and -86.0 <= longitude <= -80.0:
            return self._admin("Georgia", "GA", "Fulton County", "13121", "America/New_York")
        if 25.7 <= latitude <= 26.4 and -80.6 <= longitude <= -80.0:
            return self._admin("Florida", "FL", "Broward County", "12011", "America/New_York")
        if 27.0 <= latitude <= 29.5 and -83.0 <= longitude <= -80.0:
            return self._admin("Florida", "FL", "Orange County", "12095", "America/New_York")
        if 29.0 <= latitude <= 30.2 and -96.0 <= longitude <= -94.0:
            return self._admin("Texas", "TX", "Harris County", "48201", "America/Chicago")
        if 25.0 <= latitude <= 27.0 and -99.0 <= longitude <= -96.0:
            return self._admin("Texas", "TX", "Hidalgo County", "48215", "America/Chicago")
        if not self.fixture:
            return self._unresolved(latitude, longitude)
        return self._admin("Texas", "TX", "Travis County", "48453", "America/Chicago")

    def _admin(self, state: str, state_code: str, county: str, fips: str, timezone: str) -> AdminResolution:
        return AdminResolution(
            status=ProviderStatus("AVAILABLE"),
            country="United States",
            country_code="US",
            state_or_region=state,
            state_code=state_code,
            county_or_district=county,
            county_fips=fips,
            timezone=timezone,
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    external_record_id=f"US:{state_code}:{county}",
                    canonical_url="fixture://cli/geography" if self.fixture else "local://gaia/admin-geography",
                    authority="GAIA CLI fixture geography" if self.fixture else "GAIA local deterministic admin geography",
                    geographic_scope=f"US/{state_code}/{county}",
                    license="fixture" if self.fixture else "local-deterministic",
                    attribution="GAIA fixture" if self.fixture else "GAIA local deterministic resolver",
                    content_hash=content_hash([state_code, county]),
                )
            ],
        )

    def _unresolved(self, latitude: float, longitude: float) -> AdminResolution:
        return AdminResolution(
            status=ProviderStatus("UNAVAILABLE", "coordinate_outside_local_admin_fixture_coverage"),
            country=None,
            country_code=None,
            state_or_region=None,
            state_code=None,
            county_or_district=None,
            county_fips=None,
            timezone=None,
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    external_record_id=f"unresolved:{round(latitude, 4)}:{round(longitude, 4)}",
                    canonical_url="local://gaia/admin-geography/unresolved",
                    authority="GAIA local deterministic admin geography",
                    geographic_scope="unresolved",
                    license="local-deterministic",
                    attribution="GAIA local deterministic resolver",
                    content_hash=content_hash([latitude, longitude, "unresolved"]),
                )
            ],
        )


class CLIRegulatoryGeometryProvider:
    def __init__(self, *, fixture: bool = True) -> None:
        self.fixture = fixture
        self.provider_id = "fixture-cli-regulatory-geometry" if fixture else "gaia-local-regulatory-geometry"

    async def resolve_zones(self, latitude: float, longitude: float, at_time: str | None = None) -> RegulatoryZoneResolution:
        regulatory_zones = [AtlasZone("us-federal", "jurisdiction", "United States federal jurisdiction", "USDA APHIS")]
        quarantine_zones = []
        if 29.0 <= latitude <= 30.2 and -96.0 <= longitude <= -94.0:
            quarantine_zones.append(AtlasZone("tx-hlb-gulf-coast", "quarantine", "Texas Citrus Greening Gulf Coast Quarantined Area", "Texas Department of Agriculture"))
        if 25.0 <= latitude <= 27.0 and -99.0 <= longitude <= -96.0:
            regulatory_zones.append(AtlasZone("tx-citrus-zone", "regulated_zone", "Texas Citrus Zone", "Texas Department of Agriculture"))
        if 27.0 <= latitude <= 29.5 and -83.0 <= longitude <= -80.0:
            quarantine_zones.append(AtlasZone("fl-citrus-statewide", "quarantine", "Florida citrus regulated area", "FDACS"))
        if 25.7 <= latitude <= 26.4 and -80.6 <= longitude <= -80.0:
            quarantine_zones.append(AtlasZone("fl-gals-broward", "quarantine", "Broward County giant African land snail quarantine fixture", "FDACS"))
        return RegulatoryZoneResolution(
            status=ProviderStatus("AVAILABLE"),
            regulatory_zones=regulatory_zones,
            quarantine_zones=quarantine_zones,
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    external_record_id="fixture-cli-zones",
                    canonical_url="fixture://cli/zones" if self.fixture else "local://gaia/regulatory-geometry",
                    authority="GAIA CLI fixture regulatory geometry" if self.fixture else "GAIA local regulatory geometry",
                    geographic_scope="US",
                    license="fixture" if self.fixture else "local-deterministic",
                    attribution="GAIA fixture" if self.fixture else "GAIA local deterministic resolver",
                    content_hash=content_hash([latitude, longitude]),
                )
            ],
        )


def _fixture_defaults_for_runtime(database_url: str) -> bool:
    env_mode = os.environ.get("GAIA_RUNTIME_MODE", "").strip().lower()
    if env_mode in {"demo", "fixture", "fixtures", "test"}:
        return True
    if env_mode in {"normal", "manual-alpha", "manual_alpha", "live"}:
        return False
    return database_url in {":memory:", "sqlite:///:memory:"}


def _fixture_provider_defaults() -> dict[str, ProviderMode]:
    return {
        "atlas_geography": "fixture",
        "nws": "fixture",
        "nasa_power": "fixture",
        "usda_soil": "fixture",
        "usgs_water": "fixture",
        "gbif": "fixture",
        "kew_powo": "disabled",
        "genesys_pgr": "fixture",
        "europe_pmc": "fixture",
        "aphis": "fixture",
        "texas_agriculture": "fixture",
        "florida_fdacs": "fixture",
        "usda_nass": "fixture",
        "usda_ams": "fixture",
        "plantnet": "disabled",
        "google_calendar": "disabled",
        "text_model": "local",
        "vision_model": "local",
    }


def _normal_provider_defaults() -> dict[str, ProviderMode]:
    return {
        "atlas_geography": "live",
        "nws": "live",
        "nasa_power": "live",
        "usda_soil": "disabled",
        "usgs_water": "disabled",
        "gbif": "live",
        "kew_powo": "disabled",
        "genesys_pgr": "disabled",
        "europe_pmc": "live",
        "aphis": "disabled",
        "texas_agriculture": "disabled",
        "florida_fdacs": "disabled",
        "usda_nass": "live" if (os.environ.get("GAIA_NASS_API_KEY") or os.environ.get("USDA_NASS_API_KEY")) else "disabled",
        "usda_ams": "live" if (os.environ.get("GAIA_AMS_API_KEY") or os.environ.get("USDA_AMS_API_KEY")) else "disabled",
        "plantnet": "disabled",
        "google_calendar": "disabled",
        "text_model": "local",
        "vision_model": "local",
    }


def _mode(key: str, default: ProviderMode) -> ProviderMode:
    value = os.environ.get(key, default).strip().lower().replace("-", "_")
    normalized = {"local_ollama": "local", "off": "disabled", "none": "disabled"}.get(value, value)
    if normalized not in {"fixture", "live", "disabled", "local"}:
        return default
    return normalized  # type: ignore[return-value]


def _nws_provider(modes: AlphaProviderModes):
    if modes.nws == "live":
        return NWSApiAdapter(os.environ.get("NWS_USER_AGENT") or "GAIA Local Alpha/0.1")
    if modes.nws == "disabled":
        return DisabledWeatherProvider()
    return FixtureNWSProvider()


def _nasa_power_provider(modes: AlphaProviderModes):
    if modes.nasa_power == "live":
        return NASAPowerApiAdapter(base_url=os.environ.get("NASA_POWER_BASE_URL"))
    if modes.nasa_power == "disabled":
        return DisabledClimateProvider()
    return FixtureNASAPowerProvider()


def _soil_provider(modes: AlphaProviderModes):
    if modes.usda_soil == "live":
        return USDASoilDataAccessAdapter(user_agent=os.environ.get("SSURGO_USER_AGENT") or "GAIA Local Alpha/0.1")
    if modes.usda_soil == "fixture":
        return FixtureUSDASoilProvider()
    return DisabledSoilSurveyProvider()


def _water_provider(modes: AlphaProviderModes):
    if modes.usgs_water == "fixture":
        return FixtureUSGSWaterProvider()
    return DisabledWaterProvider()


def _gbif_provider(modes: AlphaProviderModes):
    if modes.gbif == "live":
        return GBIFApiAdapter(user_agent=os.environ.get("GBIF_USER_AGENT") or "GAIA Local Alpha/0.1")
    if modes.gbif == "disabled":
        provider = DisabledTaxonomyProvider()
        provider.provider_id = "gbif"
        return provider
    return FixtureGBIFProvider()


def _kew_provider(modes: AlphaProviderModes):
    if modes.kew_powo == "live":
        return KewPOWOApiAdapter(user_agent=os.environ.get("KEW_USER_AGENT") or os.environ.get("GBIF_USER_AGENT") or "GAIA Local Alpha/0.1")
    provider = DisabledTaxonomyProvider()
    provider.provider_id = "kew-powo"
    return provider


def _genesys_provider(modes: AlphaProviderModes):
    if modes.genesys_pgr == "live":
        return GenesysPGRAdapter(
            user_agent=os.environ.get("GENESYS_USER_AGENT") or "GAIA Local Alpha/0.1",
            client_id=os.environ.get("GENESYS_CLIENT_ID"),
            client_secret=os.environ.get("GENESYS_CLIENT_SECRET"),
        )
    if modes.genesys_pgr == "fixture":
        return FixtureGenesysProvider()
    provider = DisabledGermplasmProvider()
    provider.provider_id = "genesys-pgr"
    return provider


def _research_provider(modes: AlphaProviderModes):
    if modes.europe_pmc == "live":
        return EuropePMCAdapter()
    if modes.europe_pmc == "fixture":
        return FixtureResearchProvider()
    return DisabledResearchProvider()


def _nass_provider(modes: AlphaProviderModes):
    if modes.usda_nass == "live":
        return NASSQuickStatsProvider()
    if modes.usda_nass == "fixture":
        return FixtureNASSProvider()
    provider = DisabledEconomicProvider()
    provider.provider_id = "usda-nass"
    return provider


def _ams_provider(modes: AlphaProviderModes):
    if modes.usda_ams == "live":
        return AMSMyMarketNewsProvider()
    if modes.usda_ams == "fixture":
        return FixtureAMSProvider()
    provider = DisabledEconomicProvider()
    provider.provider_id = "usda-ams"
    return provider


def _aphis_provider(modes: AlphaProviderModes):
    if modes.aphis == "live":
        return ReadOnlyRegulatoryPageAdapter(
            provider_id="aphis",
            authority="USDA APHIS",
            urls=(APHIS_CITRUS_URL, APHIS_IMPORT_URL),
            timeout_seconds=20,
        )
    return FixtureAPHISProvider()


def _texas_regulatory_provider(modes: AlphaProviderModes):
    if modes.texas_agriculture == "live":
        return ReadOnlyRegulatoryPageAdapter(
            provider_id="texas-agriculture",
            authority="Texas Department of Agriculture",
            urls=(TEXAS_CITRUS_URL, TEXAS_GREENING_URL),
            timeout_seconds=20,
        )
    return FixtureTexasAgricultureProvider()


def _florida_regulatory_provider(modes: AlphaProviderModes):
    if modes.florida_fdacs == "live":
        return ReadOnlyRegulatoryPageAdapter(
            provider_id="florida-fdacs",
            authority="Florida Department of Agriculture and Consumer Services",
            urls=(FDACS_PLANT_INSPECTION_URL, FDACS_CITRUS_QUARANTINE_URL, FDACS_IMPORT_REGULATIONS_URL),
            timeout_seconds=20,
        )
    return FixtureFloridaFDACSProvider()


def _live_regulatory_probes(modes: AlphaProviderModes) -> dict[str, ReadOnlyRegulatoryPageAdapter]:
    probes: dict[str, ReadOnlyRegulatoryPageAdapter] = {}
    if modes.aphis == "live":
        probes["aphis"] = ReadOnlyRegulatoryPageAdapter(
            provider_id="aphis",
            authority="USDA APHIS",
            urls=(APHIS_CITRUS_URL, APHIS_IMPORT_URL),
            timeout_seconds=20,
        )
    if modes.texas_agriculture == "live":
        probes["texas-agriculture"] = ReadOnlyRegulatoryPageAdapter(
            provider_id="texas-agriculture",
            authority="Texas Department of Agriculture",
            urls=(TEXAS_CITRUS_URL, TEXAS_GREENING_URL),
            timeout_seconds=20,
        )
    if modes.florida_fdacs == "live":
        probes["florida-fdacs"] = ReadOnlyRegulatoryPageAdapter(
            provider_id="florida-fdacs",
            authority="Florida Department of Agriculture and Consumer Services",
            urls=(FDACS_PLANT_INSPECTION_URL, FDACS_CITRUS_QUARANTINE_URL, FDACS_IMPORT_REGULATIONS_URL),
            timeout_seconds=20,
        )
    return probes


def _text_model_provider(modes: AlphaProviderModes):
    if modes.text_model == "local":
        return OllamaModelProvider(model=os.environ.get("GAIA_OLLAMA_MODEL", "llama3.1:latest"), base_url=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    return FixtureGuidanceModelProvider()


def _vision_provider(modes: AlphaProviderModes):
    if modes.vision_model == "local":
        return OllamaLlavaVisionProvider(model=os.environ.get("GAIA_LLAVA_MODEL", "llava:latest"), base_url=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    if modes.vision_model == "disabled":
        return DisabledVisionProvider()
    return FixtureVisionProvider()


def _vision_provider_id(modes: AlphaProviderModes) -> str:
    if modes.vision_model == "fixture":
        return "fixture-vision-local"
    return "ollama-llava-local"


def _find_one(connection: sqlite3.Connection, table: str, column: str, value: str) -> dict | None:
    row = connection.execute(f"SELECT * FROM {table} WHERE {column} = ? AND deleted_at IS NULL LIMIT 1", (value,)).fetchone()
    return dict(row) if row else None


def _find_user(connection: sqlite3.Connection, external_auth_id: str) -> dict | None:
    row = connection.execute("SELECT * FROM users WHERE external_auth_id = ? AND deleted_at IS NULL LIMIT 1", (external_auth_id,)).fetchone()
    return dict(row) if row else None


def _membership(connection: sqlite3.Connection, organization_id: str, user_id: str) -> dict | None:
    row = connection.execute(
        "SELECT * FROM memberships WHERE organization_id = ? AND user_id = ? AND deleted_at IS NULL LIMIT 1",
        (organization_id, user_id),
    ).fetchone()
    return dict(row) if row else None


def _workspace(connection: sqlite3.Connection, organization_id: str, name: str) -> dict | None:
    row = connection.execute(
        "SELECT * FROM workspaces WHERE organization_id = ? AND name = ? AND deleted_at IS NULL LIMIT 1",
        (organization_id, name),
    ).fetchone()
    return dict(row) if row else None


def _location(connection: sqlite3.Connection, organization_id: str, label: str) -> dict | None:
    row = connection.execute(
        "SELECT * FROM locations WHERE organization_id = ? AND label = ? AND deleted_at IS NULL LIMIT 1",
        (organization_id, label),
    ).fetchone()
    return dict(row) if row else None


def _calendar_binding(connection: sqlite3.Connection, organization_id: str, user_id: str) -> dict | None:
    row = connection.execute(
        """
        SELECT * FROM calendar_bindings
        WHERE organization_id = ? AND user_id = ? AND provider = 'fixture-calendar' AND deleted_at IS NULL
        LIMIT 1
        """,
        (organization_id, user_id),
    ).fetchone()
    return dict(row) if row else None


def _guidance_plan_count(runtime: GaiaRuntime) -> int:
    row = runtime.connection.execute(
        """
        SELECT COUNT(*) AS count FROM guidance_plans
        WHERE organization_id = ? AND workspace_id = ? AND deleted_at IS NULL
        """,
        (runtime.organization_id, runtime.workspace_id),
    ).fetchone()
    return int(row["count"])


def _command_check(name: str, command: list[str]) -> dict:
    resolved = shutil.which(command[0])
    if resolved is None:
        return {"name": name, "state": "FAIL", "detail": f"{command[0]} not found"}
    try:
        result = subprocess.run([resolved, *command[1:]], cwd=ROOT, capture_output=True, text=True, timeout=10, check=False)
    except Exception as exc:
        return {"name": name, "state": "FAIL", "detail": exc.__class__.__name__}
    detail = (result.stdout or result.stderr).strip().splitlines()[0] if (result.stdout or result.stderr).strip() else "available"
    return {"name": name, "state": "PASS" if result.returncode == 0 else "FAIL", "detail": detail}


def _docker_check() -> dict:
    if shutil.which("docker") is None:
        return {"name": "Docker engine", "state": "DISABLED", "detail": "Docker CLI not found"}
    result = subprocess.run(["docker", "version"], cwd=ROOT, capture_output=True, text=True, timeout=15, check=False)
    if result.returncode == 0:
        return {"name": "Docker engine", "state": "PASS", "detail": "Docker engine available"}
    detail = (result.stderr or result.stdout).strip().splitlines()[-1] if (result.stderr or result.stdout).strip() else "Docker engine unavailable"
    return {"name": "Docker engine", "state": "WARN", "detail": detail}


def _db_check(runtime: GaiaRuntime) -> dict:
    try:
        runtime.connection.execute("SELECT 1").fetchone()
        return {"name": "Database", "state": "PASS", "detail": runtime.database_url}
    except sqlite3.Error as exc:
        return {"name": "Database", "state": "FAIL", "detail": str(exc)}


def _ollama_check(runtime: GaiaRuntime) -> dict:
    if shutil.which("ollama") is None:
        return {"name": "Ollama", "state": "WARN", "detail": "ollama command not found"}
    try:
        with urllib.request.urlopen(os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/") + "/api/tags", timeout=3) as response:
            text = response.read().decode("utf-8")
    except Exception as exc:
        return {"name": "Ollama", "state": "WARN", "detail": f"not reachable: {exc.__class__.__name__}"}
    detail = []
    if runtime.text_model in text:
        detail.append(runtime.text_model)
    if runtime.vision_model in text:
        detail.append(runtime.vision_model)
    return {"name": "Ollama", "state": "PASS" if detail else "WARN", "detail": ", ".join(detail) or "reachable; configured models not listed"}


def _provider_mode_check(runtime: GaiaRuntime) -> dict:
    paid_enabled = any(provider.enabled and provider.billing_class == BillingClass.MANUAL_PAID for provider in runtime.registry.all())
    if paid_enabled:
        return {"name": "Provider modes", "state": "FAIL", "detail": "paid provider enabled"}
    return {"name": "Provider modes", "state": "PASS", "detail": runtime.provider_modes.to_dict()}


def _cost_policy_check(runtime: GaiaRuntime) -> dict:
    status = cost_status(runtime)
    if status["paid_providers_enabled"] or status["current_estimated_external_spend"] > 0:
        return {"name": "Cost Firewall", "state": "FAIL", "detail": status}
    return {"name": "Cost Firewall", "state": "PASS", "detail": "Automatic paid usage OFF; spend $0.00; reserve $20.00"}


def _storage_check() -> dict:
    path = ROOT / "local_data"
    try:
        path.mkdir(exist_ok=True)
    except OSError as exc:
        return {"name": "Storage path", "state": "FAIL", "detail": str(exc)}
    return {"name": "Storage path", "state": "PASS", "detail": str(path)}


def _reachability_check(name: str, url: str) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=1) as response:
            return {"name": name, "state": "PASS", "detail": f"HTTP {response.status}: {url}"}
    except urllib.error.URLError:
        return {"name": name, "state": "DISABLED", "detail": f"not running at {url}"}
    except Exception as exc:
        return {"name": name, "state": "WARN", "detail": f"{exc.__class__.__name__}: {url}"}


def _git_commit() -> str:
    try:
        result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=5, check=False)
    except Exception:
        return "unknown"
    return result.stdout.strip() or "unknown"
