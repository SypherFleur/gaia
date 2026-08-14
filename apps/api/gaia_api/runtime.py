from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

from packages.audit import AuditLog, UsageLedger
from packages.botany import (
    BotanistService,
    FixtureGBIFProvider,
    FixtureGenesysProvider,
    GBIFApiAdapter,
    GBIFTaxonomyTool,
    GenesysGermplasmTool,
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
from packages.environment.live_adapters import NASAPowerApiAdapter, NWSApiAdapter
from packages.environment.tools import NASAPowerClimateTool, NWSForecastTool, USDASoilSurveyTool, USGSWaterSitesTool
from packages.geospatial import AtlasService
from packages.geospatial.providers import (
    AdminResolution,
    AtlasZone,
    FixtureHardinessProvider,
    FixtureWatershedProvider,
    ProviderStatus,
    RegulatoryZoneResolution,
)
from packages.mercator import (
    AMSMarketReportTool,
    AMSSupplyChainTool,
    FixtureAMSProvider,
    FixtureNASSProvider,
    MercatorContextProvider,
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
from packages.research import EuropePMCFetchTool, EuropePMCSearchTool, FixtureResearchProvider, FixtureScholarModelProvider, ScholarService
from packages.research.europe_pmc import EuropePMCAdapter
from packages.season import DeterministicSeasonPlanner, SeasonContextProvider, SeasonService
from packages.sentinel import (
    FixtureAPHISProvider,
    FixtureFloridaFDACSProvider,
    FixtureTexasAgricultureProvider,
    JurisdictionPack,
    JurisdictionPackMetadata,
    JurisdictionPackRegistry,
    RegulationMovementRulesTool,
    RegulationPestAlertsTool,
    SentinelService,
    USStateJurisdictionPack,
)
from packages.status import CostStatusService
from packages.tools import ToolExecutionContext, ToolGateway
from packages.vision import FixtureVisionProvider, OllamaLlavaVisionProvider, VisionAnalysisTool, VisionService


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SQLITE_URL = "sqlite:///./local_data/gaia.sqlite3"
DEFAULT_ALPHA_HOST = "127.0.0.1"
DEFAULT_ALPHA_PORT = 8765

ProviderMode = Literal["fixture", "live", "disabled", "local"]


@dataclass(frozen=True, slots=True)
class AlphaProviderModes:
    nws: ProviderMode = "fixture"
    nasa_power: ProviderMode = "fixture"
    gbif: ProviderMode = "fixture"
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
    def from_environment(cls) -> "AlphaProviderModes":
        return cls(
            nws=_mode("GAIA_NWS_MODE", "fixture"),
            nasa_power=_mode("GAIA_NASA_POWER_MODE", "fixture"),
            gbif=_mode("GAIA_GBIF_MODE", "fixture"),
            genesys_pgr=_mode("GAIA_GENESYS_MODE", "fixture"),
            europe_pmc=_mode("GAIA_EUROPE_PMC_MODE", "fixture"),
            aphis=_mode("GAIA_APHIS_MODE", "fixture"),
            texas_agriculture=_mode("GAIA_TEXAS_AGRICULTURE_MODE", "fixture"),
            florida_fdacs=_mode("GAIA_FLORIDA_FDACS_MODE", "fixture"),
            usda_nass=_mode("GAIA_NASS_MODE", "fixture"),
            usda_ams=_mode("GAIA_AMS_MODE", "fixture"),
            plantnet=_mode("GAIA_PLANTNET_MODE", "disabled"),
            google_calendar=_mode("GAIA_GOOGLE_CALENDAR_MODE", "disabled"),
            text_model=_mode("GAIA_TEXT_MODEL_MODE", "local"),
            vision_model=_mode("GAIA_VISION_MODEL_MODE", "local"),
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
    primary_location_id: str
    calendar_binding_id: str
    location_aliases: dict[str, str]
    provider_modes: AlphaProviderModes
    database_url: str = DEFAULT_SQLITE_URL
    sovereign: bool = False
    text_model: str = "llama3.1:latest"
    vision_model: str = "llava:latest"

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
    modes = provider_modes or AlphaProviderModes.from_environment()
    connection = connect_sqlite_url(database)
    initialize_schema_if_empty(connection)
    repository = GaiaRepository(connection)
    identity = ensure_development_identity(repository, sovereign=sovereign)

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

    atlas = AtlasService(repository, CLIGeographyProvider(), FixtureWatershedProvider(), FixtureHardinessProvider(), CLIRegulatoryGeometryProvider())
    terra = TerraService(
        repository,
        tool_gateway,
        NWSForecastTool(_nws_provider(modes)),
        NASAPowerClimateTool(_nasa_power_provider(modes)),
        USDASoilSurveyTool(FixtureUSDASoilProvider()),
        USGSWaterSitesTool(FixtureUSGSWaterProvider()),
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
        GenesysGermplasmTool(FixtureGenesysProvider()),
    )
    vision_tool = VisionAnalysisTool(_vision_provider(modes), provider_id=_vision_provider_id(modes))
    vision = VisionService(repository=repository, tool_gateway=tool_gateway, context_compiler=context_compiler, botanist=botanist)

    research_provider = EuropePMCAdapter() if modes.europe_pmc == "live" else FixtureResearchProvider()
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

    aphis = FixtureAPHISProvider()
    texas = FixtureTexasAgricultureProvider()
    florida = FixtureFloridaFDACSProvider()
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
        nass_production_tool=NASSProductionTool(FixtureNASSProvider()),
        nass_region_tool=NASSRegionalContextTool(FixtureNASSProvider()),
        ams_market_tool=AMSMarketReportTool(FixtureAMSProvider()),
        ams_supply_chain_tool=AMSSupplyChainTool(FixtureAMSProvider()),
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
        text_model=os.environ.get("GAIA_OLLAMA_MODEL", "llama3.1:latest"),
        vision_model=os.environ.get("GAIA_LLAVA_MODEL", "llava:latest"),
    )


def ensure_development_identity(repository: GaiaRepository, *, sovereign: bool = False) -> dict:
    organization = _find_one(repository.connection, "organizations", "slug", "gaia-local-alpha")
    if organization is None:
        organization_obj = repository.create_organization(
            Organization(name="GAIA Local Alpha", slug="gaia-local-alpha", deployment_mode="sovereign" if sovereign else "local")
        )
        organization_id = organization_obj.id
    else:
        organization_id = organization["id"]

    user = _find_user(repository.connection, "development:jason")
    if user is None:
        user_obj = repository.create_user(User(external_auth_id="development:jason", display_name="Jason Development Identity", timezone="America/Chicago"))
        user_id = user_obj.id
    else:
        user_id = user["id"]

    if _membership(repository.connection, organization_id, user_id) is None:
        repository.create_membership(
            Membership(
                organization_id=organization_id,
                user_id=user_id,
                role="owner",
                permissions=["tool.read", "regulation.read", "vision.analyze", "model.chat", "calendar.create"],
            )
        )

    workspace = _workspace(repository.connection, organization_id, "Alpha Workspace")
    if workspace is None:
        workspace_obj = repository.create_workspace(Workspace(organization_id=organization_id, name="Alpha Workspace", purpose="manual local alpha"))
        workspace_id = workspace_obj.id
    else:
        workspace_id = workspace["id"]

    aliases = seed_cli_locations(repository, organization_id)
    primary_location_id = aliases["tx-austin"]
    repository.connection.execute(
        "UPDATE workspaces SET default_location_id = ?, updated_at = ? WHERE id = ?",
        (primary_location_id, now_iso(), workspace_id),
    )
    repository.connection.commit()

    calendar_binding = _calendar_binding(repository.connection, organization_id, user_id)
    if calendar_binding is None:
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
        "tx-austin": Location(organization_id=organization_id, label="Austin garden", latitude=30.2672, longitude=-97.7431, privacy_precision="1km", exact_coordinates_authorized=True, timezone="America/Chicago", country_code="US", admin1="TX", admin2="Travis County", county_fips="48453"),
        "tx-houston": Location(organization_id=organization_id, label="Houston, TX", latitude=29.7604, longitude=-95.3698, privacy_precision="1km", exact_coordinates_authorized=True, timezone="America/Chicago", country_code="US", admin1="TX", admin2="Harris County", county_fips="48201"),
        "tx-hidalgo": Location(organization_id=organization_id, label="Hidalgo County, TX", latitude=26.1, longitude=-98.2, privacy_precision="1km", exact_coordinates_authorized=True, timezone="America/Chicago", country_code="US", admin1="TX", admin2="Hidalgo County", county_fips="48215"),
        "fl-orlando": Location(organization_id=organization_id, label="Orlando, FL", latitude=28.5383, longitude=-81.3792, privacy_precision="1km", exact_coordinates_authorized=True, timezone="America/New_York", country_code="US", admin1="FL", admin2="Orange County", county_fips="12095"),
        "fl-broward": Location(organization_id=organization_id, label="Broward County, FL", latitude=26.1901, longitude=-80.3659, privacy_precision="1km", exact_coordinates_authorized=True, timezone="America/New_York", country_code="US", admin1="FL", admin2="Broward County", county_fips="12011"),
        "ga-atlanta": Location(organization_id=organization_id, label="Atlanta, GA", latitude=33.7490, longitude=-84.3880, privacy_precision="1km", exact_coordinates_authorized=True, timezone="America/New_York", country_code="US", admin1="GA", admin2="Fulton County", county_fips="13121"),
        "ca-los-angeles": Location(organization_id=organization_id, label="Los Angeles, CA", latitude=34.0522, longitude=-118.2437, privacy_precision="1km", exact_coordinates_authorized=True, timezone="America/Los_Angeles", country_code="US", admin1="CA", admin2="Los Angeles County", county_fips="06037"),
    }
    aliases = {}
    for alias, location in records.items():
        existing = _location(repository.connection, organization_id, location.label)
        aliases[alias] = existing["id"] if existing else repository.create_location(location).id
    return aliases


def seed_demo(runtime: GaiaRuntime) -> dict:
    from apps.api.gaia_api.plant_api import post_observation, post_plant
    from apps.api.gaia_api.season_api import post_season_plan

    import asyncio

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
                location_id=runtime.primary_location_id,
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
                location_id=runtime.primary_location_id,
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
        "text_model": runtime.text_model if runtime.provider_modes.text_model == "local" else "fixture-guidance-local",
        "vision_model": runtime.vision_model if runtime.provider_modes.vision_model == "local" else "fixture-vision-local",
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


def doctor_report(runtime: GaiaRuntime, *, host: str = DEFAULT_ALPHA_HOST, port: int = DEFAULT_ALPHA_PORT) -> dict:
    checks = [
        _command_check("Python", ["py", "-3.13", "--version"]),
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


def build_provider_registry(modes: AlphaProviderModes) -> ProviderRegistry:
    return ProviderRegistry(
        [
            _provider("nws", "National Weather Service", ProviderType.WEATHER, "NOAA/NWS", modes.nws, FreshnessClass.SHORT, "US"),
            _provider("nasa-power", "NASA POWER", ProviderType.CLIMATE, "NASA", modes.nasa_power, FreshnessClass.MEDIUM),
            _provider("usda-nrcs-sda", "USDA NRCS Soil Data Access", ProviderType.SOIL, "USDA NRCS", "fixture", FreshnessClass.LONG, "US"),
            _provider("usgs-water", "USGS Water", ProviderType.WATER, "USGS", "fixture", FreshnessClass.REALTIME, "US"),
            _provider("gbif", "GBIF", ProviderType.TAXONOMY, "GBIF", modes.gbif, FreshnessClass.LONG),
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
            _provider("fixture-vision-local", "Fixture Vision", ProviderType.VISION, "local", "fixture", FreshnessClass.STATIC, remote=False, authentication=AuthenticationRequirement.LOCAL_ONLY),
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
        license_metadata=LicenseMetadata(),
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
    provider_id = "fixture-cli-geography"

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
                    canonical_url="fixture://cli/geography",
                    authority="GAIA CLI fixture geography",
                    geographic_scope=f"US/{state_code}/{county}",
                    license="fixture",
                    attribution="GAIA fixture",
                    content_hash=content_hash([state_code, county]),
                )
            ],
        )


class CLIRegulatoryGeometryProvider:
    provider_id = "fixture-cli-regulatory-geometry"

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
                    canonical_url="fixture://cli/zones",
                    authority="GAIA CLI fixture regulatory geometry",
                    geographic_scope="US",
                    license="fixture",
                    attribution="GAIA fixture",
                    content_hash=content_hash([latitude, longitude]),
                )
            ],
        )


