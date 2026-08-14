from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from packages.provenance import ProvenanceRecord


JsonDict = dict[str, Any]


@dataclass(frozen=True, slots=True)
class EconomicRequest:
    commodity: str
    geography: JsonDict
    crop_or_taxon: JsonDict = field(default_factory=dict)
    periods: list[str] = field(default_factory=list)
    market_region: str | None = None
    retrieved_at: str | None = None


@dataclass(frozen=True, slots=True)
class EconomicProviderResult:
    status: str
    data: JsonDict = field(default_factory=dict)
    provenance: list[ProvenanceRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    freshness: str = "unknown"


class EconomicDataProvider(Protocol):
    provider_id: str

    async def production(self, request: EconomicRequest) -> EconomicProviderResult: ...

    async def market_reports(self, request: EconomicRequest) -> EconomicProviderResult: ...

    async def prices(self, request: EconomicRequest) -> EconomicProviderResult: ...

    async def regional_context(self, request: EconomicRequest) -> EconomicProviderResult: ...

    async def supply_chain(self, request: EconomicRequest) -> EconomicProviderResult: ...


class DisabledEconomicProvider:
    provider_id = "economic-disabled"

    async def production(self, request: EconomicRequest) -> EconomicProviderResult:
        return EconomicProviderResult(status="UNAVAILABLE", warnings=["economic_provider_disabled"])

    async def market_reports(self, request: EconomicRequest) -> EconomicProviderResult:
        return EconomicProviderResult(status="UNAVAILABLE", warnings=["economic_provider_disabled"])

    async def prices(self, request: EconomicRequest) -> EconomicProviderResult:
        return EconomicProviderResult(status="UNAVAILABLE", warnings=["economic_provider_disabled"])

    async def regional_context(self, request: EconomicRequest) -> EconomicProviderResult:
        return EconomicProviderResult(status="UNAVAILABLE", warnings=["economic_provider_disabled"])

    async def supply_chain(self, request: EconomicRequest) -> EconomicProviderResult:
        return EconomicProviderResult(status="UNAVAILABLE", warnings=["economic_provider_disabled"])
