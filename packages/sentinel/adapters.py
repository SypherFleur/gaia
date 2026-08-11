from __future__ import annotations

import asyncio
from dataclasses import dataclass
from urllib import request as urlrequest

from packages.provenance import ProvenanceRecord, content_hash
from packages.sentinel.providers import RegulationRequest, RegulationResponse, RegulatoryRule, RegulatoryZone


APHIS_CITRUS_URL = "https://www.aphis.usda.gov/plant-pests-diseases/citrus-diseases/federal-citrus-pest-disease-written-quarantine-descriptions"
APHIS_IMPORT_URL = "https://www.aphis.usda.gov/plant-imports/how-to-import"
TEXAS_CITRUS_URL = "https://texasagriculture.gov/Regulatory-Programs/Plant-Quality/Citrus-Information"
TEXAS_GREENING_URL = "https://texasagriculture.gov/Regulatory-Programs/Plant-Quality/Pest-and-Disease-Alerts/Citrus-Greening"


class FixtureAPHISProvider:
    provider_id = "aphis"

    def __init__(self, *, unavailable: bool = False, stale: bool = False, conflict: bool = False) -> None:
        self.unavailable = unavailable
        self.stale = stale
        self.conflict = conflict
        self.calls = 0
        self.last_request = None

    async def resolve_zones(self, request: RegulationRequest) -> RegulationResponse:
        return await self.movement_rules(request)

    async def movement_rules(self, request: RegulationRequest) -> RegulationResponse:
        self.calls += 1
        self.last_request = request
        if self.unavailable:
            return RegulationResponse(provider_id=self.provider_id, status="PROVIDER_ERROR", freshness="UNAVAILABLE", warnings=["aphis_unavailable"])
        freshness = "STALE" if self.stale else "CURRENT"
        rules = [
            RegulatoryRule(
                rule_id="aphis-citrus-interstate-certificate",
                jurisdiction_pack="us_federal",
                authority="USDA APHIS",
                authority_level="federal",
                jurisdiction="United States",
                regulated_taxa=[{"rank": "genus", "name": "Citrus"}],
                regulated_articles=["nursery stock", "live plant", "cutting", "scion", "growing medium"],
                plant_parts=["live plant", "cutting", "scion", "growing medium"],
                pest_or_disease="citrus greening / Asian citrus psyllid",
                origin_scope={"country_code": "US", "quarantine_zone": "citrus"},
                destination_scope={"country_code": "US"},
                status_effect="CONDITIONAL",
                permits=[{"requirement": "APHIS certificate or compliance agreement", "authority": "USDA APHIS"}],
                inspection=[{"requirement": "Inspection may be required before interstate movement.", "authority": "USDA APHIS"}],
                exceptions=[{"plant_part": "seed", "condition": "Seed not matched by live nursery-stock rule in fixture."}],
                last_verified_at="2026-08-11T00:00:00+00:00",
                freshness=freshness,
                authority_metadata={"binding_authority": True, "source_class": "binding_authority"},
                source_reference=APHIS_CITRUS_URL,
            ),
            RegulatoryRule(
                rule_id="aphis-import-plants-for-planting-permit",
                jurisdiction_pack="us_federal",
                authority="USDA APHIS",
                authority_level="federal",
                jurisdiction="United States import",
                regulated_taxa=[{"rank": "host_class", "name": "plants for planting"}],
                regulated_articles=["plants for planting", "seeds", "cuttings"],
                plant_parts=["live plant", "seed", "cutting", "scion", "root"],
                origin_scope={"country_code": "ANY_NON_US"},
                destination_scope={"country_code": "US"},
                status_effect="CONDITIONAL",
                permits=[{"requirement": "APHIS import permit or plant inspection station process may be required.", "authority": "USDA APHIS"}],
                inspection=[{"requirement": "Plant inspection station review for imported plant material.", "authority": "USDA APHIS"}],
                last_verified_at="2026-08-11T00:00:00+00:00",
                freshness=freshness,
                authority_metadata={"binding_authority": True, "source_class": "binding_authority"},
                source_reference=APHIS_IMPORT_URL,
            ),
        ]
        if self.conflict:
            rules.append(
                RegulatoryRule(
                    rule_id="aphis-conflict-fixture",
                    jurisdiction_pack="us_federal",
                    authority="USDA APHIS conflicting fixture",
                    authority_level="federal",
                    jurisdiction="United States",
                    regulated_taxa=[{"rank": "genus", "name": "Citrus"}],
                    regulated_articles=["live plant"],
                    plant_parts=["live plant"],
                    status_effect="ALLOWED",
                    last_verified_at="2026-08-11T00:00:00+00:00",
                    freshness=freshness,
                    authority_metadata={"binding_authority": True, "source_class": "binding_authority", "conflict_fixture": True},
                    source_reference="fixture://aphis/conflict",
                )
            )
        return RegulationResponse(
            provider_id=self.provider_id,
            status="AVAILABLE",
            rules=rules,
            freshness=freshness,
            provenance=[_prov(self.provider_id, "fixture-aphis-citrus", APHIS_CITRUS_URL, "USDA APHIS", {"rules": [rule.rule_id for rule in rules]})],
        )

    async def pest_alerts(self, request: RegulationRequest) -> RegulationResponse:
        return RegulationResponse(
            provider_id=self.provider_id,
            status="AVAILABLE",
            alerts=[{"pest_or_disease": "citrus greening", "regulated": True, "authority": "USDA APHIS"}],
            reporting_requirements=[{"authority": "USDA APHIS", "instruction": "Preserve photos/location and contact plant health authorities for suspected regulated citrus disease."}],
            freshness="CURRENT",
            provenance=[_prov(self.provider_id, "fixture-aphis-alert", APHIS_CITRUS_URL, "USDA APHIS", {"alert": "citrus greening"})],
        )

    async def reporting_requirements(self, request: RegulationRequest) -> RegulationResponse:
        return await self.pest_alerts(request)