def _mode(key: str, default: ProviderMode) -> ProviderMode:
    value = os.environ.get(key, default).strip().lower().replace("-", "_")
    normalized = {"local_ollama": "local", "off": "disabled", "none": "disabled"}.get(value, value)
    if normalized not in {"fixture", "live", "disabled", "local"}:
        return default
    return normalized  # type: ignore[return-value]


def _nws_provider(modes: AlphaProviderModes):
    if modes.nws == "live":
        return NWSApiAdapter(os.environ.get("NWS_USER_AGENT") or "GAIA Local Alpha/0.1")
    return FixtureNWSProvider()


def _nasa_power_provider(modes: AlphaProviderModes):
    if modes.nasa_power == "live":
        return NASAPowerApiAdapter()
    return FixtureNASAPowerProvider()


def _gbif_provider(modes: AlphaProviderModes):
    if modes.gbif == "live":
        return GBIFApiAdapter(user_agent=os.environ.get("GBIF_USER_AGENT") or "GAIA Local Alpha/0.1")
    return FixtureGBIFProvider()


def _text_model_provider(modes: AlphaProviderModes):
    if modes.text_model == "local":
        return OllamaModelProvider(model=os.environ.get("GAIA_OLLAMA_MODEL", "llama3.1:latest"), base_url=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    return FixtureGuidanceModelProvider()


def _vision_provider(modes: AlphaProviderModes):
    if modes.vision_model == "local":
        return OllamaLlavaVisionProvider(model=os.environ.get("GAIA_LLAVA_MODEL", "llava:latest"), base_url=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    return FixtureVisionProvider()


def _vision_provider_id(modes: AlphaProviderModes) -> str:
    return "ollama-llava-local" if modes.vision_model == "local" else "fixture-vision-local"


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
