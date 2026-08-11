from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from packages.cost.policy import ProviderCostPolicy


class BillingClass(str, Enum):
    LOCAL = "LOCAL"
    FREE = "FREE"
    MANUAL_PAID = "MANUAL_PAID"


class ProviderType(str, Enum):
    WEATHER = "WEATHER"
    CLIMATE = "CLIMATE"
    SOIL = "SOIL"
    WATER = "WATER"
    MARKET = "MARKET"
    RESEARCH = "RESEARCH"
    TAXONOMY = "TAXONOMY"
    GERMPLASM = "GERMPLASM"
    REGULATION = "REGULATION"
    VISION = "VISION"
    CALENDAR = "CALENDAR"
    MODEL = "MODEL"
    MOCK = "MOCK"


class AuthenticationRequirement(str, Enum):
    NONE = "NONE"
    OPTIONAL_API_KEY = "OPTIONAL_API_KEY"
    REQUIRED_API_KEY = "REQUIRED_API_KEY"
    OAUTH = "OAUTH"
    LOCAL_ONLY = "LOCAL_ONLY"


class HealthStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
    DISABLED = "DISABLED"


class FreshnessClass(str, Enum):
    STATIC = "STATIC"
    LONG = "LONG"
    MEDIUM = "MEDIUM"
    SHORT = "SHORT"
    REALTIME = "REALTIME"
    REGULATORY_CURRENT = "REGULATORY_CURRENT"


@dataclass(frozen=True, slots=True)
class ProviderQuotaPolicy:
    daily_requests: int | None = None
    per_minute_requests: int | None = None
    daily_compute_units: int | None = None
    reset_strategy: str = "UTC_DAY"
    fail_closed: bool = True


@dataclass(frozen=True, slots=True)
class CachePolicy:
    freshness_class: FreshnessClass
    ttl_seconds: int | None = None
    stale_if_error_seconds: int | None = None
    allow_stale_for_regulatory_current: bool = False


@dataclass(frozen=True, slots=True)
class LicenseMetadata:
    terms_url: str | None = None
    license: str = "unknown"
    commercial_use: str = "unknown"
    redistribution: str = "unknown"
    caching: str = "unknown"
    derivative_use: str = "unknown"
    model_training: str = "unknown"
    attribution_required: bool = False
    last_reviewed_at: str | None = None
    review_notes: str | None = None


@dataclass(slots=True)
class ProviderRecord:
    provider_id: str
    display_name: str
    provider_type: ProviderType
    authority: str
    enabled: bool
    billing_class: BillingClass
    cost_policy: ProviderCostPolicy
    quota_policy: ProviderQuotaPolicy
    authentication_requirement: AuthenticationRequirement
    geographic_scope: str
    cache_policy: CachePolicy
    license_metadata: LicenseMetadata
    attribution: str | None = None
    health_status: HealthStatus = HealthStatus.UNKNOWN
    last_health_check: str | None = None
    remote: bool = False


class ProviderRegistry:
    def __init__(self, providers: list[ProviderRecord] | None = None) -> None:
        self._providers: dict[str, ProviderRecord] = {}
        for provider in providers or []:
            self.register(provider)

    def register(self, provider: ProviderRecord) -> None:
        if provider.billing_class == BillingClass.MANUAL_PAID and provider.enabled:
            raise ValueError("MANUAL_PAID providers may not be enabled by default")
        self._providers[provider.provider_id] = provider

    def get(self, provider_id: str) -> ProviderRecord:
        try:
            return self._providers[provider_id]
        except KeyError as exc:
            raise KeyError(f"Unknown provider: {provider_id}") from exc

    def all(self) -> list[ProviderRecord]:
        return list(self._providers.values())

    def enabled(self) -> list[ProviderRecord]:
        return [provider for provider in self._providers.values() if provider.enabled]

    def disabled(self) -> list[ProviderRecord]:
        return [provider for provider in self._providers.values() if not provider.enabled]


def _policy(provider_id: str, billing_class: BillingClass) -> ProviderCostPolicy:
    return ProviderCostPolicy(
        provider_id=provider_id,
        billing_class=billing_class.value,
        hard_monthly_usd=0.0,
        allow_overage=False,
    )


def _provider(
    provider_id: str,
    display_name: str,
    provider_type: ProviderType,
    authority: str,
    billing_class: BillingClass,
    authentication_requirement: AuthenticationRequirement,
    freshness_class: FreshnessClass,
    geographic_scope: str = "global",
    enabled: bool = False,
    remote: bool = True,
    quota_policy: ProviderQuotaPolicy | None = None,
    license_metadata: LicenseMetadata | None = None,
) -> ProviderRecord:
    return ProviderRecord(
        provider_id=provider_id,
        display_name=display_name,
        provider_type=provider_type,
        authority=authority,
        enabled=enabled,
        billing_class=billing_class,
        cost_policy=_policy(provider_id, billing_class),
        quota_policy=quota_policy or ProviderQuotaPolicy(),
        authentication_requirement=authentication_requirement,
        geographic_scope=geographic_scope,
        cache_policy=CachePolicy(freshness_class=freshness_class),
        license_metadata=license_metadata or LicenseMetadata(),
        attribution=authority,
        health_status=HealthStatus.UNKNOWN if enabled else HealthStatus.DISABLED,
        remote=remote,
    )


