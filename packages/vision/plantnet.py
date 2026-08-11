from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from packages.provenance import ProvenanceRecord, content_hash
from packages.vision.providers import VisionCapabilities, VisionRequest, VisionResponse


JsonDict = dict[str, Any]


def normalize_plantnet_identification(payload: JsonDict) -> list[JsonDict]:
    candidates = []
    for item in payload.get("results", []):
        species = item.get("species", {})
        scientific = species.get("scientificNameWithoutAuthor") or species.get("scientificName")
        common_names = species.get("commonNames") or []
        candidates.append(
            {
                "scientific_name": scientific,
                "common_name": common_names[0] if common_names else None,
                "confidence": item.get("score"),
                "source": "plantnet",
                "external_id": species.get("id"),
            }
        )
    return candidates


@dataclass(slots=True)
class PlantNetAdapter:
    api_key: str | None = None
    base_url: str = "https://my-api.plantnet.org/v2"
    provider_id: str = "plantnet"

    async def capabilities(self) -> VisionCapabilities:
        return VisionCapabilities(
            provider_id=self.provider_id,
            plant_identification=True,
            image_quality_assessment=False,
            local_or_remote="remote",
            cost_class="FREE",
        )

    async def analyze(self, request: VisionRequest) -> VisionResponse:
        if not self.api_key:
            return VisionResponse(
                provider_id=self.provider_id,
                status="UNAVAILABLE",
                warnings=["plantnet_api_key_not_configured"],
                safety_notes=["Pl@ntNet is optional and is not required for GAIA to boot or test."],
            )
        raise NotImplementedError("Live Pl@ntNet HTTP execution is intentionally deferred behind Tool Gateway configuration.")

    def fixture_response(self, payload: JsonDict) -> VisionResponse:
        candidates = normalize_plantnet_identification(payload)
        return VisionResponse(
            provider_id=self.provider_id,
            status="AVAILABLE",
            plant_candidates=candidates,
            safety_notes=["Pl@ntNet identification is not a disease diagnosis."],
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    external_record_id=payload.get("query", {}).get("project"),
                    canonical_url="https://my.plantnet.org/doc/api/identify",
                    authority="Pl@ntNet recognition API",
                    geographic_scope="image-based plant identification",
                    license="Pl@ntNet API terms",
                    attribution="Pl@ntNet",
                    content_hash=content_hash(payload),
                )
            ],
        )

