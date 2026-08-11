from __future__ import annotations

from packages.tools import GaiaTool, ToolExecutionContext, ToolRequest, ToolResult, ToolRisk
from packages.vision.providers import VisionProvider, VisionRequest


class VisionAnalysisTool(GaiaTool):
    id = "vision.provider.analyze"
    version = "0.1.0"
    risk_class = ToolRisk.READ
    required_permissions = ("vision.analyze",)

    def __init__(self, provider: VisionProvider, *, provider_id: str | None = None) -> None:
        self.provider = provider
        self.provider_id = provider_id or provider.provider_id

    async def execute(self, context: ToolExecutionContext, request: ToolRequest) -> ToolResult:
        response = await self.provider.analyze(
            VisionRequest(
                image_base64=str(request.payload.get("image_base64", "")),
                content_type=str(request.payload.get("content_type", "image/jpeg")),
                prompt=str(request.payload.get("prompt", "")),
                user_plant_context=request.payload.get("user_plant_context", {}),
                environmental_context=request.payload.get("environmental_context", {}),
                max_hypotheses=int(request.payload.get("max_hypotheses", 3)),
                metadata=request.payload.get("metadata", {}),
            )
        )
        return ToolResult(
            data={
                "provider_id": response.provider_id,
                "status": response.status,
                "observations": response.observations,
                "hypotheses": response.hypotheses,
                "plant_candidates": response.plant_candidates,
                "image_quality": response.image_quality,
                "required_next_evidence": response.required_next_evidence,
                "safety_notes": response.safety_notes,
                "model": response.model,
                "model_run_id": response.model_run_id,
                "warnings": response.warnings,
                "raw_response_reference": response.raw_response_reference,
            },
            provenance=response.provenance,
            warnings=response.warnings,
            status=response.status,
        )


class PlantNetIdentifyTool(VisionAnalysisTool):
    id = "vision.plantnet.identify"
    version = "0.1.0"

