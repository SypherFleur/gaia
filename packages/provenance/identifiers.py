from __future__ import annotations

import re
from typing import Any


# Bibliographic identifiers a model might fabricate inside prose. Structured
# citation keys are checked separately; these patterns catch the case where a
# model free-texts "see doi:10.1234/made-up" into a summary or rationale, which
# key-based validation cannot see.
DOI_PATTERN = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
PMID_PATTERN = re.compile(r"\bPMID:?\s*(\d{7,8})\b", re.IGNORECASE)
PMCID_PATTERN = re.compile(r"\bPMC\d{6,8}\b", re.IGNORECASE)

_STRIPPABLE_PREFIXES = ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "doi:", "pmid:", "pmcid:")
_TRAILING_PUNCTUATION = ".,;:)]}\"'"


def normalize_identifier(value: str) -> str:
    text = str(value).strip().lower()
    for prefix in _STRIPPABLE_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    return text.strip().rstrip(_TRAILING_PUNCTUATION)


def find_prose_identifiers(value: Any) -> list[str]:
    """Every bibliographic identifier appearing in any string in the payload.

    Walks prose fields as well as structured ones, so a fabricated DOI hidden
    in a narrative sentence is surfaced.
    """
    found: list[str] = []
    if isinstance(value, dict):
        for nested in value.values():
            found.extend(find_prose_identifiers(nested))
    elif isinstance(value, list):
        for item in value:
            found.extend(find_prose_identifiers(item))
    elif isinstance(value, str):
        found.extend(match.group(0) for match in DOI_PATTERN.finditer(value))
        found.extend(f"pmid:{match.group(1)}" for match in PMID_PATTERN.finditer(value))
        found.extend(match.group(0) for match in PMCID_PATTERN.finditer(value))
    return found


def expand_allowed_identifiers(allowed: set[str] | frozenset[str]) -> set[str]:
    """Normalized forms of every allowed identifier, including ones embedded in it.

    A work id may be a bare DOI, a prefixed DOI, or an opaque provider id that
    contains one; all forms must compare equal to what appears in prose.
    """
    expanded: set[str] = set()
    for item in allowed:
        text = str(item)
        expanded.add(normalize_identifier(text))
        for identifier in find_prose_identifiers(text):
            expanded.add(normalize_identifier(identifier))
    return {item for item in expanded if item}


def unverifiable_prose_identifiers(payload: Any, allowed: set[str] | frozenset[str]) -> list[str]:
    """Identifiers cited in prose that are not backed by a retrieved record."""
    permitted = expand_allowed_identifiers(allowed)
    seen: dict[str, None] = {}
    for identifier in find_prose_identifiers(payload):
        if normalize_identifier(identifier) not in permitted:
            seen.setdefault(identifier, None)
    return sorted(seen)
