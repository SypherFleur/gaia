from __future__ import annotations

from packages.provenance import ProvenanceRecord, content_hash
from packages.vision.providers import VisionCapabilities, VisionRequest, VisionResponse


class FixtureVisionProvider:
    provider_id = "fixture-vision-local"

    def __init__(self, *, overclaim: bool = False, unavailable: bool = False) -> None:
        self.overclaim = overclaim
        self.unavailable = unavailable
        self.calls = 0

    async def capabilities(self) -> VisionCapabilities:
        return VisionCapabilities(
            provider_id=self.provider_id,
            plant_identification=True,
            general_visual_reasoning=True,
            symptom_description=True,
            image_quality_assessment=True,
            bounding_regions=True,
            local_or_remote="local",
            cost_class="LOCAL",
        )

    async def analyze(self, request: VisionRequest) -> VisionResponse:
        self.calls += 1
        if self.unavailable:
            return VisionResponse(provider_id=self.provider_id, status="PROVIDER_ERROR", warnings=["fixture_vision_unavailable"])
        observations = [
            {
                "label": "visible yellowing",
                "description": "Yellowing is visible along lower leaf margins.",
                "visibility": "visible",
                "confidence": 0.72,
                "bounding_region": {"x": 0.18, "y": 0.42, "width": 0.38, "height": 0.28},
            },
            {
                "label": "brown circular lesions",
                "description": "Small brown circular lesions are visible on one lower leaf.",
                "visibility": "visible",
                "confidence": 0.58,
            },
        ]
        hypotheses = [
            {
                "label": "early blight",
                "rationale": "Brown lesions on lower leaves can be consistent with early blight, but image evidence alone is insufficient.",
                "confidence": 0.46,
                "status": "hypothesis",
                "required_next_evidence": ["clear underside image", "close-up of lesion margins", "recent watering and weather history"],
            },
            {
                "label": "nutrient stress",
                "rationale": "Lower-leaf yellowing can be consistent with nutrient stress, but soil or tissue evidence is needed.",
                "confidence": 0.34,
                "status": "hypothesis",
                "required_next_evidence": ["soil pH or fertility context"],
            },
        ]
        if self.overclaim:
            hypotheses[0]["status"] = "confirmed"
            hypotheses[0]["rationale"] = "Confirmed early blight."
        payload = {"observations": observations, "hypotheses": hypotheses}
        return VisionResponse(
            provider_id=self.provider_id,
            status="AVAILABLE",
            observations=observations,
            hypotheses=hypotheses,
            plant_candidates=[
                {"scientific_name": "Solanum lycopersicum", "common_name": "tomato", "confidence": 0.64, "source": self.provider_id}
            ],
            image_quality={"usable": True, "issues": ["single angle only"], "confidence": 0.8},
            required_next_evidence=["underside of affected leaf", "whole plant photo", "close-up in natural light"],
            safety_notes=["Vision output is not a confirmed diagnosis."],
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    external_record_id="fixture-vision-analysis",
                    canonical_url="fixture://vision/analysis",
                    authority="GAIA fixture vision provider",
                    geographic_scope="image evidence",
                    license="internal-fixture",
                    attribution="GAIA fixture",
                    content_hash=content_hash(payload),
                )
            ],
            model="fixture-vision-v0",
        )


class FixturePlantNetProvider:
    provider_id = "plantnet"

    async def capabilities(self) -> VisionCapabilities:
        return VisionCapabilities(
            provider_id=self.provider_id,
            plant_identification=True,
            image_quality_assessment=False,
            local_or_remote="remote",
            cost_class="FREE",
        )

    async def analyze(self, request: VisionRequest) -> VisionResponse:
        payload = {
            "candidates": [
                {"scientific_name": "Solanum lycopersicum", "common_name": "tomato", "confidence": 0.78, "source": "plantnet"}
            ]
        }
        return VisionResponse(
            provider_id=self.provider_id,
            status="AVAILABLE",
            plant_candidates=payload["candidates"],
            image_quality={"usable": True, "issues": [], "confidence": 0.7},
            safety_notes=["Pl@ntNet identification is not a disease diagnosis."],
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    external_record_id="fixture-plantnet-identification",
                    canonical_url="fixture://plantnet/identify",
                    authority="Pl@ntNet recognition API",
                    geographic_scope="image-based plant identification",
                    license="unknown",
                    attribution="Pl@ntNet",
                    content_hash=content_hash(payload),
                )
            ],
        )
