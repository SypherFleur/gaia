from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


JsonDict = dict[str, Any]
ModelCostClass = Literal["LOCAL", "FREE", "MANUAL_PAID"]


@dataclass(frozen=True, slots=True)
class ModelCapabilities:
    provider_id: str
    model: str
    text: bool = True
    image: bool = False
    audio: bool = False
    video: bool = False
    tool_use: bool = False
    structured_output: bool = False
    context_window: int | None = None
    local_or_remote: Literal["local", "remote"] = "local"
    cost_class: ModelCostClass = "LOCAL"


@dataclass(frozen=True, slots=True)
class ModelMessage:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True, slots=True)
class ModelRequest:
    messages: list[ModelMessage]
    prompt_id: str
    prompt_version: str
    prompt_hash: str
    response_format: Literal["json", "text"] = "text"
    temperature: float = 0.2
    max_output_tokens: int | None = None
    input_modalities: list[str] = field(default_factory=lambda: ["text"])
    metadata: JsonDict = field(default_factory=dict)
    contains_private_text: bool = True
    contains_private_image: bool = False
    contains_private_document: bool = False
    contains_exact_location: bool = False
    estimated_usage_units: float = 1.0
    estimated_cost_usd: float = 0.0


@dataclass(frozen=True, slots=True)
class ModelResponse:
    provider_id: str
    model: str
    content: str
    model_version: str | None = None
    input_tokens_or_units: int = 0
    output_tokens_or_units: int = 0
    elapsed_ms: int = 0
    cost_usd: float = 0.0
    finish_reason: str | None = None
    model_run_id: str | None = None
    status: Literal["success", "denied", "provider_error"] = "success"
    error: str | None = None
    raw_response_reference: str | None = None


class ModelProvider(Protocol):
    provider_id: str
    model: str

    async def capabilities(self) -> ModelCapabilities: ...

    async def generate(self, request: ModelRequest) -> ModelResponse: ...
