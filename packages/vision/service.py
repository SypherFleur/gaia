from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any

from packages.botany import BotanistService
from packages.context import ContextCompiler
from packages.domain import MediaAttachment, Observation, SourceRecord, VisualAnalysis
from packages.persistence import GaiaRepository
from packages.provenance import ProvenanceRecord
from packages.tools import ToolExecutionContext, ToolGateway, ToolRequest, ToolResult
from packages.vision.tools import VisionAnalysisTool
from packages.vision.validation import VisionValidationError, validate_visual_response


JsonDict = dict[str, Any]


@dataclass(frozen=True, slots=True)
class VisionAnalysisResult:
    visual_analysis: VisualAnalysis
    provider_result: ToolResult
    observation_id: str | None


class VisionService:
    def __init__(
        self,
        *,
        repository: GaiaRepository,
        tool_gateway: ToolGateway,
        context_compiler: ContextCompiler | None = None,
        botanist: BotanistService | None = None,
    ) -> None:
        self.repository = repository
        self.tool_gateway = tool_gateway
        self.context_compiler = context_compiler
        self.botanist = botanist

    async def create_image_attachment(
        self,
        context: ToolExecutionContext,
        *,
        image_base64: str,
        content_type: str = "image/jpeg",
        user_plant_id: str | None = None,
    ) -> MediaAttachment:
        digest = _image_digest(image_base64)
        metadata = {"content_hash": digest, "inline_base64": image_base64}
        if user_plant_id:
            metadata["user_plant_id"] = user_plant_id
        return self.repository.create_media_attachment(
            MediaAttachment(
                organization_id=context.organization_id,
                workspace_id=context.workspace_id,
                modality="image",
                storage_uri=f"inline://sha256/{digest}",
                content_type=content_type,
                byte_size=len(image_base64),
                metadata=metadata,
            )
        )

    async def analyze_attachment(
        self,
        context: ToolExecutionContext,
        *,
        tool: VisionAnalysisTool,
        media_attachment_id: str,
        user_plant_id: str | None = None,
        location_id: str | None = None,
        prompt: str = "Describe visible plant evidence and cautious hypotheses.",
        persist_observation: bool = True,
    ) -> VisionAnalysisResult:
        media = self.repository.get_media_attachment(context.organization_id, media_attachment_id)
        if media is None:
            raise PermissionError("MediaAttachment is missing or inaccessible")
        if media.get("modality") != "image":
            raise ValueError("Vision analysis requires an image attachment")
        image_base64 = media.get("metadata", {}).get("inline_base64")
        if not image_base64:
            raise ValueError("Image bytes are unavailable for local Phase 6 analysis")

        botanist_context = {}
        if user_plant_id and self.botanist is not None:
            botanist_context = (await self.botanist.build_context(context, user_plant_id)).to_dict()

        geo_context_id = None
        environmental_snapshot_id = None
        environmental_context = {}
        if location_id and self.context_compiler is not None:
            bundle = await self.context_compiler.build_environmental_context(context, location_id)
            environmental_context = bundle.to_dict()
            geo_context_id = bundle.geo_context.id
            environmental_snapshot_id = bundle.environmental_snapshot.id if bundle.environmental_snapshot else None

        digest = str(media.get("metadata", {}).get("content_hash") or _image_digest(image_base64))
        tool_result = await self.tool_gateway.execute(
            tool,
            context,
            ToolRequest(
                payload={
                    "image_base64": image_base64,
                    "content_type": media.get("content_type") or "image/jpeg",
                    "prompt": prompt,
                    "user_plant_context": botanist_context,
                    "environmental_context": environmental_context,
                    "metadata": {"media_attachment_id": media_attachment_id, "image_hash": digest},
                },
                cache_key=f"vision:{tool.provider_id}:{digest}",
                cache_ttl_seconds=86400,
                stale_if_error_seconds=86400 * 7,
                allow_stale_cache=True,
                estimated_cost_usd=0.0,
                contains_private_image=True,
                contains_private_text=bool(botanist_context),
                contains_exact_location=False,
            ),
        )
        source_record_ids = self._persist_sources(context.organization_id, tool_result.provenance)
        status = _analysis_status(tool_result)
        observations = tool_result.data.get("observations", [])
        hypotheses = tool_result.data.get("hypotheses", [])
        safety_notes = list(tool_result.data.get("safety_notes", []))
        if status == "AVAILABLE":
            try:
                validate_visual_response(observations, hypotheses)
            except VisionValidationError as exc:
                status = "VALIDATION_FAILED"
                observations = []
                hypotheses = []
                safety_notes.append(f"Rejected unsafe visual output: {exc}")

        visual_analysis = self.repository.create_visual_analysis(
            VisualAnalysis(
                organization_id=context.organization_id,
                workspace_id=context.workspace_id,
                user_plant_id=user_plant_id,
                media_attachment_id=media_attachment_id,
                provider=str(tool_result.data.get("provider_id") or tool.provider_id),
                model=tool_result.data.get("model"),
                status=status,
                image_quality=tool_result.data.get("image_quality", {}),
                plant_candidates=tool_result.data.get("plant_candidates", []) if status == "AVAILABLE" else [],
                visual_observations=[_observation_payload(item, source_record_ids) for item in observations] if status == "AVAILABLE" else [],
                visual_hypotheses=[_hypothesis_payload(item, source_record_ids) for item in hypotheses] if status == "AVAILABLE" else [],
                required_next_evidence=tool_result.data.get("required_next_evidence", []),
                botanist_context=botanist_context,
                geo_context_id=geo_context_id,
                environmental_snapshot_id=environmental_snapshot_id,
                model_run_id=tool_result.data.get("model_run_id"),
                source_record_ids=source_record_ids,
                safety_notes=safety_notes or ["Vision output is not a confirmed diagnosis."],
            )
        )
        observation_id = None
        if persist_observation and user_plant_id and status == "AVAILABLE":
            observation = self.repository.create_observation(
                Observation(
                    organization_id=context.organization_id,
                    workspace_id=context.workspace_id,
                    user_plant_id=user_plant_id,
                    author_id=context.user_id,
                    text="GAIA visual analysis attached cautious image evidence.",
                    images=[media_attachment_id],
                    weather_snapshot_id=environmental_snapshot_id,
                    source="imported",
                    observed_facts=visual_analysis.visual_observations,
                    gaia_inferences=visual_analysis.visual_hypotheses,
                    health_tags=[str(item.get("label")) for item in visual_analysis.visual_observations],
                )
            )
            observation_id = observation.id
        return VisionAnalysisResult(visual_analysis=visual_analysis, provider_result=tool_result, observation_id=observation_id)

    def _persist_sources(self, organization_id: str, provenance_records: list[ProvenanceRecord]) -> list[str]:
        source_ids = []
        for provenance in provenance_records:
            source = SourceRecord(
                organization_id=organization_id,
                provider=provenance.provider,
                source_type="vision",
                canonical_url=provenance.canonical_url,
                external_record_id=provenance.external_record_id,
                title=provenance.external_record_id or provenance.provider,
                authority=provenance.authority,
                retrieved_at=provenance.retrieved_at,
                observed_at=provenance.observed_at,
                valid_from=provenance.valid_at,
                license=provenance.license,
                attribution=provenance.attribution,
                content_hash=provenance.content_hash,
            )
            self.repository.create_source_record(source)
            source_ids.append(source.id)
        return source_ids


