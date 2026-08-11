from __future__ import annotations

import json
from typing import Any


JsonDict = dict[str, Any]


class GuidancePlanValidationError(ValueError):
    pass


REQUIRED_LIST_FIELDS = [
    "recommendations",
    "actions",
    "timing",
    "risks",
    "measurements_to_take",
    "follow_up",
]


def parse_guidance_plan_json(content: str) -> JsonDict:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise GuidancePlanValidationError("model_output_not_valid_json") from exc
    if not isinstance(parsed, dict):
        raise GuidancePlanValidationError("model_output_not_object")
    return parsed


def validate_guidance_plan_draft(content: str) -> JsonDict:
    draft = parse_guidance_plan_json(content)
    for field in ["subject", "situation"]:
        if not isinstance(draft.get(field), str) or not draft[field].strip():
            raise GuidancePlanValidationError(f"missing_or_invalid_{field}")
    for field in REQUIRED_LIST_FIELDS:
        if not isinstance(draft.get(field), list):
            raise GuidancePlanValidationError(f"missing_or_invalid_{field}")
    if "resources" in draft and not isinstance(draft["resources"], list):
        raise GuidancePlanValidationError("invalid_resources")
    if not isinstance(draft.get("uncertainty"), dict):
        raise GuidancePlanValidationError("missing_or_invalid_uncertainty")
    injected_ids = _find_model_generated_source_ids(draft)
    if injected_ids:
        raise GuidancePlanValidationError("model_generated_source_ids_rejected")
    return {
        "subject": draft["subject"].strip(),
        "situation": draft["situation"].strip(),
        "recommendations": draft["recommendations"],
        "actions": draft["actions"],
        "timing": draft["timing"],
        "resources": draft.get("resources", []),
        "risks": draft["risks"],
        "uncertainty": draft["uncertainty"],
        "measurements_to_take": draft["measurements_to_take"],
        "follow_up": draft["follow_up"],
    }


def _find_model_generated_source_ids(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized_key = key.lower()
            if normalized_key in {"source_record_ids", "source_ids", "citations", "citation_ids"}:
                if isinstance(nested, list):
                    found.extend(str(item) for item in nested if str(item).strip())
                elif nested:
                    found.append(str(nested))
            found.extend(_find_model_generated_source_ids(nested))
    elif isinstance(value, list):
        for item in value:
            found.extend(_find_model_generated_source_ids(item))
    return found
