from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from packages.sentinel.providers import RegulationProvider
from packages.sentinel.tools import RegulationMovementRulesTool, RegulationPestAlertsTool


JsonDict = dict[str, Any]


@dataclass(frozen=True, slots=True)
class JurisdictionPackMetadata:
    pack_id: str
    version: str
    display_name: str
    country_code: str
    authority_ids: list[str] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)
    enabled: bool = True
    legal_scope: str = "movement, quarantine, pest alert, and reporting guidance"
    freshness_required: str = "REGULATORY_CURRENT"


@dataclass(frozen=True, slots=True)
class JurisdictionPack:
    metadata: JurisdictionPackMetadata
    provider: RegulationProvider

    @property
    def pack_id(self) -> str:
        return self.metadata.pack_id

    @property
    def provider_id(self) -> str:
        return self.provider.provider_id

    @property
    def movement_tool(self) -> RegulationMovementRulesTool:
        return RegulationMovementRulesTool(self.provider, self.provider_id)

    @property
    def pest_alert_tool(self) -> RegulationPestAlertsTool:
        return RegulationPestAlertsTool(self.provider, self.provider_id)

    def applies_to(self, origin_geo: JsonDict, destination_geo: JsonDict, request: JsonDict) -> bool:
        return self.metadata.country_code in {
            origin_geo.get("country_code") or request.get("source_country"),
            destination_geo.get("country_code") or request.get("destination_country"),
        }


@dataclass(frozen=True, slots=True)
class USStateJurisdictionPack(JurisdictionPack):
    state_code: str = ""

    def applies_to(self, origin_geo: JsonDict, destination_geo: JsonDict, request: JsonDict) -> bool:
        if not self.metadata.enabled:
            return False
        return self.state_code in {origin_geo.get("state_code"), destination_geo.get("state_code")}


class JurisdictionPackRegistry:
    def __init__(self, packs: list[JurisdictionPack]) -> None:
        self._packs = {pack.pack_id: pack for pack in packs}

    def all(self) -> list[JurisdictionPack]:
        return list(self._packs.values())

    def enabled(self) -> list[JurisdictionPack]:
        return [pack for pack in self._packs.values() if pack.metadata.enabled]

    def get(self, pack_id: str) -> JurisdictionPack:
        try:
            return self._packs[pack_id]
        except KeyError as exc:
            raise KeyError(f"Unknown jurisdiction pack: {pack_id}") from exc

    def movement_tools_for(self, origin_geo: JsonDict, destination_geo: JsonDict, request: JsonDict) -> list[RegulationMovementRulesTool]:
        tools: list[RegulationMovementRulesTool] = []
        for pack in self.enabled():
            if pack.applies_to(origin_geo, destination_geo, request):
                tools.append(pack.movement_tool)
        return tools

    def pest_alert_tools_for(self, country_code: str | None, state_code: str | None = None) -> list[RegulationPestAlertsTool]:
        tools: list[RegulationPestAlertsTool] = []
        for pack in self.enabled():
            if pack.metadata.country_code != country_code:
                continue
            if isinstance(pack, USStateJurisdictionPack) and state_code not in {None, pack.state_code}:
                continue
            tools.append(pack.pest_alert_tool)
        return tools


def legacy_registry(
    federal_tool: RegulationMovementRulesTool,
    texas_tool: RegulationMovementRulesTool | None = None,
) -> JurisdictionPackRegistry:
    packs: list[JurisdictionPack] = [
        JurisdictionPack(
            JurisdictionPackMetadata(
                pack_id="us_federal",
                version="0.1.0",
                display_name="United States federal plant-health jurisdiction",
                country_code="US",
                authority_ids=["usda_aphis"],
            ),
            federal_tool.provider,
        )
    ]
    if texas_tool is not None:
        packs.append(
            USStateJurisdictionPack(
                JurisdictionPackMetadata(
                    pack_id="us_tx",
                    version="0.1.0",
                    display_name="Texas plant-health jurisdiction",
                    country_code="US",
                    authority_ids=["tx_agriculture"],
                ),
                texas_tool.provider,
                state_code="TX",
            )
        )
    return JurisdictionPackRegistry(packs)
