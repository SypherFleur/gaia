from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from packages.audit import AuditLog, UsageLedger
from packages.botany import BotanistService, FixtureGBIFProvider, FixtureGenesysProvider, GBIFTaxonomyTool, GenesysGermplasmTool
from packages.cache import SQLiteCacheBackend
from packages.context import ContextCompiler
from packages.cost import CostFirewall, FinancialPolicy, ProviderCostPolicy
from packages.domain import Location, Membership, Organization, User, Workspace
from packages.domain.models import new_id
from packages.geospatial import AtlasService
from packages.geospatial.providers import (
    AdminResolution,
    AtlasZone,
    FixtureHardinessProvider,
    FixtureWatershedProvider,
    ProviderStatus,
    RegulatoryZoneResolution,
)
from packages.persistence import GaiaRepository, connect_in_memory, initialize_schema
from packages.policy import DataEgressPolicy
from packages.providers import (
    AuthenticationRequirement,
    BillingClass,
    CachePolicy,
    FreshnessClass,
    LicenseMetadata,
    ProviderQuotaPolicy,
    ProviderRecord,
    ProviderRegistry,
    ProviderType,
    QuotaManager,
)
from packages.provenance import ProvenanceRecord, content_hash
from packages.sentinel import (
    FixtureAPHISProvider,
    FixtureFloridaFDACSProvider,
    FixtureTexasAgricultureProvider,
    JurisdictionPack,
    JurisdictionPackMetadata,
    JurisdictionPackRegistry,
    RegulationMovementRulesTool,
    SentinelService,
    USStateJurisdictionPack,
)
from packages.status import CostStatusService
from packages.tools import ToolExecutionContext, ToolGateway


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SQLITE_URL = "sqlite:///./local_data/gaia.sqlite3"


@dataclass(slots=True)
class GaiaRuntime:
    connection: sqlite3.Connection
    repository: GaiaRepository
    registry: ProviderRegistry
    usage_ledger: UsageLedger
    audit_log: AuditLog
    tool_gateway: ToolGateway
    context_compiler: ContextCompiler
    botanist: BotanistService
    sentinel: SentinelService
    organization_id: str
    user_id: str
    workspace_id: str
    location_aliases: dict[str, str]
    sovereign: bool = False

    def context(self, *, request_id: str = "cli") -> ToolExecutionContext:
        return ToolExecutionContext(
            request_id=request_id,
            organization_id=self.organization_id,
            user_id=self.user_id,
            workspace_id=self.workspace_id,
            permissions=frozenset({"tool.read", "regulation.read", "vision.analyze", "model.chat"}),
            data_egress_policy=DataEgressPolicy.sovereign_default() if self.sovereign else DataEgressPolicy(),
        )

    def close(self) -> None:
        self.connection.close()


def create_runtime(database_url: str | None = None, *, sovereign: bool = False) -> GaiaRuntime:
    connection = connect_sqlite_url(database_url or DEFAULT_SQLITE_URL)
    initialize_schema_if_empty(connection)
    repository = GaiaRepository(connection)
    suffix = new_id()[:8]
    organization = repository.create_organization(Organization(name="GAIA CLI", slug=f"gaia-cli-{suffix}", deployment_mode="sovereign" if sovereign else "local"))
    user = repository.create_user(User(external_auth_id=f"cli:{suffix}", display_name="GAIA CLI User"))
    repository.create_membership(
        Membership(
            organization_id=organization.id,
            user_id=user.id,
            role="owner",
            permissions=["tool.read", "regulation.read", "vision.analyze", "model.chat"],
        )
    )
    workspace = repository.create_workspace(Workspace(organization_id=organization.id, name="CLI Workspace", purpose="local fixture"))
    aliases = seed_cli_locations(repository, organization.id)
    registry = ProviderRegistry(
        [
            enabled_provider("aphis", ProviderType.REGULATION),
            enabled_provider("texas-agriculture", ProviderType.REGULATION),
            enabled_provider("florida-fdacs", ProviderType.REGULATION),
            enabled_provider("gbif", ProviderType.TAXONOMY),
            enabled_provider("genesys-pgr", ProviderType.GERMPLASM),
            enabled_provider("ollama-local", ProviderType.MODEL, remote=False),
        ]
    )
    usage_ledger = UsageLedger(connection)
    audit_log = AuditLog(connection)
    tool_gateway = ToolGateway(
        connection=connection,
        registry=registry,
        cost_firewall=CostFirewall(FinancialPolicy()),
        quota_manager=QuotaManager(connection),
        cache_backend=SQLiteCacheBackend(connection),
        usage_ledger=usage_ledger,
        audit_log=audit_log,
    )
    aphis = FixtureAPHISProvider()
    texas = FixtureTexasAgricultureProvider()
    florida = FixtureFloridaFDACSProvider()
    pack_registry = JurisdictionPackRegistry(
        [
            JurisdictionPack(
                JurisdictionPackMetadata("us_federal", "0.1.0", "U.S. federal", "US", ["usda_aphis"], enabled=True),
                aphis,
            ),
            USStateJurisdictionPack(
                JurisdictionPackMetadata("us_tx", "0.1.0", "Texas", "US", ["tx_agriculture"], enabled=True),
                texas,
                state_code="TX",
            ),
            USStateJurisdictionPack(
                JurisdictionPackMetadata("us_fl", "0.1.0", "Florida", "US", ["fl_fdacs_dpi"], enabled=True),
                florida,
                state_code="FL",
            ),
        ]
    )
    atlas = AtlasService(repository, CLIGeographyProvider(), FixtureWatershedProvider(), FixtureHardinessProvider(), CLIRegulatoryGeometryProvider())
    context_compiler = ContextCompiler(repository, atlas, None)
    botanist = BotanistService(repository, tool_gateway, GBIFTaxonomyTool(FixtureGBIFProvider()), GenesysGermplasmTool(FixtureGenesysProvider()))
    sentinel = SentinelService(
        repository=repository,
        tool_gateway=tool_gateway,
        context_compiler=context_compiler,
        federal_tool=RegulationMovementRulesTool(aphis, "aphis"),
        texas_tool=RegulationMovementRulesTool(texas, "texas-agriculture"),
        jurisdiction_registry=pack_registry,
    )
    return GaiaRuntime(
        connection=connection,
        repository=repository,
        registry=registry,
        usage_ledger=usage_ledger,
        audit_log=audit_log,
        tool_gateway=tool_gateway,
        context_compiler=context_compiler,
        botanist=botanist,
        sentinel=sentinel,
        organization_id=organization.id,
        user_id=user.id,
        workspace_id=workspace.id,
        location_aliases=aliases,
        sovereign=sovereign,
    )


