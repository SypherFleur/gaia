from __future__ import annotations

import re


def normalize_research_query(query: str) -> str:
    normalized = re.sub(r"\s+", " ", query.strip().lower())
    return normalized


def plan_research_queries(question: str, *, botanist_context: dict | None = None, limit: int = 3) -> list[str]:
    normalized = normalize_research_query(question)
    variants = [normalized]
    plant_entity = (botanist_context or {}).get("plant_entity", {})
    scientific = plant_entity.get("scientific_name")
    common_names = plant_entity.get("common_names") or []
    if scientific:
        variants.append(f"{scientific} {normalized}")
    if common_names:
        variants.append(f"{common_names[0]} {normalized}")
    if "full moon" in normalized or "lunar" in normalized or "moon" in normalized:
        variants.extend(["lunar phase plant growth", "moonlight germination controlled experiment"])
    if "blossom-end rot" in normalized or "calcium" in normalized:
        variants.extend(["calcium spray blossom-end rot tomato", "Solanum lycopersicum blossom end rot calcium"])
    deduped = []
    for variant in variants:
        clean = normalize_research_query(variant)
        if clean and clean not in deduped:
            deduped.append(clean)
    return deduped[:limit]