class FixtureTexasAgricultureProvider:
    provider_id = "texas-agriculture"

    def __init__(self, *, unavailable: bool = False, stale: bool = False) -> None:
        self.unavailable = unavailable
        self.stale = stale
        self.calls = 0

    async def resolve_zones(self, request: RegulationRequest) -> RegulationResponse:
        self.calls += 1
        if self.unavailable:
            return RegulationResponse(provider_id=self.provider_id, status="PROVIDER_ERROR", freshness="UNAVAILABLE", warnings=["texas_agriculture_unavailable"])
        freshness = "STALE" if self.stale else "CURRENT"
        zones = [
            RegulatoryZone(
                zone_id="tx-citrus-zone",
                jurisdiction_pack="us_tx",
                authority="Texas Department of Agriculture",
                zone_type="citrus_zone",
                name="Texas Citrus Zone",
                area_scope={"state_code": "TX", "counties": ["Cameron", "Hidalgo", "Nueces", "Aransas"]},
                geometry_reference="fixture://tx/citrus-zone",
                freshness=freshness,
            ),
            RegulatoryZone(
                zone_id="tx-hlb-gulf-coast",
                jurisdiction_pack="us_tx",
                authority="Texas Department of Agriculture",
                zone_type="quarantine",
                name="Texas Citrus Greening Gulf Coast Quarantined Area",
                area_scope={"state_code": "TX", "counties": ["Brazoria", "Fort Bend", "Galveston", "Harris", "Montgomery"]},
                geometry_reference="fixture://tx/hlb/gulf-coast",
                freshness=freshness,
            ),
        ]
        return RegulationResponse(
            provider_id=self.provider_id,
            status="AVAILABLE",
            zones=zones,
            freshness=freshness,
            provenance=[_prov(self.provider_id, "fixture-tda-citrus-zones", TEXAS_CITRUS_URL, "Texas Department of Agriculture", {"zones": [zone.zone_id for zone in zones]})],
        )

    async def movement_rules(self, request: RegulationRequest) -> RegulationResponse:
        zone_response = await self.resolve_zones(request)
        if zone_response.status != "AVAILABLE":
            return zone_response
        freshness = zone_response.freshness
        rules = [
            RegulatoryRule(
                rule_id="tda-citrus-import-prohibited-without-compliance",
                jurisdiction_pack="us_tx",
                authority="Texas Department of Agriculture",
                authority_level="state",
                jurisdiction="Texas",
                regulated_taxa=[{"rank": "genus", "name": "Citrus"}, {"rank": "species", "name": "Murraya paniculata"}],
                regulated_articles=["citrus", "related plants", "quarantined articles", "nursery stock"],
                plant_parts=["live plant", "cutting", "scion", "root", "growing medium"],
                pest_or_disease="citrus quarantined pests and diseases",
                origin_scope={"state_code": "ANY"},
                destination_scope={"state_code": "TX"},
                status_effect="CONDITIONAL",
                conditions=[{"requirement": "Unauthorized movement of citrus, related plants, or quarantined articles into Texas is prohibited.", "authority": "Texas Department of Agriculture"}],
                permits=[{"requirement": "Compliance agreement or special permit may be required.", "authority": "Texas Department of Agriculture"}],
                treatments=[{"requirement": "Treatment may be required by destination or quarantine status.", "authority": "Texas Department of Agriculture"}],
                exceptions=[{"plant_part": "fruit", "condition": "Fixture rule focuses on live/nursery plants and propagative material; fruit requires separate commodity rule."}],
                last_verified_at="2026-08-11T00:00:00+00:00",
                freshness=freshness,
                authority_metadata={"binding_authority": True, "source_class": "binding_authority"},
                source_reference=TEXAS_CITRUS_URL,
            ),
            RegulatoryRule(
                rule_id="tda-citrus-greening-quarantine-live-tree",
                jurisdiction_pack="us_tx",
                authority="Texas Department of Agriculture",
                authority_level="state",
                jurisdiction="Texas citrus greening quarantined area",
                regulated_taxa=[{"rank": "genus", "name": "Citrus"}],
                regulated_articles=["citrus nursery trees", "citrus trees"],
                plant_parts=["live plant"],
                pest_or_disease="citrus greening",
                origin_scope={"quarantine_zone": "tx-hlb"},
                destination_scope={"state_code": "TX"},
                status_effect="RESTRICTED",
                conditions=[{"requirement": "No citrus nursery trees inside the quarantined area may be moved except under compliance agreement or special permit.", "authority": "Texas Department of Agriculture"}],
                permits=[{"requirement": "Compliance agreement or special permit issued by TDA.", "authority": "Texas Department of Agriculture"}],
                reporting=[{"requirement": "Suspected citrus greening should be reported to Texas plant health authorities.", "authority": "Texas Department of Agriculture"}],
                exceptions=[{"plant_part": "seed", "condition": "Seed is outside this live-tree quarantine fixture."}],
                last_verified_at="2026-08-11T00:00:00+00:00",
                freshness=freshness,
                authority_metadata={"binding_authority": True, "source_class": "binding_authority"},
                source_reference=TEXAS_GREENING_URL,
            ),
        ]
        return RegulationResponse(
            provider_id=self.provider_id,
            status="AVAILABLE",
            rules=rules,
            zones=zone_response.zones,
            freshness=freshness,
            provenance=[*zone_response.provenance, _prov(self.provider_id, "fixture-tda-citrus-rules", TEXAS_CITRUS_URL, "Texas Department of Agriculture", {"rules": [rule.rule_id for rule in rules]})],
        )

    async def pest_alerts(self, request: RegulationRequest) -> RegulationResponse:
        return RegulationResponse(
            provider_id=self.provider_id,
            status="AVAILABLE",
            alerts=[{"pest_or_disease": "citrus greening", "regulated": True, "authority": "Texas Department of Agriculture"}],
            reporting_requirements=[{"authority": "Texas Department of Agriculture", "instruction": "Preserve photos and plant location; contact TDA for suspected regulated citrus disease."}],
            freshness="CURRENT",
            provenance=[_prov(self.provider_id, "fixture-tda-alert", TEXAS_GREENING_URL, "Texas Department of Agriculture", {"alert": "citrus greening"})],
        )

    async def reporting_requirements(self, request: RegulationRequest) -> RegulationResponse:
        return await self.pest_alerts(request)


