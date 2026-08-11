from __future__ import annotations

import asyncio
import json
import time
import urllib.error
import urllib.request

from packages.model_gateway.types import ModelCapabilities, ModelProvider, ModelRequest, ModelResponse


class OllamaUnavailableError(RuntimeError):
    pass


class OllamaModelProvider(ModelProvider):
    def __init__(
        self,
        *,
        provider_id: str = "ollama-local",
        model: str = "llama3.1:latest",
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: float = 60.0,
    ) -> None:
        self.provider_id = provider_id
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            provider_id=self.provider_id,
            model=self.model,
            text=True,
            image=self.model.startswith("llava"),
            audio=False,
            video=False,
            tool_use=False,
            structured_output=True,
            context_window=8192,
            local_or_remote="local",
            cost_class="LOCAL",
        )

    async def generate(self, request: ModelRequest) -> ModelResponse:
        return await asyncio.to_thread(self._generate_sync, request)

    def _generate_sync(self, request: ModelRequest) -> ModelResponse:
        started = time.perf_counter()
        payload = {
            "model": self.model,
            "messages": [{"role": message.role, "content": message.content} for message in request.messages],
            "stream": False,
            "options": {"temperature": request.temperature},
        }
        if request.response_format == "json":
            payload["format"] = "json"
        if request.max_output_tokens is not None:
            payload["options"]["num_predict"] = request.max_output_tokens

        body = json.dumps(payload).encode("utf-8")
        http_request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise OllamaUnavailableError(str(exc)) from exc

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        content = data.get("message", {}).get("content", "")
        return ModelResponse(
            provider_id=self.provider_id,
            model=self.model,
            model_version=data.get("model"),
            content=content,
            input_tokens_or_units=int(data.get("prompt_eval_count") or 0),
            output_tokens_or_units=int(data.get("eval_count") or 0),
            elapsed_ms=elapsed_ms,
            cost_usd=0.0,
            finish_reason=data.get("done_reason"),
            status="success",
        )
