from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


JsonDict = dict[str, Any]


@dataclass(frozen=True, slots=True)
class Authority:
    id: str
    name: str
    jurisdiction: str
    authority_level: str
    domain: str
    canonical_url: str
    source_type: str = "official_public"
    contact_reference: str | None = None

    def to_dict(self) -> JsonDict:
        return asdict(self)


class AuthorityRegistry:
    def __init__(self, authorities: list[Authority]) -> None:
        self._authorities = {authority.id: authority for authority in authorities}

    def get(self, authority_id: str) -> Authority:
        try:
            return self._authorities[authority_id]
        except KeyError as exc:
            raise KeyError(f"Unknown authority: {authority_id}") from exc

    def all(self) -> list[Authority]:
        return list(self._authorities.values())

    def as_metadata(self, authority_id: str, **extra: Any) -> JsonDict:
        metadata = self.get(authority_id).to_dict()
        metadata.update(extra)
        return metadata


def default_authority_registry() -> AuthorityRegistry:
    return AuthorityRegistry(
        [
            Authority(
                id="usda_aphis",
                name="USDA Animal and Plant Health Inspection Service",
                jurisdiction="United States",
                authority_level="federal",
                domain="plant health, quarantine, and interstate/import movement",
                canonical_url="https://www.aphis.usda.gov/",
            ),
            Authority(
                id="tx_agriculture",
                name="Texas Department of Agriculture",
                jurisdiction="US/TX",
                authority_level="state",
                domain="Texas plant quality, quarantine, and nursery regulation",
                canonical_url="https://texasagriculture.gov/",
            ),
            Authority(
                id="fl_fdacs_dpi",
                name="Florida Department of Agriculture and Consumer Services Division of Plant Industry",
                jurisdiction="US/FL",
                authority_level="state",
                domain="Florida plant inspection, quarantine, nursery, and citrus health regulation",
                canonical_url="https://www.fdacs.gov/Agriculture-Industry/Plants-and-Nurseries/Plant-Inspection",
                contact_reference="FDACS Division of Plant Industry helpline",
            ),
            Authority(
                id="fl_dep_invasive_plants",
                name="Florida Department of Environmental Protection Invasive Plant Management",
                jurisdiction="US/FL",
                authority_level="state",
                domain="Florida aquatic and invasive plant management permits",
                canonical_url="https://floridadep.gov/",
            ),
        ]
    )
