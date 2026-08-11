from __future__ import annotations

from dataclasses import asdict
from typing import AsyncIterator

from packages.orchestration import GaiaOrchestrator
from packages.persistence import GaiaRepository
from packages.tools import ToolExecutionContext


async def post_chat(
    orchestrator: GaiaOrchestrator,
    context: ToolExecutionContext,
    *,
    message: str,
    location_id: str,
) -> dict:
    result = await orchestrator.handle_chat(context, message=message, location_id=location_id)
    return _chat_result_dict(result)


async def post_chat_message(
    orchestrator: GaiaOrchestrator,
    context: ToolExecutionContext,
    *,
    conversation_id: str,
    message: str,
    location_id: str,
) -> dict:
    result = await orchestrator.handle_chat(
        context,
        conversation_id=conversation_id,
        message=message,
        location_id=location_id,
    )
    return _chat_result_dict(result)


async def stream_chat_message(
    orchestrator: GaiaOrchestrator,
    context: ToolExecutionContext,
    *,
    message: str,
    location_id: str,
    conversation_id: str | None = None,
) -> AsyncIterator[dict]:
    yield {"event": "route_pending"}
    result = await orchestrator.handle_chat(
        context,
        conversation_id=conversation_id,
        message=message,
        location_id=location_id,
    )
    yield {"event": "route", "route": result.route, "model_run_count": result.model_run_count}
    for chunk in _chunks(result.content):
        yield {"event": "token", "text": chunk}
    yield {"event": "final", "data": _chat_result_dict(result)}


def get_conversations(repository: GaiaRepository, context: ToolExecutionContext) -> list[dict]:
    return repository.list_conversations(context.organization_id, context.workspace_id)


def _chat_result_dict(result) -> dict:
    data = asdict(result)
    if result.context_bundle is not None:
        data["context_bundle"] = result.context_bundle.to_dict()
    return data


def _chunks(text: str, size: int = 48) -> list[str]:
    return [text[index : index + size] for index in range(0, len(text), size)] or [""]