def _analysis_status(result: ToolResult) -> str:
    if result.status in {"AVAILABLE", "UNAVAILABLE", "PROVIDER_ERROR", "VALIDATION_FAILED"}:
        return result.status
    if result.status in {"denied", "failed", "fail_closed"}:
        return "UNAVAILABLE"
    return "AVAILABLE" if result.data else "UNAVAILABLE"


def _observation_payload(item: JsonDict, source_record_ids: list[str]) -> JsonDict:
    return {
        "label": item.get("label", ""),
        "description": item.get("description", ""),
        "visibility": item.get("visibility", "visible"),
        "bounding_region": item.get("bounding_region"),
        "confidence": item.get("confidence"),
        "source_record_ids": source_record_ids,
        "evidence_role": "visual_observation",
    }


def _hypothesis_payload(item: JsonDict, source_record_ids: list[str]) -> JsonDict:
    return {
        "label": item.get("label", ""),
        "rationale": item.get("rationale", ""),
        "confidence": item.get("confidence", 0.0),
        "status": item.get("status", "hypothesis"),
        "required_next_evidence": item.get("required_next_evidence", []),
        "source_record_ids": source_record_ids,
        "evidence_role": "visual_hypothesis",
    }


def _image_digest(image_base64: str) -> str:
    return hashlib.sha256(image_base64.encode("utf-8")).hexdigest()

