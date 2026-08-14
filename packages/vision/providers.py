from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from packages.provenance import ProvenanceRecord


JsonDict = dict[str, Any]


@dataclass(frozen=True, slots=True)
class VisionCapabilities:
    provider_id: str
    plant_identification: bool = False
    general_visual_reasoning: bool = False
    symptom_description: bool = False
    image_quality_assessment: bool = False
    bounding_regions: bool = False
    multiframe: bool = False
    video: bool = False
    local_or_remote: str = "local"
    cost_class: str = "LOCAL"


@dataclass(frozen=True, slots=True)
class VisionRequest:
    image_base64: str
    content_type: str
    prompt: str
    user_plant_context: JsonDict = field(default_factory=dict)
    environmental_context: JsonDict = field(default_factory=dict)
    max_hypotheses: int = 3
    metadata: JsonDict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VisionResponse:
    provider_id: str
    status: str
    observations: list[JsonDict] = field(default_factory=list)
    hypotheses: list[JsonDict] = field(default_factory=list)
    plant_candidates: list[JsonDict] = field(default_factory=list)
    image_quality: JsonDict = field(default_factory=dict)
    required_next_evidence: list[str] = field(default_factory=list)
    safety_notes: list[str] = field(default_factory=list)
    provenance: list[ProvenanceRecord] = field(default_factory=list)
    model: str | None = None
    model_run_id: str | None = None
    warnings: list[str] = field(default_factory=list)
    raw_response_reference: str | None = None


class VisionProvider(Protocol):
    provider_id: str

    async def capabilities(self) -> VisionCapabilities: ...

    async def analyze(self, request: VisionRequest) -> VisionResponse: ...


class DisabledVisionProvider:
    provider_id = "ollama-llava-local"

    async def capabilities(self) -> VisionCapabilities:
        return VisionCapabilities(provider_id=self.provider_id, local_or_remote="local", cost_class="LOCAL")

    async def analyze(self, request: VisionRequest) -> VisionResponse:
        return VisionResponse(provider_id=self.provider_id, status="UNAVAILABLE", warnings=["vision_provider_disabled"])