def connect_sqlite_url(database_url: str) -> sqlite3.Connection:
    if database_url in {":memory:", "sqlite:///:memory:"}:
        return connect_in_memory()
    if not database_url.startswith("sqlite:///"):
        raise ValueError("Only sqlite:/// database URLs are supported by the local CLI runtime.")
    raw_path = database_url.removeprefix("sqlite:///")
    path = Path(raw_path)
    if not path.is_absolute():
        path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
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


def seed_cli_locations(repository: GaiaRepository, organization_id: str) -> dict[str, str]:
    records = {
        "tx-austin": Location(organization_id=organization_id, label="Austin, TX", latitude=30.2672, longitude=-97.7431, privacy_precision="1km", exact_coordinates_authorized=True, country_code="US"),
        "tx-houston": Location(organization_id=organization_id, label="Houston, TX", latitude=29.7604, longitude=-95.3698, privacy_precision="1km", exact_coordinates_authorized=True, country_code="US"),
        "tx-hidalgo": Location(organization_id=organization_id, label="Hidalgo County, TX", latitude=26.1, longitude=-98.2, privacy_precision="1km", exact_coordinates_authorized=True, country_code="US"),
        "fl-orlando": Location(organization_id=organization_id, label="Orlando, FL", latitude=28.5383, longitude=-81.3792, privacy_precision="1km", exact_coordinates_authorized=True, country_code="US"),
        "fl-broward": Location(organization_id=organization_id, label="Broward County, FL", latitude=26.1901, longitude=-80.3659, privacy_precision="1km", exact_coordinates_authorized=True, country_code="US"),
        "ga-atlanta": Location(organization_id=organization_id, label="Atlanta, GA", latitude=33.7490, longitude=-84.3880, privacy_precision="1km", exact_coordinates_authorized=True, country_code="US"),
        "ca-los-angeles": Location(organization_id=organization_id, label="Los Angeles, CA", latitude=34.0522, longitude=-118.2437, privacy_precision="1km", exact_coordinates_authorized=True, country_code="US"),
    }
    aliases = {}
    for alias, location in records.items():
        aliases[alias] = repository.create_location(location).id
    return aliases


def enabled_provider(provider_id: str, provider_type: ProviderType, *, remote: bool = True) -> ProviderRecord:
    billing = BillingClass.LOCAL if not remote else BillingClass.FREE
    return ProviderRecord(
        provider_id=provider_id,
        display_name=provider_id,
        provider_type=provider_type,
        authority=provider_id,
        enabled=True,
        billing_class=billing,
        cost_policy=ProviderCostPolicy(provider_id=provider_id, billing_class=billing.value, hard_monthly_usd=0.0, allow_overage=False),
        quota_policy=ProviderQuotaPolicy(daily_requests=100),
        authentication_requirement=AuthenticationRequirement.LOCAL_ONLY if not remote else AuthenticationRequirement.NONE,
        geographic_scope="fixture",
        cache_policy=CachePolicy(FreshnessClass.REGULATORY_CURRENT, ttl_seconds=3600, stale_if_error_seconds=86400),
        license_metadata=LicenseMetadata(),
        attribution=provider_id,
        remote=remote,
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


def cost_status(runtime: GaiaRuntime) -> dict:
    return CostStatusService(runtime.registry, runtime.usage_ledger, FinancialPolicy()).status()
