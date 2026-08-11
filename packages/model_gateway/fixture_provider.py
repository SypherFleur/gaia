from __future__ import annotations

import json

from packages.model_gateway.types import ModelCapabilities, ModelProvider, ModelRequest, ModelResponse


class FixtureGuidanceModelProvider(ModelProvider):
    def __init__(self, *, malformed: bool = False, injected_source_id: str | None = None) -> None:
        self.provider_id = "ollama-local"
        self.model = "fixture-guidance-local"
        self.malformed = malformed
        self.injected_source_id = injected_source_id

    async def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            provider_id=self.provider_id,
            model=self.model,
            text=True,
            structured_output=True,
            context_window=4096,
            local_or_remote="local",
            cost_class="LOCAL",
        )

    async def generate(self, request: ModelRequest) -> ModelResponse:
        if self.malformed:
            content = "not-json: pretend this is a GuidancePlan"
        else:
            recommendation = {
                "summary": "Wait for a warm, stable window before planting tomatoes.",
                "rationale": "The context includes forecast, soil survey, season, and photoperiod signals, but GAIA has not yet loaded crop-specific cultivar thresholds.",
                "confidence": 0.62,
            }
            if self.injected_source_id is not None:
                recommendation["source_record_ids"] = [self.injected_source_id]
            content = json.dumps(
                {
                    "subject": "Tomato planting considerations",
                    "situation": "The user is considering planting tomatoes using the current GAIA location and environmental context.",
                    "recommendations": [recommendation],
                    "actions": [
                        {
                            "title": "Check nighttime lows before transplanting",
                            "instructions": "Avoid transplanting if forecast lows are near cold-stress ranges; use local forecast context and wait for a warmer window.",
                        }
                    ],
                    "timing": [{"window": "next suitable warm period", "basis": "forecast and seasonal context"}],
                    "resources": [],
                    "risks": [
                        {
                            "risk": "Cold stress or poor establishment",
                            "mitigation": "Delay planting or protect seedlings if nights trend cold.",
                        }
                    ],
                    "uncertainty": {
                        "level": "medium",
                        "reasons": ["Crop-specific thresholds and cultivar details are deferred until Botanist/Season phases."],
                    },
                    "measurements_to_take": [
                        {"measurement": "soil temperature at planting depth", "why": "SSURGO is survey data, not live bed temperature."}
                    ],
                    "follow_up": [{"prompt": "Share tomato variety and bed/container conditions for a tighter plan."}],
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
