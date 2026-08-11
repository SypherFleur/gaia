from __future__ import annotations

import json

from packages.model_gateway.types import ModelCapabilities, ModelProvider, ModelRequest, ModelResponse


class FixtureScholarModelProvider(ModelProvider):
    def __init__(self, *, injected_work_id: str | None = None, fake_certainty: bool = False) -> None:
        self.provider_id = "ollama-local"
        self.model = "fixture-scholar-local"
        self.injected_work_id = injected_work_id
        self.fake_certainty = fake_certainty
        self.last_request = None

    async def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(provider_id=self.provider_id, model=self.model, text=True, structured_output=True, local_or_remote="local")

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.last_request = request
        work_id = self.injected_work_id or _first_allowed_work_id(request)
        summary = "The retrieved evidence is mixed and context-dependent."
        if self.fake_certainty:
            summary = "This is 87.4% proven and guaranteed."
        content = json.dumps(
            {
                "question": "fixture scholar question",
                "summary": summary,
                "supporting_claims": [{"statement": "Some controlled work reports an effect.", "source_work_ids": [work_id]}] if work_id else [],
                "contradictory_claims": [{"statement": "Review evidence remains limited.", "source_work_ids": [work_id]}] if work_id else [],
                "uncertain_claims": [],
                "evidence_quality": "mixed",
                "model_confidence": "moderate",
                "uncertainty": {"level": "mixed", "reasons": ["Retrieved studies disagree or have limited applicability."]},
                "applicability": {"summary": "Apply cautiously to the current plant context."},
            },
            sort_keys=True,
        )
        return ModelResponse(
            provider_id=self.provider_id,
            model=self.model,
            content=content,
            input_tokens_or_units=sum(len(message.content.split()) for message in request.messages),
            output_tokens_or_units=len(content.split()),
            elapsed_ms=1,
            cost_usd=0.0,
            status="success",
        )


def _first_allowed_work_id(request: ModelRequest) -> str | None:
    try:
        payload = json.loads(request.messages[1].content)
    except (IndexError, json.JSONDecodeError):
        return None
    work_ids = payload.get("allowed_work_ids", [])
    return work_ids[0] if work_ids else None

