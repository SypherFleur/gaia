from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any


JsonDict = dict[str, Any]

COMMODITY_ALIASES = {
    "tomato": {
        "canonical_name": "tomato",
        "scientific_name": "Solanum lycopersicum",
        "source_labels": ["TOMATOES", "Tomatoes, fresh market", "Tomato", "Fresh tomatoes"],
    },
    "tomatoes": {
        "canonical_name": "tomato",
        "scientific_name": "Solanum lycopersicum",
        "source_labels": ["TOMATOES", "Tomatoes, fresh market", "Tomato", "Fresh tomatoes"],
    },
    "solanum lycopersicum": {
        "canonical_name": "tomato",
        "scientific_name": "Solanum lycopersicum",
        "source_labels": ["TOMATOES", "Tomatoes, fresh market", "Tomato", "Fresh tomatoes"],
    },
    "fresh tomatoes": {
        "canonical_name": "tomato",
        "scientific_name": "Solanum lycopersicum",
        "source_labels": ["TOMATOES", "Fresh tomatoes"],
    },
    "citrus": {
        "canonical_name": "citrus",
        "scientific_name": "Citrus spp.",
        "source_labels": ["CITRUS", "Citrus"],
    },
}


def normalize_commodity(label: str, *, crop_or_taxon: JsonDict | None = None) -> JsonDict:
    native = label.strip()
    key = native.lower()
    if key not in COMMODITY_ALIASES and crop_or_taxon:
        scientific = str(crop_or_taxon.get("scientific_name") or "").lower()
        key = scientific if scientific in COMMODITY_ALIASES else key
    base = dict(COMMODITY_ALIASES.get(key, {"canonical_name": key or native, "scientific_name": None, "source_labels": []}))
    labels = list(dict.fromkeys([native, *base.get("source_labels", [])]))
    base["source_labels"] = labels
    if crop_or_taxon and crop_or_taxon.get("id"):
        base["crop_or_taxon_id"] = crop_or_taxon["id"]
    return base


def classify_freshness(data_class: str, observation_period: str | None, publication_date: str | None, *, today: date | None = None) -> str:
    current_day = today or datetime.now(UTC).date()
    if data_class == "REALTIME_OR_CURRENT_REPORT":
        report_day = _parse_date(publication_date or observation_period)
        if report_day is None:
            return "current_report_unknown_date"
        age_days = (current_day - report_day).days
        if age_days <= 14:
            return "current"
        if age_days <= 90:
            return "recent"
        return "historical"
    if data_class == "RECENT_PERIODIC_STATISTIC":
        year = _period_year(observation_period)
        if year is not None and current_day.year - year <= 1:
            return "recent_periodic"
        return "historical"
    if data_class == "STRUCTURAL_SUPPLY_CHAIN":
        return "structural_historical"
    if data_class == "REGIONAL_ECONOMIC_CONTEXT":
        return "regional_context"
    if data_class == "MODEL_OR_INFERENCE":
        return "modeled_or_inferred"
    return "historical"


def comparable_units(left: JsonDict, right: JsonDict) -> tuple[bool, str]:
    left_unit = str(left.get("unit") or left.get("normalized_unit") or "")
    right_unit = str(right.get("unit") or right.get("normalized_unit") or "")
    left_package = str(left.get("package") or "")
    right_package = str(right.get("package") or "")
    left_grade = str(left.get("grade") or "").strip().lower()
    right_grade = str(right.get("grade") or "").strip().lower()
    # Different quality grades are different products; a price delta across
    # grades would silently conflate quality tiers.
    if left_grade != right_grade:
        return False, "grade_mismatch"
    if left_unit == right_unit and left_package == right_package:
        return True, "same_unit_and_package"
    if left_unit in {"$/lb", "USD/lb"} and right_unit in {"$/lb", "USD/lb"}:
        return True, "same_weight_unit"
    return False, "incompatible_unit_or_package"


def normalize_unit(value: Any, unit: str, *, package: str | None = None, grade: str | None = None) -> JsonDict:
    return {
        "original_value": value,
        "original_unit": unit,
        "normalized_value": value if unit in {"$/lb", "USD/lb", "acres", "cwt"} else None,
        "normalized_unit": unit if unit in {"$/lb", "USD/lb", "acres", "cwt"} else None,
        "package": package,
        "grade": grade,
        "conversion_status": "known" if unit in {"$/lb", "USD/lb", "acres", "cwt"} else "not_converted_without_package_weight",
    }


def _period_year(period: str | None) -> int | None:
    if not period:
        return None
    for token in str(period).replace("-", " ").split():
        if token.isdigit() and len(token) == 4:
            return int(token)
    return None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        year = _period_year(value)
        if year is not None:
            return date(year, 12, 31)
    return None