def default_protocol_two_registry() -> ProviderRegistry:
    providers = [
        _provider("nws", "National Weather Service", ProviderType.WEATHER, "NOAA/NWS", BillingClass.FREE, AuthenticationRequirement.NONE, FreshnessClass.SHORT, "US"),
        _provider("nasa-power", "NASA POWER", ProviderType.CLIMATE, "NASA", BillingClass.FREE, AuthenticationRequirement.NONE, FreshnessClass.MEDIUM),
        _provider("usda-nrcs-sda", "USDA NRCS Soil Data Access", ProviderType.SOIL, "USDA NRCS", BillingClass.FREE, AuthenticationRequirement.NONE, FreshnessClass.LONG, "US"),
        _provider("usgs-water", "USGS Water", ProviderType.WATER, "USGS", BillingClass.FREE, AuthenticationRequirement.NONE, FreshnessClass.REALTIME, "US"),
        _provider("usda-nass", "USDA NASS Quick Stats", ProviderType.MARKET, "USDA NASS", BillingClass.FREE, AuthenticationRequirement.OPTIONAL_API_KEY, FreshnessClass.MEDIUM, "US"),
        _provider("usda-ams", "USDA AMS MyMarketNews", ProviderType.MARKET, "USDA AMS", BillingClass.FREE, AuthenticationRequirement.OPTIONAL_API_KEY, FreshnessClass.SHORT, "US"),
        _provider("gbif", "GBIF", ProviderType.TAXONOMY, "GBIF", BillingClass.FREE, AuthenticationRequirement.NONE, FreshnessClass.LONG),
        _provider("genesys-pgr", "Genesys PGR", ProviderType.GERMPLASM, "Genesys PGR", BillingClass.FREE, AuthenticationRequirement.OAUTH, FreshnessClass.LONG),
        _provider("europe-pmc", "Europe PMC", ProviderType.RESEARCH, "Europe PMC", BillingClass.FREE, AuthenticationRequirement.NONE, FreshnessClass.MEDIUM),
        _provider("ollama-llava-local", "Local Ollama LLaVA", ProviderType.VISION, "local", BillingClass.LOCAL, AuthenticationRequirement.LOCAL_ONLY, FreshnessClass.STATIC, enabled=True, remote=False),
        _provider("plantnet", "Pl@ntNet", ProviderType.VISION, "Pl@ntNet", BillingClass.FREE, AuthenticationRequirement.REQUIRED_API_KEY, FreshnessClass.SHORT, quota_policy=ProviderQuotaPolicy(daily_requests=500)),
        _provider("aphis", "APHIS", ProviderType.REGULATION, "USDA APHIS", BillingClass.FREE, AuthenticationRequirement.NONE, FreshnessClass.REGULATORY_CURRENT, "US"),
        _provider("texas-agriculture", "Texas Department of Agriculture", ProviderType.REGULATION, "Texas Department of Agriculture", BillingClass.FREE, AuthenticationRequirement.NONE, FreshnessClass.REGULATORY_CURRENT, "US/TX"),
        _provider("google-calendar", "Google Calendar", ProviderType.CALENDAR, "Google", BillingClass.FREE, AuthenticationRequirement.OAUTH, FreshnessClass.SHORT),
        _provider("ollama-local", "Local Ollama", ProviderType.MODEL, "local", BillingClass.LOCAL, AuthenticationRequirement.LOCAL_ONLY, FreshnessClass.STATIC, enabled=True, remote=False),
        _provider("llama-cpp-local", "Local llama.cpp", ProviderType.MODEL, "local", BillingClass.LOCAL, AuthenticationRequirement.LOCAL_ONLY, FreshnessClass.STATIC, enabled=True, remote=False),
        _provider("nvidia-runtime-future", "Future NVIDIA Runtime", ProviderType.MODEL, "NVIDIA/local or customer runtime", BillingClass.LOCAL, AuthenticationRequirement.LOCAL_ONLY, FreshnessClass.STATIC, remote=False),
        _provider("cloudflare-workers-ai-future", "Future Cloudflare Workers AI", ProviderType.MODEL, "Cloudflare", BillingClass.FREE, AuthenticationRequirement.REQUIRED_API_KEY, FreshnessClass.SHORT),
        _provider("future-paid-provider", "Future Paid Provider", ProviderType.MODEL, "manual future provider", BillingClass.MANUAL_PAID, AuthenticationRequirement.REQUIRED_API_KEY, FreshnessClass.SHORT),
    ]
    return ProviderRegistry(providers)
