from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib import request as urlrequest

from packages.provenance import ProvenanceRecord, content_hash
from packages.vision.providers import VisionCapabilities, VisionRequest, VisionResponse
from packages.vision.validation import VisionValidationError, validate_visual_response


JsonDict = dict[str, Any]


SYSTEM_PROMPT = """You are GAIA Vision. Return JSON only with observations, hypotheses, plant_candidates, image_quality, required_next_evidence, and safety_notes.
Describe visible plant evidence. Do not diagnose. Use only cautious hypothesis status values: hypothesis, possible, candidate."""


@dataclass(slots=True)
class OllamaLlavaVisionProvider:
    model: str = "llava:latest"
    base_url: str = "http://localhost:11434"
    timeout_seconds: float = 60.0
    provider_id: str = "ollama-llava-local"

    async def capabilities(self) -> VisionCapabilities:
        return VisionCapabilities(
            provider_id=self.provider_id,
            plant_identification=True,
            general_visual_reasoning=True,
            symptom_description=True,
            image_quality_assessment=True,
            bounding_regions=False,
            local_or_remote="local",
            cost_class="LOCAL",
        )

    async def analyze(self, request: VisionRequest) -> VisionResponse:
        started = time.monotonic()
        prompt = f"{SYSTEM_PROMPT}\n\nUser request:\n{request.prompt}"
        body = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt, "images": [request.image_base64]},
            ],
            "options": {"temperature": 0.1},
        }
        try:
            response_payload = await asyncio.to_thread(self._post_json, "/api/chat", body)
        except Exception as exc:
            return VisionResponse(provider_id=self.provider_id, model=self.model, status="PROVIDER_ERROR", warnings=[f"ollama_error:{exc.__class__.__name__}"])

        content = str(response_payload.get("message", {}).get("content", ""))
        parsed = _parse_json_object(content)
        observations = parsed.get("observations", []) if parsed else []
        hypotheses = parsed.get("hypotheses", []) if parsed else []
        try:
            validate_visual_response(observations, hypotheses)
        except VisionValidationError as exc:
            return VisionResponse(
                provider_id=self.provider_id,
                model=self.model,
                status="VALIDATION_FAILED",
                warnings=[str(exc)],
                safety_notes=["Local vision output failed GAIA caution validation and was not accepted as plant evidence."],
            )
        payload_hash = content_hash({"content": content, "elapsed_ms": int((time.monotonic() - started) * 1000)})
        return VisionResponse(
            provider_id=self.provider_id,
            model=self.model,
            status="AVAILABLE",
            observations=observations,
            hypotheses=hypotheses,
            plant_candidates=parsed.get("plant_candidates", []) if parsed else [],
            image_quality=parsed.get("image_quality", {"usable": bool(content), "issues": ["unstructured local output"], "confidence": 0.2}),
            required_next_evidence=parsed.get("required_next_evidence", []) if parsed else [],
            safety_notes=(parsed.get("safety_notes", []) if parsed else []) + ["Local LLaVA output is visual evidence, not a diagnosis."],
            provenance=[
                ProvenanceRecord(
                    provider=self.provider_id,
                    external_record_id=self.model,
                    canonical_url="http://localhost:11434/api/chat",
                    authority="local Ollama",
                    geographic_scope="local image evidence",
                    license="local model license",
                    attribution="Ollama local runtime",
                    content_hash=payload_hash,
                )
            ],
        )

    def _post_json(self, path: str, body: JsonDict) -> JsonDict:
        data = json.dumps(body).encode("utf-8")
        http_request = urlrequest.Request(
            self.base_url.rstrip("/") + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlrequest.urlopen(http_request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))


def _parse_json_object(text: str) -> JsonDict:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end < start:
        return {}
    try:
        parsed = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}

