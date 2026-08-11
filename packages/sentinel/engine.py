from __future__ import annotations

from dataclasses import dataclass
from typing import Any


JsonDict = dict[str, Any]

STATUS_RANK = {"ALLOWED": 0, "CONDITIONAL": 1, "RESTRICTED": 2, "UNRESOLVED": 3}
RESTRICTIVE_ORDER = ["ALLOWED", "CONDITIONAL", "RESTRICTED", "UNRESOLVED"]


@dataclass(frozen=True, slots=True)
class MatchResult:
    applicable: bool
    exception_applied: bool = False
    reasons: list[str] | None = None


def normalize_taxon_name(value: str | None) -> str:
    return " ".join((value or "").strip().lower().replace(" spp.", "").split())


def rule_matches(rule: JsonDict, request: JsonDict, origin_geo: JsonDict, destination_geo: JsonDict) -> MatchResult:
    reasons = []
    if not _taxon_matches(rule.get("regulated_taxa", []), request.get("species")):
        return MatchResult(False, reasons=["taxon_not_matched"])
    if not _plant_part_matches(rule.get("plant_parts", []), request):
        return MatchResult(False, reasons=["plant_part_not_matched"])
    if not _scope_matches(rule.get("origin_scope", {}), origin_geo, request, "origin"):
        return MatchResult(False, reasons=["origin_scope_not_matched"])
    if not _scope_matches(rule.get("destination_scope", {}), destination_geo, request, "destination"):
        return MatchResult(False, reasons=["destination_scope_not_matched"])
    for exception in rule.get("exceptions", []):
        if exception.get("plant_part") == request.get("plant_part"):
            return MatchResult(False, exception_applied=True, reasons=[f"exception:{exception.get('condition', 'matched')}"])
    if request.get("soil_attached") and "growing medium" in rule.get("plant_parts", []):
        reasons.append("soil_or_growing_media_matched")
    return MatchResult(True, reasons=reasons)


def aggregate_status(applicable_rules: list[JsonDict], *, freshness: str, conflicts: list[JsonDict], unresolved_questions: list[str]) -> str:
    if unresolved_questions or conflicts or freshness in {"UNAVAILABLE", "STALE", "EXPIRED", "CONFLICT"}:
        return "UNRESOLVED"
    if not applicable_rules:
        return "ALLOWED"
    status = "ALLOWED"
    for rule in applicable_rules:
        effect = rule.get("status_effect", "CONDITIONAL")
        if STATUS_RANK.get(effect, 1) > STATUS_RANK.get(status, 0):
            status = effect
    return status


def detect_conflicts(applicable_rules: list[JsonDict]) -> list[JsonDict]:
    conflicts = []
    for rule in applicable_rules:
        if rule.get("authority_metadata", {}).get("conflict_fixture"):
            conflicts.append(
                {
                    "subject": rule.get("rule_id"),
                    "effects": [rule.get("status_effect", "CONDITIONAL")],
                    "authorities": [rule.get("authority")],
                    "resolution": "UNRESOLVED",
                }
            )
    by_subject: dict[str, set[str]] = {}
    for rule in applicable_rules:
        key = f"{rule.get('authority_level')}:{rule.get('pest_or_disease')}:{','.join(rule.get('plant_parts', []))}"
        by_subject.setdefault(key, set()).add(rule.get("status_effect", "CONDITIONAL"))
    for key, effects in by_subject.items():
        if "ALLOWED" in effects and ({"CONDITIONAL", "RESTRICTED"} & effects):
            conflicts.append({"subject": key, "effects": sorted(effects), "resolution": "UNRESOLVED"})
    return conflicts


def source_class(rule: JsonDict) -> str:
    return rule.get("authority_metadata", {}).get("source_class", "informational")


def _taxon_matches(regulated_taxa: list[JsonDict], species: str | None) -> bool:
    if not species:
        return False
    normalized = normalize_taxon_name(species)
    parts = normalized.split()
    genus = parts[0] if parts else normalized
    for item in regulated_taxa:
        name = normalize_taxon_name(item.get("name"))
        rank = item.get("rank")
        if rank == "genus" and genus == name:
            return True
        if rank == "species" and normalized == name:
            return True
        if rank == "host_class" and name in {"plants for planting", "citrus"}:
            return True
    return False


def _plant_part_matches(plant_parts: list[str], request: JsonDict) -> bool:
    part = request.get("plant_part", "unknown")
    if part in plant_parts:
        return True
    if request.get("live_plant") and "live plant" in plant_parts:
        return True
    if request.get("soil_attached") and "growing medium" in plant_parts:
        return True
    return False


def _scope_matches(scope: JsonDict, geo: JsonDict, request: JsonDict, side: str) -> bool:
    if not scope:
        return True
    country = geo.get("country_code") or request.get(f"{side}_country")
    state = geo.get("state_code")
    county = (geo.get("county_or_district") or "").replace(" County", "")
    if scope.get("country_code") == "US" and country != "US":
        return False
    if scope.get("country_code") == "ANY_NON_US" and country == "US":
        return False
    if scope.get("state_code") == "ANY":
        return True
    if scope.get("state_code") and state != scope["state_code"]:
        return False
    counties = scope.get("counties")
    if counties and county not in counties:
        return False
    quarantine_zone = scope.get("quarantine_zone")
    zones = geo.get("quarantine_zones", []) + geo.get("pest_zones", []) + geo.get("regulatory_zones", [])
    if quarantine_zone == "tx-hlb":
        return any("Gulf Coast" in zone or "Citrus Greening" in zone for zone in zones)
    if quarantine_zone == "citrus":
        return bool(zones) or state in {"TX", "FL", "CA", "AZ"}
    return True