@dataclass(slots=True)
class ReadOnlyRegulatoryPageAdapter:
    provider_id: str
    authority: str
    urls: tuple[str, ...]
    timeout_seconds: float = 15.0

    async def resolve_zones(self, request: RegulationRequest) -> RegulationResponse:
        return await self.movement_rules(request)

    async def movement_rules(self, request: RegulationRequest) -> RegulationResponse:
        try:
            pages = await asyncio.gather(*(asyncio.to_thread(self._fetch, url) for url in self.urls))
        except Exception as exc:
            return RegulationResponse(provider_id=self.provider_id, status="PROVIDER_ERROR", freshness="UNAVAILABLE", warnings=[f"regulatory_page_error:{exc.__class__.__name__}"])
        provenance = [_prov(self.provider_id, f"live-{index}", self.urls[index], self.authority, {"url": self.urls[index], "content_hash": content_hash(page)}) for index, page in enumerate(pages)]
        return RegulationResponse(provider_id=self.provider_id, status="AVAILABLE", freshness="CURRENT", provenance=provenance)

    async def pest_alerts(self, request: RegulationRequest) -> RegulationResponse:
        return await self.movement_rules(request)

    async def reporting_requirements(self, request: RegulationRequest) -> RegulationResponse:
        return await self.movement_rules(request)

    def _fetch(self, url: str) -> str:
        http_request = urlrequest.Request(url, headers={"User-Agent": "GAIA Protocol Two Sentinel/0.1", "Accept": "text/html"})
        with urlrequest.urlopen(http_request, timeout=self.timeout_seconds) as response:
            return response.read().decode("utf-8", errors="replace")


def _prov(provider_id: str, record_id: str, url: str, authority: str, payload: object) -> ProvenanceRecord:
    return ProvenanceRecord(
        provider=provider_id,
        external_record_id=record_id,
        canonical_url=url,
        authority=authority,
        geographic_scope="regulatory jurisdiction",
        license="official public regulatory source",
        attribution=authority,
        content_hash=content_hash(payload),
    )

