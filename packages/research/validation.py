from __future__ import annotations

import json
from typing import Any

from packages.provenance import unverifiable_prose_identifiers


class ResearchValidationError(ValueError):
    pass


FORBIDDEN_CERTAINTY_PATTERNS = ["87.4% proven", "guaranteed", "definitively proven"]
ALLOWED_CITATION_FIELDS = {"source_work_ids", "work_ids", "citations"}


def parse_synthesis_json(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ResearchValidationError("research_model_output_not_valid_json") from exc
    if not isinstance(parsed, dict):
        raise ResearchValidationError("research_model_output_not_object")
    return parsed


def validate_synthesis_draft(content: str, *, allowed_work_ids: set[str]) -> dict[str, Any]:
    draft = parse_synthesis_json(content)
    for field in ["question", "summary", "evidence_quality", "uncertainty"]:
        if field not in draft:
            raise ResearchValidationError(f"missing_{field}")
    text = json.dumps(draft, sort_keys=True).lower()
    if any(pattern in text for pattern in FORBIDDEN_CERTAINTY_PATTERNS):
        raise ResearchValidationError("fake_numeric_or_absolute_certainty_rejected")
    cited = _find_citations(draft)
    unknown = sorted(citation for citation in cited if citation not in allowed_work_ids)
    if unknown:
        raise ResearchValidationError("model_generated_unknown_citation_rejected")
    # Key-based checking above cannot see an identifier a model writes into a
    # narrative field, which reads to a human as a real citation.
    if unverifiable_prose_identifiers(draft, set(allowed_work_ids)):
        raise ResearchValidationError("model_generated_unknown_identifier_in_prose_rejected")
    for field in ["supporting_claims", "contradictory_claims", "uncertain_claims"]:
        if field in draft and not isinstance(draft[field], list):
            raise ResearchValidationError(f"invalid_{field}")
    return draft


def _find_citations(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if key.lower() in ALLOWED_CITATION_FIELDS:
                if isinstance(nested, list):
                    found.extend(str(item) for item in nested if str(item).strip())
                elif nested:
                    found.append(str(nested))
            found.extend(_find_citations(nested))
    elif isinstance(value, list):
        for item in value:
            found.extend(_find_citations(item))
    return found


def sanitize_retrieved_text(text: str) -> str:
    return text.replace("\x00", "").strip()

